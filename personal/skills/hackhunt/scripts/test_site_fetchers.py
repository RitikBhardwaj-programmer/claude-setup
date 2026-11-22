"""Tests for fetch_unstop, fetch_devfolio, fetch_devpost_rules and stealth_fetch. No network, no browser.

Fixtures in fixtures/ are trimmed from real responses saved on 2026-11-10 (Unstop, Devpost rules) or from one
polite live request made the same day (Devfolio). The Cloudflare page is a minimal hand-made stand-in.
"""
import contextlib
import io
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import fetch_devfolio as DF  # noqa: E402
import fetch_devpost_rules as DR  # noqa: E402
import fetch_unstop as U  # noqa: E402
import hacks_db as H  # noqa: E402
import stealth_fetch as S  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


CLOUDFLARE = "<html><head><title>Just a moment...</title></head><body>Enable JavaScript and cookies to continue</body></html>"


class TestUnstop(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(fixture("unstop_sample.json"))
        self.rows = U.parse_items(self.data)

    def test_parse_fixture(self):
        self.assertEqual(len(self.rows), 3)
        r = self.rows[0]
        self.assertEqual(r["name"], "IDEATHON- FutureX: Innovating for Global Challenges")
        self.assertEqual((r["organiser"], r["platform"], r["source"]), ("Skill2Career", "unstop", "unstop"))
        self.assertEqual((r["mode"], r["team_min"], r["team_max"], r["solo_ok"]), ("online", 2, 4, False))
        self.assertEqual((r["reg_deadline"], r["event_end"]), ("2026-12-16", "2026-12-18"))
        self.assertTrue(r["url"].startswith("https://unstop.com/hackathons/ideathon-futurex"))
        self.assertEqual((r["fee"], r["city"], r["prize_pool"]), ("", "", ""))

    def test_paid_offline_with_prizes(self):
        r = self.rows[1]
        self.assertEqual((r["name"], r["mode"], r["city"]), ("Zenith'26", "offline", "Hyderabad"))
        self.assertEqual((r["fee"], r["prize_pool"], r["perks"]), ("₹499", "₹150,000", "AWS Swags"))
        self.assertEqual((r["team_min"], r["team_max"]), (3, 4))
        self.assertIn("Engineering Students", r["eligibility_text"])
        self.assertIn("Problem Solving", r["themes"])

    def test_solo_ok_when_min_team_is_one(self):
        r = self.rows[2]
        self.assertEqual((r["team_min"], r["team_max"], r["solo_ok"]), (1, 1, True))
        self.assertEqual(r["reg_deadline"], "2027-03-01")

    def test_missing_fields_do_not_crash(self):
        r = U.parse_items({"data": {"data": [{"title": "Bare", "themes": None, "prizes": None, "filters": None}]}})[0]
        self.assertEqual((r["name"], r["mode"], r["reg_deadline"], r["themes"], r["fee"]), ("Bare", "", "", [], ""))
        self.assertNotIn("team_min", r)
        self.assertNotIn("solo_ok", r)

    def test_empty_list(self):
        self.assertEqual(U.parse_items({"data": {"data": []}}), [])
        self.assertEqual(U.parse_items({}), [])
        self.assertEqual(U.fetch_all(1, fetcher=lambda url: {"data": {"data": [], "last_page": 1}}), [])

    def test_rows_feed_hacks_db_unchanged(self):
        for r in self.rows:
            n = H.normalise(r)
            self.assertEqual(n["platform"], "unstop")

    def test_page_cap_and_delay_enforced(self):
        urls = []

        def fake(url):
            urls.append(url)
            return {"data": {"data": self.data["data"]["data"][:1], "last_page": 13}}

        with mock.patch.object(U.time, "sleep") as sleep:
            rows = U.fetch_all(pages=50, delay=0, fetcher=fake)
        self.assertEqual(len(urls), 3)
        self.assertEqual(len(rows), 3)
        self.assertIn("page=3", urls[2])
        self.assertIn("oppstatus=open", urls[0])
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(c.args[0] >= 2 for c in sleep.call_args_list))

    def test_stops_at_last_page(self):
        calls = []

        def fake(url):
            calls.append(url)
            return {"data": {"data": self.data["data"]["data"][:1], "last_page": 2}}

        with mock.patch.object(U.time, "sleep"):
            U.fetch_all(pages=3, fetcher=fake)
        self.assertEqual(len(calls), 2)

    def test_failure_reports_json_on_stderr_exit_1(self):
        err = io.StringIO()
        with mock.patch.object(U, "fetch_page", side_effect=OSError("boom")), contextlib.redirect_stderr(err):
            code = U.main([])
        self.assertEqual(code, 1)
        e = json.loads(err.getvalue())
        self.assertEqual((e["ok"], e["source"]), (False, "unstop"))
        self.assertIn("boom", e["error"])


