import json
import os
import sys
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import fetch_devpost as D  # noqa: E402
import fetch_mlh as M  # noqa: E402
import hacks_db as H  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


class TestDevpost(unittest.TestCase):
    def test_parse_range_shapes(self):
        self.assertEqual(D.parse_range("Aug 31 - Oct 23, 2026"), ("2026-08-31", "2026-10-23"))
        self.assertEqual(D.parse_range("Oct 05 - 27, 2026"), ("2026-10-05", "2026-10-27"))
        self.assertEqual(D.parse_range("Dec 20, 2026 - Jan 10, 2027"), ("2026-12-20", "2027-01-10"))
        self.assertEqual(D.parse_range("Oct 27, 2026"), ("2026-10-27", "2026-10-27"))
        self.assertEqual(D.parse_range("Dec 20 - Jan 10, 2027"), ("2026-12-20", "2027-01-10"))
        self.assertEqual(D.parse_range("soon"), ("", ""))

    def test_null_fields_do_not_crash(self):
        r = D.parse_hackathons({"hackathons": [{"title": "X", "themes": None, "displayed_location": {"location": ""}}]})[0]
        self.assertEqual((r["themes"], r["mode"]), ([], ""))
        e = {"name": "N", "formatType": "digital", "customFields": None, "venueAddress": None}
        self.assertEqual(M.to_raw(e)["themes"], [])

    def test_parse_fixture(self):
        rows = D.parse_hackathons(json.loads(fixture("devpost_sample.json")))
        self.assertEqual(len(rows), 3)
        r = rows[0]
        self.assertEqual((r["name"], r["mode"], r["platform"]), ("Build, Ship, Shape: Amazon Developer Hackathon",
                                                                  "online", "devpost"))
        self.assertEqual((r["event_start"], r["submit_deadline"], r["prize_pool"]), ("2026-08-31", "2026-10-23", "$138,000"))
        self.assertIn("Machine Learning/AI", r["themes"])
        self.assertTrue(r["url"].startswith("https://"))

    def test_offline_event_gets_city(self):
        data = {"hackathons": [{"title": "X", "displayed_location": {"location": "Pune, India"},
                                "submission_period_dates": "Oct 05 - 27, 2026", "url": "https://x"}]}
        r = D.parse_hackathons(data)[0]
        self.assertEqual((r["mode"], r["city"]), ("offline", "Pune, India"))

    def test_fetch_all_stops_on_empty_page(self):
        calls = []
        data = json.loads(fixture("devpost_sample.json"))

        def fake(url):
            calls.append(url)
            return data if len(calls) == 1 else {"hackathons": []}
        rows = D.fetch_all(pages=5, delay=0, fetcher=fake)
        self.assertEqual((len(rows), len(calls)), (3, 2))
        self.assertIn("status%5B%5D=open", calls[0])

    def test_feeds_db(self):
        rows = D.parse_hackathons(json.loads(fixture("devpost_sample.json")))
        with tempfile.TemporaryDirectory() as tmp:
            con = H.connect(os.path.join(tmp, "h.db"))
            r = H.add_hacks(con, rows)
            self.assertEqual((r["added"], r["invalid"]), (3, 0))
            self.assertEqual(H.add_hacks(con, rows)["duplicates"], 3)
            con.close()


class TestMlh(unittest.TestCase):
    def test_country_filter(self):
        rows = M.parse_page(fixture("mlh_sample.html"))
        self.assertEqual([r["name"] for r in rows], ["hackCBS 9.O"])
        r = rows[0]
        self.assertEqual((r["mode"], r["city"], r["event_start"], r["event_end"]),
                         ("offline", "New delhi, New delhi", "2026-10-31", "2026-11-01"))
        self.assertTrue(r["url"].startswith("http"))
        self.assertNotIn("_country", r)

    def test_keep_all_and_modes(self):
        rows = M.parse_page(fixture("mlh_sample.html"), keep_all=True)
        self.assertEqual({r["name"]: r["mode"] for r in rows},
                         {"hackCBS 9.O": "offline", "SwampHacks XII": "offline", "Technica Hacks": "hybrid"})

    def test_layout_change_is_loud(self):
        with self.assertRaises(ValueError):
            M.parse_events("<html>no script</html>")
        with self.assertRaises(ValueError):
            M.parse_events('<script data-page="app" type="application/json">{"props":{}}</script>')

    def test_default_season(self):
        self.assertEqual(M.default_season(date(2026, 10, 18)), 2027)
        self.assertEqual(M.default_season(date(2027, 3, 1)), 2027)

    def test_feeds_db(self):
        rows = M.parse_page(fixture("mlh_sample.html"), keep_all=True)
        with tempfile.TemporaryDirectory() as tmp:
            con = H.connect(os.path.join(tmp, "h.db"))
            self.assertEqual(H.add_hacks(con, rows)["added"], 3)
            con.close()


if __name__ == "__main__":
    unittest.main()
