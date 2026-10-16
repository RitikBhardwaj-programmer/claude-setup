import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import fetch_adzuna as Z  # noqa: E402
import fetch_ats as A  # noqa: E402
import jobs_db as J  # noqa: E402


def fx(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return json.load(f)


def test_greenhouse_parse_and_filter():
    jobs = A.parse_greenhouse(fx("greenhouse_sample.json"), "Figma")
    assert len(jobs) == 2 and all(j["url"].startswith("http") for j in jobs)
    assert "<" not in jobs[0]["description"] and "&lt;" not in jobs[0]["description"]
    kept = [j for j in jobs if A.keep(j, A.DEFAULT_KEYWORDS)]
    assert len(kept) == 1 and "intern" in kept[0]["title"].lower()


def test_ashby_parse():
    jobs = A.parse_ashby(fx("ashby_sample.json"), "Ramp")
    assert len(jobs) == 2 and jobs[0]["source"] == "ashby" and jobs[0]["url"].startswith("https://jobs.ashbyhq.com")
    assert sum(A.keep(j, A.DEFAULT_KEYWORDS) for j in jobs) == 1


def test_lever_parse_and_all_flag():
    data = fx("lever_sample.json")
    jobs = A.parse_lever(data, "Spotify")
    assert len(jobs) == 2 and jobs[0]["url"].startswith("https://jobs.lever.co")
    c = {"name": "Spotify", "ats": "lever", "slug": "spotify"}
    assert A.fetch_company(c, A.DEFAULT_KEYWORDS, fetcher=lambda u: data) == []        # no intern titles
    assert len(A.fetch_company(c, A.DEFAULT_KEYWORDS, keep_all=True, fetcher=lambda u: data)) == 2
    data[0]["text"] = "Backend Engineering Intern"
    assert len(A.fetch_company(c, A.DEFAULT_KEYWORDS, fetcher=lambda u: data)) == 1


def test_keyword_is_word_bounded():
    assert not A.keep({"title": "International Sales Lead"}, ["intern"])
    assert A.keep({"title": "Data Science Intern, 2027"}, ["intern"])


def test_fetchers_feed_db(tmp_path):
    raws = A.parse_greenhouse(fx("greenhouse_sample.json"), "Figma") + A.parse_ashby(fx("ashby_sample.json"), "Ramp")
    con = J.connect(str(tmp_path / "j.db"))
    r = J.add_jobs(con, raws)
    assert r["added"] == 4 and r["invalid"] == 0
    assert J.add_jobs(con, raws)["duplicates"] == 4


def test_load_companies(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("# c\ncompanies:\n  - name: Figma\n    ats: greenhouse  # note\n    slug: figma\n  - ats: lever\n    slug: spotify\n",
                 encoding="utf-8")
    cs = A.load_companies(str(p))
    assert cs == [{"name": "Figma", "ats": "greenhouse", "slug": "figma"}, {"ats": "lever", "slug": "spotify", "name": "spotify"}]
    p.write_text("companies:\n  - ats: workday\n    slug: x\n", encoding="utf-8")
    with pytest.raises(ValueError):
        A.load_companies(str(p))


def test_adzuna_parse():
    jobs = Z.parse_results(fx("adzuna_sample.json"), "in")
    assert jobs[0]["company"] == "Example Tech Pvt Ltd" and jobs[0]["source"] == "adzuna-in"
    assert jobs[0]["stipend"] == "INR 240000-360000 per year (estimated)" and jobs[1]["stipend"] == ""
    assert jobs[1]["remote"] if "remote" in jobs[1] else J.normalise(jobs[1])["remote"] == 1


def test_adzuna_missing_keys(monkeypatch, capsys):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    assert Z.main([]) == 2
    assert "missing_keys" in capsys.readouterr().err