class TestDevfolio(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(fixture("devfolio_sample.json"))
        self.rows = DF.parse_hits(self.data)

    def test_parse_fixture(self):
        self.assertEqual(len(self.rows), 3)
        r = self.rows[0]
        self.assertEqual((r["name"], r["platform"], r["source"]), ("Hacknauts 2.0", "devfolio", "devfolio"))
        self.assertEqual(r["url"], "https://hacknauts26.devfolio.co/overview")
        self.assertEqual((r["mode"], r["city"]), ("offline", "Ludhiana"))
        self.assertEqual((r["team_min"], r["team_max"], r["solo_ok"]), (2, 4, False))
        self.assertEqual((r["event_start"], r["event_end"], r["reg_deadline"]), ("2026-11-14", "2026-11-15", "2026-11-10"))

    def test_faq_answers_feed_fee_and_eligibility(self):
        r = self.rows[2]
        self.assertEqual(r["name"], "GeNarrative Clash")
        self.assertIn("completely free", r["fee"])
        self.assertNotIn("**", r["fee"])
        self.assertIn("Team size: Teams can consist of anywhere from 2 to 4 members", r["eligibility_text"])
        self.assertIn("Who can participate:", r["eligibility_text"])
        self.assertIn("currently enrolled", r["eligibility_text"])
        self.assertEqual(r["themes"], ["Design"])
        self.assertEqual(r["reg_deadline"], "2026-11-15")

    def test_no_faqs_leaves_fee_and_eligibility_empty(self):
        r = self.rows[1]
        self.assertEqual((r["fee"], r["eligibility_text"], r["themes"]), ("", "", []))

    def test_dates_use_event_timezone(self):
        self.assertEqual(DF._local_date("2026-11-13T18:30:00+00:00", "Asia/Calcutta"), "2026-11-14")
        self.assertEqual(DF._local_date("2026-11-13T18:30:00+00:00", "UTC"), "2026-11-13")
        self.assertEqual(DF._local_date(None, "UTC"), "")

    def test_online_event_and_missing_fields(self):
        h = {"hits": {"hits": [{"_source": {"name": "Web", "slug": "web", "is_online": True, "city": "X"}}]}}
        r = DF.parse_hits(h)[0]
        self.assertEqual((r["mode"], r["city"], r["reg_deadline"], r["fee"]), ("online", "", "", ""))
        self.assertNotIn("team_min", r)
        r = DF.parse_hits({"hits": {"hits": [{"_source": {"name": "NoFlag"}}]}})[0]
        self.assertEqual((r["mode"], r["url"]), ("", ""))

    def test_empty_list(self):
        self.assertEqual(DF.parse_hits({"hits": {"total": {"value": 0}, "hits": []}}), [])
        self.assertEqual(DF.parse_hits({}), [])

    def test_rows_feed_hacks_db_unchanged(self):
        for r in self.rows:
            self.assertEqual(H.normalise(r)["platform"], "devfolio")

    def test_request_cap_offsets_and_body(self):
        calls = []

        def fake(url, body):
            calls.append((url, dict(body)))
            return {"hits": {"total": {"value": 500}, "hits": self.data["hits"]["hits"][:1]}}

        with mock.patch.object(DF.time, "sleep") as sleep:
            rows = DF.fetch_all(pages=9, size=20, delay=0, fetcher=fake)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual([c[1]["from"] for c in calls], [0, 20, 40])
        self.assertEqual(calls[0][1], {"type": "application_open", "from": 0, "size": 20})
        self.assertEqual(calls[0][0], "https://api.devfolio.co/api/search/hackathons")
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(c.args[0] >= 2 for c in sleep.call_args_list))

    def test_stops_when_total_reached(self):
        calls = []

        def fake(url, body):
            calls.append(body)
            return {"hits": {"total": {"value": 18}, "hits": self.data["hits"]["hits"]}}

        with mock.patch.object(DF.time, "sleep"):
            DF.fetch_all(pages=3, size=20, fetcher=fake)
        self.assertEqual(len(calls), 1)

    def test_failure_reports_json_on_stderr_exit_1(self):
        err = io.StringIO()
        with mock.patch.object(DF, "fetch_page", side_effect=OSError("boom")), contextlib.redirect_stderr(err):
            code = DF.main([])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(err.getvalue())["source"], "devfolio")


