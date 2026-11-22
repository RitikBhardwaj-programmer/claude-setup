import contextlib
import io
import json
import os
import sys
from unittest import mock

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import fetch_internshala as I  # noqa: E402
import jobs_db as J  # noqa: E402


def page(name="internshala_sample.html"):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


def jobs_of(html):
    cards, _ = I.parse_cards(html)
    return I.to_jobs(cards)


def test_parse_fixture_cards():
    jobs = jobs_of(page())
    assert len(jobs) == 3
    j = jobs[0]
    assert j["title"] == "Subject Matter Expert (SME) - AI/ML"
    assert j["company"] == "House Of Couton Private Limited"
    assert j["source"] == "internshala"
    assert j["remote"] is True and j["location"] == "Work from home"
    assert j["stipend"] == "₹ 12,000 - 35,000 /month"
    assert j["url"].startswith("https://internshala.com/internship/detail/work-from-home-subject-matter-expert")
    assert "Duration: 3 Months" in j["description"] and "Python" in j["description"]
    assert j["deadline"] == ""


def test_onsite_card_is_not_remote():
    j = jobs_of(page())[1]
    assert j["remote"] is False and j["location"] == "Hyderabad"
    assert j["stipend"].startswith("₹ 6,000")


def test_multi_location_hybrid_card():
    j = jobs_of(page())[2]
    assert j["remote"] is False
    assert j["location"].startswith("Chennai, Coimbatore") and j["location"].endswith("Tirchy (Hybrid)")


def test_pagination_state_and_url_format():
    _, is_last = I.parse_cards(page())
    assert is_last is False
    assert "href=/internships/computer-science-internship/page-2/" in page()
    assert I.page_url("computer-science", 1) == "https://internshala.com/internships/computer-science-internship/"
    assert I.page_url("computer-science", 2) == "https://internshala.com/internships/computer-science-internship/page-2/"
    assert I.page_url("web-development", 3).endswith("/web-development-internship/page-3/")


def test_missing_fields_and_empty_list():
    html = ('<div class="container-fluid individual_internship x" data-href=\'/internship/detail/a1\'>'
            '<a class="job-title-href" href="/internship/detail/a1">Only Title</a></div>'
            '<div class="container-fluid individual_internship x" data-href=\'/internship/detail/b2\'>'
            '<a class="job-title-href">T2</a><p class="company-name"> Acme </p></div>')
    jobs = jobs_of(html)
    assert len(jobs) == 1  # the card with no company is dropped (company is required by jobs_db)
    assert jobs[0]["company"] == "Acme" and jobs[0]["stipend"] == "" and jobs[0]["remote"] is False
    assert jobs[0]["url"] == "https://internshala.com/internship/detail/b2"
    assert jobs_of("<html><body>nothing</body></html>") == []


def test_recaptcha_key_on_normal_page_does_not_trigger_block():
    html = page()
    assert "recaptcha" in html.lower()
    cards, _ = I.parse_cards(html)
    I.check_blocked(html, len(cards))  # must not raise
    # even a card-less page that only mentions recaptcha (the login-form key) is not a block
    I.check_blocked("<script>var is_g_recaptcha='K'</script><script src='recaptcha/enterprise.js'></script>", 0)


@pytest.mark.parametrize("body", [
    "<title>Just a moment...</title>",
    "<p>We have detected unusual traffic from your network</p>",
    "<div>Please verify you are human</div>",
    "<form><textarea name='g-recaptcha-response'></textarea></form>",
])
def test_block_pages_stop_the_run(body):
    with pytest.raises(I.Blocked):
        I.check_blocked(body, 0)
    with mock.patch.object(I.time, "sleep"), pytest.raises(I.Blocked):
        I.fetch_all(fetcher=lambda url: body)


