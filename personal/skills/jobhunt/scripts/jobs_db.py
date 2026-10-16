"""Job store for the jobhunt skill: one schema, dedupe, status tracking, tracker.csv export. Stdlib only.

Usage:
  py -3 jobs_db.py [--data DIR] init
  py -3 jobs_db.py [--data DIR] add < jobs.json        # JSON list (or one object) of raw job dicts
  py -3 jobs_db.py [--data DIR] list [--status new] [--limit 50]
  py -3 jobs_db.py [--data DIR] show ID
  py -3 jobs_db.py [--data DIR] status ID shortlisted [--note "text"]
  py -3 jobs_db.py [--data DIR] score ID 82 "reason"
  py -3 jobs_db.py [--data DIR] export                 # writes tracker.csv

DATA defaults to env JOBHUNT_DIR, else C:/Users/DELL/JobHunt (or ~/JobHunt). Every command prints JSON.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

STATUSES = ["new", "shortlisted", "drafted", "applied", "interview", "rejected", "skipped"]
# Allowed moves. Any state can go to skipped; applied can go to interview/rejected; no going back to new.
TRANSITIONS = {
    "new": {"shortlisted", "skipped"},
    "shortlisted": {"drafted", "skipped", "applied"},
    "drafted": {"applied", "shortlisted", "skipped"},
    "applied": {"interview", "rejected"},
    "interview": {"rejected", "applied"},
    "rejected": set(),
    "skipped": {"new", "shortlisted"},
}
FIELDS = ["id", "source", "title", "company", "location", "remote", "stipend", "deadline", "url",
          "description", "first_seen"]
CSV_COLS = ["id", "status", "score", "company", "title", "location", "remote", "stipend", "deadline",
            "source", "url", "first_seen", "applied_on", "note"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, dedupe_key TEXT UNIQUE NOT NULL, source TEXT, title TEXT, company TEXT,
  location TEXT, remote INTEGER DEFAULT 0, stipend TEXT, deadline TEXT, url TEXT, description TEXT,
  first_seen TEXT, status TEXT DEFAULT 'new', score INTEGER, score_reason TEXT, applied_on TEXT,
  note TEXT, also_seen TEXT DEFAULT ''
);
"""


def data_dir(arg=None):
    d = arg or os.environ.get("JOBHUNT_DIR")
    if not d:
        d = "C:/Users/DELL/JobHunt" if os.path.isdir("C:/Users/DELL") else os.path.expanduser("~/JobHunt")
    return d


def connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _norm_text(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)          # drop bracketed noise like "(Remote)"
    s = re.sub(r"[^a-z0-9+#]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_location(s):
    s = _norm_text(s)
    return s.split(" ")[0] if s else ""              # first token: "bengaluru karnataka" ~ "bengaluru india"


def _strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


def dedupe_key(company, title, location):
    return "|".join([_norm_text(company), _norm_text(title), _norm_location(location)])


def normalise(raw):
    """Map a raw job dict (from any fetcher or hand-made) to the schema. Raises ValueError if unusable."""
    title = (raw.get("title") or "").strip()
    company = (raw.get("company") or "").strip()
    if not title or not company:
        raise ValueError("job needs title and company: %r" % {k: raw.get(k) for k in ("title", "company")})
    location = (raw.get("location") or "").strip()
    remote = raw.get("remote")
    if remote is None:
        remote = bool(re.search(r"\bremote\b|work from home|\bwfh\b", location + " " + title, re.I))
    desc = _strip_html(raw.get("description"))
    key = dedupe_key(company, title, location)
    return {
        "id": hashlib.sha1(key.encode("utf-8")).hexdigest()[:10],
        "dedupe_key": key,
        "source": (raw.get("source") or "manual").strip(),
        "title": title, "company": company, "location": location, "remote": int(bool(remote)),
        "stipend": (str(raw.get("stipend")).strip() if raw.get("stipend") not in (None, "") else ""),
        "deadline": (raw.get("deadline") or "").strip(),
        "url": (raw.get("url") or "").strip(),
        "description": desc[:20000],
        "first_seen": raw.get("first_seen") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def add_jobs(con, raws):
    """Insert normalised jobs. Duplicates (same dedupe_key) keep the first record; the new source is noted."""
    added, dup, bad = [], [], []
    for raw in raws:
        try:
            j = normalise(raw)
        except ValueError as e:
            bad.append(str(e))
            continue
        row = con.execute("SELECT id, source, also_seen FROM jobs WHERE dedupe_key=?", (j["dedupe_key"],)).fetchone()
        if row:
            seen = set(filter(None, row["also_seen"].split(",")))
            if j["source"] != row["source"]:
                seen.add(j["source"])
            con.execute("UPDATE jobs SET also_seen=? WHERE id=?", (",".join(sorted(seen)), row["id"]))
            dup.append(row["id"])
            continue
        con.execute(
            "INSERT INTO jobs (id,dedupe_key,source,title,company,location,remote,stipend,deadline,url,"
            "description,first_seen) VALUES (:id,:dedupe_key,:source,:title,:company,:location,:remote,"
            ":stipend,:deadline,:url,:description,:first_seen)", j)
        added.append(j["id"])
    con.commit()
    return {"added": len(added), "duplicates": len(dup), "invalid": len(bad), "added_ids": added, "errors": bad}


def set_status(con, job_id, new, note=None):
    if new not in STATUSES:
        raise ValueError("unknown status %r; use one of %s" % (new, STATUSES))
    row = con.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise KeyError("no job with id %s" % job_id)
    old = row["status"]
    if new != old and new not in TRANSITIONS[old]:
        raise ValueError("cannot move %s -> %s (allowed: %s)" % (old, new, sorted(TRANSITIONS[old]) or "none"))
    applied_on = datetime.now().strftime("%Y-%m-%d") if new == "applied" else None
    con.execute("UPDATE jobs SET status=?, applied_on=COALESCE(?, applied_on), note=COALESCE(?, note) WHERE id=?",
                (new, applied_on, note, job_id))
    con.commit()
    return {"id": job_id, "from": old, "to": new}


def set_score(con, job_id, score, reason=""):
    if not 0 <= int(score) <= 100:
        raise ValueError("score must be 0-100")
    cur = con.execute("UPDATE jobs SET score=?, score_reason=? WHERE id=?", (int(score), reason, job_id))
    if cur.rowcount == 0:
        raise KeyError("no job with id %s" % job_id)
    con.commit()
    return {"id": job_id, "score": int(score)}


def list_jobs(con, status=None, limit=50, with_desc=False):
    q = "SELECT * FROM jobs" + (" WHERE status=?" if status else "")
    q += " ORDER BY COALESCE(score,-1) DESC, first_seen DESC LIMIT ?"
    rows = con.execute(q, ([status] if status else []) + [limit]).fetchall()
    out = [dict(r) for r in rows]
    for r in out:
        r.pop("dedupe_key", None)
        if not with_desc:
            r["description"] = r["description"][:300]
    return out


def export_csv(con, path):
    rows = con.execute("SELECT * FROM jobs ORDER BY first_seen, company").fetchall()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel reads UTF-8
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            d = dict(r)
            d["remote"] = "yes" if d["remote"] else ""
            w.writerow(d)
    return {"path": path, "rows": len(rows)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("add")
    ls = sub.add_parser("list")
    ls.add_argument("--status")
    ls.add_argument("--limit", type=int, default=50)
    sh = sub.add_parser("show")
    sh.add_argument("id")
    st = sub.add_parser("status")
    st.add_argument("id")
    st.add_argument("new")
    st.add_argument("--note")
    sc = sub.add_parser("score")
    sc.add_argument("id")
    sc.add_argument("score", type=int)
    sc.add_argument("reason", nargs="?", default="")
    sub.add_parser("export")
    a = p.parse_args(argv)

    d = data_dir(a.data)
    con = connect(os.path.join(d, "jobs.db"))
    try:
        if a.cmd == "init":
            res = {"ok": True, "db": os.path.join(d, "jobs.db")}
        elif a.cmd == "add":
            data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
            res = add_jobs(con, data if isinstance(data, list) else [data])
        elif a.cmd == "list":
            res = list_jobs(con, a.status, a.limit)
        elif a.cmd == "show":
            res = list_jobs(con, None, 100000, with_desc=True)
            res = next((r for r in res if r["id"] == a.id), None)
            if res is None:
                raise KeyError("no job with id %s" % a.id)
        elif a.cmd == "status":
            res = set_status(con, a.id, a.new, a.note)
        elif a.cmd == "score":
            res = set_score(con, a.id, a.score, a.reason)
        elif a.cmd == "export":
            res = export_csv(con, os.path.join(d, "tracker.csv"))
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