class TestDevpostRules(unittest.TestCase):
    def setUp(self):
        self.team = fixture("devpost_rules_team.html")
        self.noteam = fixture("devpost_rules_noteam.html")

    def row(self, url="https://kiroween.devpost.com/", **kw):
        r = {"name": "Kiroween", "platform": "devpost", "url": url, "source": "devpost", "eligibility_text": ""}
        r.update(kw)
        return r

    def test_rules_url(self):
        self.assertEqual(DR.rules_url("https://x.devpost.com/"), "https://x.devpost.com/rules")
        self.assertEqual(DR.rules_url("https://x.devpost.com"), "https://x.devpost.com/rules")
        self.assertEqual(DR.rules_url("https://x.devpost.com/?ref=1"), "https://x.devpost.com/rules")
        self.assertEqual(DR.rules_url("https://unstop.com/hackathons/x"), "")
        self.assertEqual(DR.rules_url("https://evil.com/?u=x.devpost.com"), "")
        self.assertEqual(DR.rules_url(""), "")

    def test_team_max_from_css(self):
        self.assertEqual(DR.parse_team_max(self.team), 3)
        self.assertIsNone(DR.parse_team_max(self.noteam))

    def test_eligibility_section(self):
        e = DR.parse_eligibility(self.team)
        self.assertTrue(e.startswith("The Hackathon IS open to"))
        self.assertNotIn("3. Eligibility", e)
        self.assertIn("maximum 3 participants per team", e)
        self.assertNotIn("<", e)
        self.assertNotIn("&nbsp;", e)
        self.assertLessEqual(len(e), 600)
        self.assertEqual(len(e), 600)  # the real section is longer than the cap
        self.assertNotIn("How to Enter", e)
        self.assertEqual(DR.parse_eligibility("<h5>1. Dates</h5><p>x</p>"), "")

    def test_enrich_row(self):
        new, note = DR.enrich_row(self.row(), fetcher=lambda u: self.team)
        self.assertEqual(note, "")
        self.assertEqual(new["team_max"], 3)
        self.assertTrue(new["eligibility_text"].startswith("The Hackathon IS open to"))
        self.assertNotIn("team_max", self.row())

    def test_no_css_team_size_leaves_team_max_unset(self):
        new, note = DR.enrich_row(self.row(), fetcher=lambda u: self.noteam)
        self.assertNotIn("team_max", new)
        self.assertTrue(new["eligibility_text"].startswith("The Hackathon IS open to"))

    def test_existing_eligibility_text_is_kept(self):
        new, _ = DR.enrich_row(self.row(eligibility_text="Invite only: x"), fetcher=lambda u: self.noteam)
        self.assertTrue(new["eligibility_text"].startswith("Invite only: x | The Hackathon IS open to"))

    def test_fetches_rules_url(self):
        seen = []
        DR.enrich_row(self.row("https://kiroween.devpost.com/"), fetcher=lambda u: seen.append(u) or self.team)
        self.assertEqual(seen, ["https://kiroween.devpost.com/rules"])

    def test_cloudflare_page_leaves_row_unchanged_and_reports(self):
        rows = [self.row()]
        reports = []
        with mock.patch.object(DR.time, "sleep"):
            out = DR.enrich_all(rows, fetcher=lambda u: CLOUDFLARE, report=reports.append)
        self.assertEqual(out, rows)
        self.assertEqual(len(reports), 1)
        self.assertFalse(reports[0]["ok"])
        self.assertIn("Cloudflare", reports[0]["error"])

    def test_one_bad_page_does_not_fail_run(self):
        rows = [self.row("https://a.devpost.com/"), self.row("https://b.devpost.com/")]

        def fake(url):
            if "a.devpost" in url:
                raise OSError("down")
            return self.team

        reports = []
        with mock.patch.object(DR.time, "sleep"):
            out = DR.enrich_all(rows, fetcher=fake, report=reports.append)
        self.assertEqual(out[0], rows[0])
        self.assertEqual(out[1]["team_max"], 3)
        self.assertEqual(len(reports), 1)

    def test_limit_pause_and_non_devpost_rows(self):
        rows = [self.row("https://e%d.devpost.com/" % i) for i in range(5)]
        rows.insert(1, {"name": "Other", "url": "https://unstop.com/hackathons/x"})
        seen = []
        with mock.patch.object(DR.time, "sleep") as sleep:
            out = DR.enrich_all(rows, limit=2, delay=0, fetcher=lambda u: seen.append(u) or self.team)
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(out), 6)
        self.assertEqual(out[1], rows[1])
        self.assertNotIn("team_max", out[-1])
        self.assertEqual(sleep.call_count, 1)
        self.assertGreaterEqual(sleep.call_args.args[0], 2)

    def test_empty_list(self):
        self.assertEqual(DR.enrich_all([], fetcher=lambda u: self.team), [])

    def test_main_reads_stdin_and_rejects_non_list(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(DR.main([], stdin=io.StringIO('{"a": 1}')), 1)
            self.assertEqual(DR.main([], stdin=io.StringIO("not json")), 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(DR.main([], stdin=io.StringIO("[]")), 0)
        self.assertEqual(json.loads(out.getvalue()), [])


class TestStealthFetch(unittest.TestCase):
    def test_arg_parsing(self):
        a = S.parse_args(["https://x.devpost.com/rules"])
        self.assertEqual((a.url, a.text, a.html), ("https://x.devpost.com/rules", False, False))
        self.assertTrue(S.parse_args(["https://x.io", "--html"]).html)
        self.assertTrue(S.parse_args(["https://x.io", "--text"]).text)

    def test_bad_args_exit(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for bad in ([], ["not-a-url"], ["https://x.io", "--text", "--html"]):
                with self.assertRaises(SystemExit):
                    S.parse_args(bad)

    def test_html_to_text(self):
        page = ("<html><head><style>.a{color:red}</style><script>var x=1;</script></head><body>"
                "<h1>Rules</h1><p>Team max&nbsp;size: <b>3</b> &amp; more</p><ul><li>One</li><li>Two</li></ul>"
                "<!-- hidden --></body></html>")
        t = S.html_to_text(page)
        self.assertEqual(t.split("\n"), ["Rules", "Team max size: 3 & more", "One", "Two"])
        self.assertNotIn("color", t)
        self.assertNotIn("var x", t)
        self.assertEqual(S.html_to_text(""), "")

    def test_scrapling_is_imported_lazily_with_clear_error(self):
        with mock.patch.dict(sys.modules, {"scrapling": None, "scrapling.fetchers": None}):
            with self.assertRaises(RuntimeError) as cm:
                S.fetch_html("https://x.io")
        self.assertIn("scrape-venv", str(cm.exception))

    def test_main_prints_text_or_html(self):
        with mock.patch.object(S, "fetch_html", return_value="<p>Hi &amp; bye</p>"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(S.main(["https://x.io"]), 0)
            self.assertEqual(out.getvalue().strip(), "Hi & bye")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                S.main(["https://x.io", "--html"])
            self.assertEqual(out.getvalue().strip(), "<p>Hi &amp; bye</p>")

    def test_main_error_json_exit_1(self):
        err = io.StringIO()
        with mock.patch.object(S, "fetch_html", side_effect=RuntimeError("no")), contextlib.redirect_stderr(err):
            self.assertEqual(S.main(["https://x.io"]), 1)
        self.assertEqual(json.loads(err.getvalue())["source"], "stealth_fetch")


class TestReviewFixes(unittest.TestCase):
    """Guards added after review: banned hosts, stop on challenge, safe numbers, clamps."""

    def test_stealth_refuses_linkedin_naukri_and_subdomains(self):
        for url in ("https://linkedin.com/jobs", "https://www.linkedin.com/in/x", "https://in.naukri.com/jobs",
                    "http://NAUKRI.COM/x", "https://a.b.linkedin.com./x"):
            with self.assertRaises(ValueError, msg=url):
                S.check_url(url)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                S.parse_args([url])
        S.check_url("https://notlinkedin.com/rules")  # lookalike host is a different site
        S.check_url("https://kiroween.devpost.com/rules")

    def test_stealth_refuses_login_register_apply_paths(self):
        for path in ("/login", "/users/Sign-In", "/signin", "/signup", "/account/Register", "/jobs/apply",
                     "/internship/APPLY/123", "/a/b/login/next"):
            with self.assertRaises(ValueError, msg=path):
                S.check_url("https://example.com" + path)
        S.check_url("https://x.devpost.com/rules")
        S.check_url("https://unstop.com/hackathons/some-event-123")

    def test_stealth_fetch_html_checks_before_importing_scrapling(self):
        with mock.patch.dict(sys.modules, {"scrapling": None, "scrapling.fetchers": None}):
            with self.assertRaises(ValueError):
                S.fetch_html("https://www.linkedin.com/jobs")

    def test_rules_url_is_idempotent(self):
        once = DR.rules_url("https://x.devpost.com/")
        self.assertEqual(DR.rules_url(once), once)
        self.assertEqual(DR.rules_url("https://x.devpost.com/rules/"), "https://x.devpost.com/rules")

    def test_challenge_stops_all_further_fetching(self):
        rows = [{"name": n, "url": "https://%s.devpost.com/" % n, "eligibility_text": ""} for n in "abc"]
        seen, reports = [], []

        def fake(url):
            seen.append(url)
            return CLOUDFLARE

        with mock.patch.object(DR.time, "sleep"):
            out = DR.enrich_all(rows, limit=10, fetcher=fake, report=reports.append)
        self.assertEqual(seen, ["https://a.devpost.com/rules"])  # 2nd and 3rd URL never fetched
        self.assertEqual(out, rows)
        self.assertEqual(len(reports), 1)

    def test_http_403_and_429_stop_but_other_errors_do_not(self):
        import urllib.error
        rows = [{"name": n, "url": "https://%s.devpost.com/" % n} for n in "abc"]
        for code, expect_calls in ((403, 1), (429, 1), (500, 3)):
            seen = []

            def fake(url, code=code):
                seen.append(url)
                raise urllib.error.HTTPError(url, code, "x", {}, io.BytesIO(b""))

            reports = []
            with mock.patch.object(DR.time, "sleep"):
                out = DR.enrich_all(rows, fetcher=fake, report=reports.append)
            self.assertEqual(len(seen), expect_calls, code)
            self.assertEqual(out, rows)

    def test_limit_clamped_to_20(self):
        rows = [{"name": "n%d" % i, "url": "https://e%d.devpost.com/" % i} for i in range(30)]
        seen = []
        with mock.patch.object(DR.time, "sleep"):
            out = DR.enrich_all(rows, limit=999, fetcher=lambda u: seen.append(u) or "<p>x</p>", report=lambda d: None)
        self.assertEqual(len(seen), 20)
        self.assertEqual(len(out), 30)

    def test_eligibility_not_appended_twice(self):
        team = fixture("devpost_rules_team.html")
        r = {"name": "K", "url": "https://k.devpost.com/", "eligibility_text": ""}
        once, _ = DR.enrich_row(r, fetcher=lambda u: team)
        twice, _ = DR.enrich_row(once, fetcher=lambda u: team)
        self.assertEqual(once["eligibility_text"], twice["eligibility_text"])

    def test_unstop_num_helper(self):
        self.assertEqual(U._num("1,50,000"), 150000)
        self.assertEqual(U._num(150000), 150000)
        self.assertEqual(U._num("₹ 2,500.5"), 2500.5)
        for bad in (None, "", "abc", "N/A", True, [], {}, float("nan"), float("inf")):
            self.assertIsNone(U._num(bad), bad)

    def test_unstop_odd_fields_never_crash(self):
        item = {"title": "Odd", "prizes": [{"prize_type": "cash", "cash": "1,50,000", "currency": "fa-rupee"},
                                           {"prize_type": "cash", "cash": "lots"}, "junk", None],
                "payment_services": [{"amount": "N/A"}, {"amount": "1,000"}, 5],
                "regnRequirements": {"min_team_size": "two", "max_team_size": "4", "end_regn_dt": None},
                "filters": "oops", "required_skills": [None, {"skill": "Go"}], "organisation": None}
        r = U.parse_items({"data": {"data": [item, "not a dict", None]}})
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["prize_pool"], r[0]["fee"]), ("₹150,000", "₹1,000"))
        self.assertEqual(r[0]["team_max"], 4)
        self.assertNotIn("team_min", r[0])
        self.assertEqual(r[0]["themes"], ["Go"])

    def test_default_pages_is_two_and_cap_stays_three(self):
        for mod, fake in ((U, lambda url: {"data": {"data": [{"title": "x"}], "last_page": 13}}),
                          (DF, lambda url, body: {"hits": {"total": {"value": 999}, "hits": [{"_source": {"name": "x"}}]}})):
            calls = []
            with mock.patch.object(mod.time, "sleep"):
                mod.fetch_all(fetcher=lambda *a, f=fake: calls.append(a) or f(*a))
            self.assertEqual(len(calls), 2, mod.__name__)
            self.assertEqual(mod.MAX_PAGES, 3)

    def test_devfolio_size_clamped_to_50(self):
        bodies = []

        def fake(url, body):
            bodies.append(body)
            return {"hits": {"total": {"value": 1}, "hits": []}}

        DF.fetch_all(pages=1, size=5000, fetcher=fake)
        self.assertEqual(bodies[0]["size"], 50)

    def test_devfolio_fee_regex(self):
        def row(q):
            faq = [{"question": q, "answer": "Rs 500 per team."}]
            h = {"hits": {"hits": [{"_source": {"name": "X", "hackathon_faqs": faq}}]}}
            return DF.parse_hits(h)[0]["fee"]

        self.assertEqual(row("Is there any cost for accommodation?"), "")
        self.assertEqual(row("Is food free? What is the fee for the workshop?"), "")
        for q in ("Registration costs?", "Is there any registration fee to participate?",
                  "Is there a participation fee?", "What is the entry fee?", "Is there any cost to register?"):
            self.assertEqual(row(q), "Rs 500 per team.", q)


if __name__ == "__main__":
    unittest.main()
