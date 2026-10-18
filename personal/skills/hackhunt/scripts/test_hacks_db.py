import csv
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import hacks_db as H  # noqa: E402


def raw(**kw):
    d = {"name": "Hack For Tomorrow 2026", "organiser": "Excel", "platform": "devfolio", "mode": "online",
         "team_min": 2, "team_max": 4, "event_start": "2026-10-24", "reg_deadline": "2026-10-20",
         "submit_deadline": "2026-10-25", "url": "https://hft2026.devfolio.co/",
         "eligibility_text": "<p>Team size 2 - 4</p>"}
    d.update(kw)
    return d


class DbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.con = H.connect(os.path.join(self.tmp.name, "hacks.db"))
        self.addCleanup(self.con.close)

    def add(self, *raws):
        return H.add_hacks(self.con, list(raws))


class TestNormalise(unittest.TestCase):
    def test_basic(self):
        h = H.normalise(raw())
        self.assertEqual(h["eligibility_text"], "Team size 2 - 4")
        self.assertEqual(len(h["id"]), 10)
        self.assertEqual(h["solo_ok"], 0)

    def test_solo_inferred_only_when_team_known(self):
        self.assertEqual(H.normalise(raw(team_min=1, team_max=4))["solo_ok"], 1)
        self.assertIsNone(H.normalise(raw(team_min=None, team_max=None))["solo_ok"])
        self.assertEqual(H.normalise(raw(team_min=None, solo_ok=True))["solo_ok"], 1)

    def test_requires_name_and_valid_mode(self):
        with self.assertRaises(ValueError):
            H.normalise({"url": "x"})
        with self.assertRaises(ValueError):
            H.normalise(raw(mode="moon"))

    def test_dates_to_iso_and_unknown_stays_empty(self):
        h = H.normalise(raw(reg_deadline="Oct 20, 2026", submit_deadline="25/10/2026", event_end="soon"))
        self.assertEqual((h["reg_deadline"], h["submit_deadline"], h["event_end"]), ("2026-10-20", "2026-10-25", ""))
        self.assertEqual(H.iso_date("2026-10-31T12:00:00Z"), "2026-10-31")
        self.assertEqual(H.iso_date("Oct 20"), "")          # no year: never guess

    def test_themes_list_joined(self):
        self.assertEqual(H.normalise(raw(themes=["AI", "Web"]))["themes"], "AI, Web")


class TestAdd(DbCase):
    def test_dedupe_across_platforms_and_fill_empty_fields(self):
        r = self.add(raw(platform="devfolio", fee="", prize_pool=""),
                     raw(name="hack for tomorrow 2026 (Online)", platform="unstop", fee="0", prize_pool="$313",
                         team_max=9))
        self.assertEqual((r["added"], r["duplicates"]), (1, 1))
        row = self.con.execute("SELECT * FROM hacks").fetchone()
        self.assertEqual(row["also_seen"], "unstop")
        self.assertEqual((row["fee"], row["prize_pool"]), ("0", "$313"))
        self.assertEqual(row["team_max"], 4)                # first record wins when a value exists

    def test_different_month_is_not_duplicate(self):
        self.assertEqual(self.add(raw(), raw(event_start="2027-10-24"))["added"], 2)

    def test_invalid_counted_not_fatal(self):
        r = self.add(raw(), {"name": ""})
        self.assertEqual((r["added"], r["invalid"]), (1, 1))


class TestReviewFixes(DbCase):
    def test_empty_start_dedupes_both_ways(self):
        self.assertEqual(self.add(raw(name="Y Hack", event_start=""), raw(name="Y Hack"))["duplicates"], 1)
        self.assertEqual(self.add(raw(name="Z Hack"), raw(name="Z Hack", event_start=""))["duplicates"], 1)
        row = self.con.execute("SELECT event_start FROM hacks WHERE name='Y Hack'").fetchone()
        self.assertEqual(row[0], "2026-10-24")                 # empty start filled by the later source

    def test_bad_types_do_not_kill_batch(self):
        r = self.add(raw(), raw(name="B", perks=5), "not a dict", raw(name="C", organiser=["x"]))
        self.assertEqual((r["added"], r["invalid"]), (1, 3))

    def test_solo_ok_strings(self):
        self.assertEqual(H.normalise(raw(solo_ok="no"))["solo_ok"], 0)
        self.assertEqual(H.normalise(raw(solo_ok="False"))["solo_ok"], 0)
        self.assertEqual(H.normalise(raw(solo_ok="yes"))["solo_ok"], 1)

    def test_sept_and_elig_replace(self):
        self.assertEqual(H.iso_date("Sept 5, 2026"), "2026-09-05")
        hid = self.add(raw(eligibility_text="Open to: Students"))["added_ids"][0]
        self.add(raw(eligibility_text="Teams of 3-4 required"))            # fill-only: tag stays
        self.assertEqual(H.list_hacks(self.con, with_text=True)[0]["eligibility_text"], "Open to: Students")
        H.set_eligibility(self.con, hid, "Teams of 3-4 required")
        self.assertEqual(H.list_hacks(self.con, with_text=True)[0]["eligibility_text"], "Teams of 3-4 required")
        with self.assertRaises(KeyError):
            H.set_eligibility(self.con, "nope", "x")

    def test_due_includes_submit_only_new_row(self):
        self.add(raw(reg_deadline="", submit_deadline="2026-10-20"))
        self.assertEqual(H.due(self.con, 7, date(2026, 10, 18))[0]["kind"], "submit_deadline")


