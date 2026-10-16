import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import jobs_db as J  # noqa: E402


@pytest.fixture
def con(tmp_path):
    return J.connect(str(tmp_path / "jobs.db"))


def raw(**kw):
    d = {"title": "Software Engineer Intern", "company": "Acme", "location": "Bengaluru, India", "source": "greenhouse",
         "url": "https://x/1", "description": "<p>Build &amp; ship</p>"}
    d.update(kw)
    return d


def test_normalise_basic():
    j = J.normalise(raw())
    assert j["description"] == "Build & ship"
    assert j["remote"] == 0 and len(j["id"]) == 10


def test_normalise_remote_detected_from_location():
    assert J.normalise(raw(location="Remote - US"))["remote"] == 1
    assert J.normalise(raw(remote=False, location="Remote"))["remote"] == 0


def test_normalise_requires_title_and_company():
    with pytest.raises(ValueError):
        J.normalise({"title": "x"})


def test_dedupe_same_job_different_wording(con):
    r = J.add_jobs(con, [raw(), raw(title="Software Engineer Intern (Remote)", source="adzuna",
                                    location="Bengaluru, Karnataka"), raw(company="ACME ", title="software  engineer intern")])
    assert r["added"] == 1 and r["duplicates"] == 2
    row = con.execute("SELECT also_seen FROM jobs").fetchone()
    assert row["also_seen"] == "adzuna"


def test_different_location_is_not_duplicate(con):
    r = J.add_jobs(con, [raw(), raw(location="Berlin, Germany")])
    assert r["added"] == 2


def test_invalid_counted_not_fatal(con):
    r = J.add_jobs(con, [raw(), {"title": ""}])
    assert r["added"] == 1 and r["invalid"] == 1


def test_status_transitions(con):
    jid = J.add_jobs(con, [raw()])["added_ids"][0]
    assert J.set_status(con, jid, "shortlisted")["to"] == "shortlisted"
    with pytest.raises(ValueError):
        J.set_status(con, jid, "interview")          # must be applied first
    J.set_status(con, jid, "drafted")
    J.set_status(con, jid, "applied", note="via greenhouse")
    row = con.execute("SELECT status, applied_on, note FROM jobs").fetchone()
    assert row["status"] == "applied" and row["applied_on"] and row["note"] == "via greenhouse"
    J.set_status(con, jid, "interview")
    J.set_status(con, jid, "rejected")
    with pytest.raises(ValueError):
        J.set_status(con, jid, "new")


def test_status_unknown_id_and_value(con):
    with pytest.raises(KeyError):
        J.set_status(con, "nope", "skipped")
    jid = J.add_jobs(con, [raw()])["added_ids"][0]
    with pytest.raises(ValueError):
        J.set_status(con, jid, "hired")


def test_score_and_list_order(con):
    ids = J.add_jobs(con, [raw(), raw(company="Beta")])["added_ids"]
    J.set_score(con, ids[1], 90, "great")
    out = J.list_jobs(con)
    assert out[0]["id"] == ids[1] and "dedupe_key" not in out[0]
    with pytest.raises(ValueError):
        J.set_score(con, ids[0], 101)


def test_export_csv(con, tmp_path):
    J.add_jobs(con, [raw(title="Intern, ML \"Core\"")])
    res = J.export_csv(con, str(tmp_path / "tracker.csv"))
    assert res["rows"] == 1
    with open(res["path"], encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["title"] == 'Intern, ML "Core"' and rows[0]["status"] == "new"


def test_cli_roundtrip(tmp_path, capsys, monkeypatch):
    import io
    import json
    monkeypatch.setattr(sys, "stdin", type("S", (), {"buffer": io.BytesIO(json.dumps([raw()]).encode())})())
    assert J.main(["--data", str(tmp_path), "add"]) == 0
    assert json.loads(capsys.readouterr().out)["added"] == 1
    assert J.main(["--data", str(tmp_path), "status", "zzz", "skipped"]) == 1