def test_page_cap_delay_and_last_page():
    urls = []

    def fake(url):
        urls.append(url)
        return page()

    with mock.patch.object(I.time, "sleep") as sleep:
        jobs = I.fetch_all("computer-science", pages=99, delay=0, fetcher=fake)
    assert len(urls) == 3 and len(jobs) == 9
    assert urls[1].endswith("/page-2/") and urls[2].endswith("/page-3/")
    assert sleep.call_count == 2 and all(c.args[0] >= 3 for c in sleep.call_args_list)

    last = page().replace('name="isLastPage" id="isLastPage" value="0"', 'name="isLastPage" id="isLastPage" value="1"')
    urls.clear()
    with mock.patch.object(I.time, "sleep"):
        I.fetch_all(pages=3, fetcher=lambda u: urls.append(u) or last)
    assert len(urls) == 1


def test_zero_cards_on_page_1_is_an_error():
    with mock.patch.object(I.time, "sleep"), pytest.raises(RuntimeError, match="layout changed or empty"):
        I.fetch_all(pages=3, fetcher=lambda u: "<html><body>no results</body></html>")
    err = io.StringIO()
    with mock.patch.object(I, "fetch_page", return_value="<html><body>no results</body></html>"), \
            contextlib.redirect_stderr(err):
        assert I.main([]) == 1
    assert "layout changed or empty" in json.loads(err.getvalue())["error"]


def test_empty_page_after_page_1_just_stops():
    pages = iter([page(), "<html><body>no results</body></html>"])
    with mock.patch.object(I.time, "sleep"):
        jobs = I.fetch_all(pages=3, fetcher=lambda u: next(pages))
    assert len(jobs) == 3


def test_card_with_self_closing_and_void_tags_keeps_depth():
    html = ('<div class="container-fluid individual_internship x" data-href=\'/internship/detail/a1\'>'
            '<div class="internship_logo"><img src="l.png" /><br/><img src="m.png"></div>'
            '<h2><a class="job-title-href" href="/internship/detail/a1">Img Title</a></h2>'
            '<p class="company-name">Img Co</p>'
            '<div class="row-1-item locations"><i class="ic-16-map-pin"></i><span><a>Pune</a></span></div>'
            '<span class="stipend">Unpaid</span></div>'
            '<div class="container-fluid individual_internship x" data-href=\'/internship/detail/b2\'>'
            '<a class="job-title-href" href="/internship/detail/b2">Second</a><p class="company-name">Two</p></div>')
    jobs = jobs_of(html)
    assert [j["title"] for j in jobs] == ["Img Title", "Second"]
    assert jobs[0]["company"] == "Img Co" and jobs[0]["location"] == "Pune" and jobs[0]["stipend"] == "Unpaid"
    assert jobs[1]["company"] == "Two"


def test_stray_end_tags_do_not_close_a_card_early():
    html = ('<div class="container-fluid individual_internship x" data-href=\'/internship/detail/a1\'>'
            '</span></p><a class="job-title-href" href="/internship/detail/a1">T</a></li>'
            '<p class="company-name">Co</p></div>')
    jobs = jobs_of(html)
    assert len(jobs) == 1 and jobs[0]["company"] == "Co"


@pytest.mark.parametrize("bad", ["", "Computer Science", "cs/../x", "a b", "x?y=1", "UPPER", "a_b"])
def test_category_is_validated(bad):
    called = []
    with pytest.raises(ValueError):
        I.fetch_all(bad, fetcher=lambda u: called.append(u))
    assert called == []
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert I.main(["--category", bad]) == 1
    assert json.loads(err.getvalue())["ok"] is False


def test_valid_category_url():
    seen = []
    with mock.patch.object(I.time, "sleep"):
        I.fetch_all("web-development", pages=1, fetcher=lambda u: seen.append(u) or page())
    assert seen == ["https://internshala.com/internships/web-development-internship/"]


def test_rows_feed_jobs_db_unchanged():
    for j in jobs_of(page()):
        n = J.normalise(j)
        assert n["source"] == "internshala" and n["title"] and n["company"]


def test_failure_reports_json_exit_1():
    err = io.StringIO()
    with mock.patch.object(I, "fetch_page", side_effect=OSError("boom")), contextlib.redirect_stderr(err):
        assert I.main([]) == 1
    e = json.loads(err.getvalue())
    assert e["ok"] is False and e["source"] == "internshala" and "boom" in e["error"]