class TestStatus(DbCase):
    def test_full_path(self):
        hid = self.add(raw())["added_ids"][0]
        H.set_status(self.con, hid, "shortlisted")
        with self.assertRaises(ValueError):
            H.set_status(self.con, hid, "submitted")        # must register first
        H.set_status(self.con, hid, "registered", note="team: me + 2")
        H.set_status(self.con, hid, "submitted")
        H.set_status(self.con, hid, "advanced")
        H.set_status(self.con, hid, "won")
        with self.assertRaises(ValueError):
            H.set_status(self.con, hid, "new")
        self.assertEqual(self.con.execute("SELECT note FROM hacks").fetchone()["note"], "team: me + 2")

    def test_skipped_only_early(self):
        hid = self.add(raw())["added_ids"][0]
        H.set_status(self.con, hid, "shortlisted")
        H.set_status(self.con, hid, "registered")
        with self.assertRaises(ValueError):
            H.set_status(self.con, hid, "skipped")
        H.set_status(self.con, hid, "out")

    def test_unknown_id_and_value(self):
        with self.assertRaises(KeyError):
            H.set_status(self.con, "nope", "skipped")
        hid = self.add(raw())["added_ids"][0]
        with self.assertRaises(ValueError):
            H.set_status(self.con, hid, "hired")


class TestScoreAndDue(DbCase):
    def test_score_and_list_order(self):
        ids = self.add(raw(), raw(name="Other Hack"))["added_ids"]
        H.set_score(self.con, ids[1], 90, "great")
        out = H.list_hacks(self.con)
        self.assertEqual(out[0]["id"], ids[1])
        self.assertNotIn("dedupe_key", out[0])
        with self.assertRaises(ValueError):
            H.set_score(self.con, ids[0], 101)

    def test_due_filter(self):
        today = date(2026, 10, 18)
        a = self.add(raw(name="A soon", reg_deadline="2026-10-20", submit_deadline="2026-11-30"))["added_ids"][0]
        self.add(raw(name="B far", reg_deadline="2026-12-20", submit_deadline="2027-01-30"))
        self.add(raw(name="C past", reg_deadline="2026-10-10", submit_deadline="2026-10-12"))
        self.add(raw(name="D none", reg_deadline="", submit_deadline=""))
        d = H.due(self.con, 7, today)
        self.assertEqual([(x["name"], x["kind"], x["days_left"]) for x in d], [("A soon", "reg_deadline", 2)])
        # once registered, only the submit deadline counts
        H.set_status(self.con, a, "shortlisted")
        H.set_status(self.con, a, "registered")
        self.assertEqual(H.due(self.con, 7, today), [])
        self.assertEqual(H.due(self.con, 60, today)[0]["kind"], "submit_deadline")
        # terminal states drop out
        H.set_status(self.con, a, "out")
        self.assertEqual(H.due(self.con, 60, today), [])

    def test_notion_ids(self):
        hid = self.add(raw())["added_ids"][0]
        H.set_notion_ids(self.con, hid, reg="r1")
        H.set_notion_ids(self.con, hid, submit="s1")
        row = self.con.execute("SELECT reg_event_id, submit_event_id FROM hacks").fetchone()
        self.assertEqual((row[0], row[1]), ("r1", "s1"))
        with self.assertRaises(KeyError):
            H.set_notion_ids(self.con, "nope", reg="x")


class TestExportAndCli(DbCase):
    def test_export_csv(self):
        self.add(raw(name='Hack "Core", 2026', team_min=None, team_max=None))
        res = H.export_csv(self.con, os.path.join(self.tmp.name, "tracker.csv"))
        with open(res["path"], encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual((res["rows"], rows[0]["name"], rows[0]["status"], rows[0]["solo_ok"]),
                         (1, 'Hack "Core", 2026', "new", ""))

    def test_cli_roundtrip(self):
        def run(args, stdin=None):
            real_in, real_out = sys.stdin, sys.stdout
            if stdin is not None:
                sys.stdin = type("S", (), {"buffer": io.BytesIO(stdin.encode())})()
            sys.stdout = out = io.StringIO()
            try:
                code = H.main(["--data", self.tmp.name] + args)
            finally:
                sys.stdin, sys.stdout = real_in, real_out
            return code, json.loads(out.getvalue())

        code, res = run(["add"], json.dumps([raw()]))
        self.assertEqual((code, res["added"]), (0, 1))
        hid = res["added_ids"][0]
        code, res = run(["status", "zzz", "skipped"])
        self.assertEqual((code, res["ok"]), (1, False))
        self.assertEqual(run(["score", hid, "70", "ok"])[1]["score"], 70)
        self.assertEqual(run(["elig", hid, "Team size 2 - 4"])[1]["eligibility_text"], "Team size 2 - 4")
        self.assertEqual(run(["notion", hid, "--reg", "e1"])[1]["reg_event_id"], "e1")
        self.assertEqual(run(["list"])[1][0]["id"], hid)
        self.assertEqual(run(["show", hid])[1]["eligibility_text"], "Team size 2 - 4")
        self.assertEqual(run(["due", "--days", "3650"])[0], 0)


if __name__ == "__main__":
    unittest.main()
