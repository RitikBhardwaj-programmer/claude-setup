"""Hackathon store for the hackhunt skill: one schema, dedupe, status tracking, due dates, tracker.csv export. Stdlib only.

Usage:
  py -3 hacks_db.py [--data DIR] init
  py -3 hacks_db.py [--data DIR] add < hacks.json       # JSON list (or one object) of raw hackathon dicts
  py -3 hacks_db.py [--data DIR] list [--status new] [--limit 50]
  py -3 hacks_db.py [--data DIR] show ID
  py -3 hacks_db.py [--data DIR] status ID shortlisted [--note "text"]
  py -3 hacks_db.py [--data DIR] score ID 82 "reason"
  py -3 hacks_db.py [--data DIR] elig ID "exact team/eligibility sentence"   # replace the stored quote
  py -3 hacks_db.py [--data DIR] due [--days 7]         # deadlines in the next N days, soonest first
  py -3 hacks_db.py [--data DIR] notion ID [--reg EVENT_ID] [--submit EVENT_ID]   # remember Notion Calendar event ids
  py -3 hacks_db.py [--data DIR] export                 # writes tracker.csv

DATA defaults to env HACKHUNT_DIR, else C:/Users/DELL/HackHunt (or ~/HackHunt). Every command prints JSON.
Dates are stored as ISO YYYY-MM-DD. Unknown team size / fee / dates stay empty: never guessed.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone

STATUSES = ["new", "shortlisted", "registered", "submitted", "advanced", "won", "out", "skipped"]
# Allowed moves. skipped is only for early drops; no going back to new once shortlisted.
TRANSITIONS = {
    "new": {"shortlisted", "skipped"},
    "shortlisted": {"registered", "skipped"},
    "registered": {"submitted", "out"},
    "submitted": {"advanced", "won", "out"},
    "advanced": {"won", "out"},
    "won": set(),
    "out": set(),
    "skipped": {"new", "shortlisted"},
}
OPEN_STATUSES = ("new", "shortlisted", "registered")   # states where a deadline still matters
MODES = ("online", "offline", "hybrid")
CSV_COLS = ["id", "status", "score", "name", "organiser", "platform", "mode", "city", "team_min", "team_max",
            "solo_ok", "fee", "prize_pool", "perks", "themes", "reg_deadline", "submit_deadline",
            "event_start", "event_end", "eligibility_text", "url", "source", "first_seen", "note"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS hacks (
  id TEXT PRIMARY KEY, dedupe_key TEXT UNIQUE NOT NULL, name TEXT, organiser TEXT, platform TEXT,
  mode TEXT, city TEXT, team_min INTEGER, team_max INTEGER, solo_ok INTEGER, fee TEXT, prize_pool TEXT,
  perks TEXT, themes TEXT, reg_deadline TEXT, submit_deadline TEXT, event_start TEXT, event_end TEXT,
  eligibility_text TEXT, url TEXT, source TEXT, first_seen TEXT, status TEXT DEFAULT 'new', score INTEGER,
  score_reason TEXT, note TEXT, also_seen TEXT DEFAULT '', reg_event_id TEXT, submit_event_id TEXT
);
"""


def data_dir(arg=None):
    d = arg or os.environ.get("HACKHUNT_DIR")
    if not d:
        d = "C:/Users/DELL/HackHunt" if os.path.isdir("C:/Users/DELL") else os.path.expanduser("~/HackHunt")
    return d


def connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _norm_text(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.sub(r"[^a-z0-9+#]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y")


def iso_date(s):
    """Return YYYY-MM-DD for a recognised date or datetime string, else ''. Never guesses a missing year."""
    s = (str(s) if s is not None else "").strip()
    if not s:
        return ""
    s = re.sub(r"\bSept\b", "Sep", s)
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ]", s)          # 2026-10-31T12:00:00Z
    if m:
        s = m.group(1)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def dedupe_key(name, event_start):
    return "|".join([_norm_text(name), iso_date(event_start)[:7]])


def _int_or_none(v):
    if v in (None, ""):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def normalise(raw):
    """Map a raw hackathon dict (from any fetcher or hand-made) to the schema. Raises ValueError if unusable."""
    name = (raw.get("name") or "").strip()
    if not name:
        raise ValueError("hackathon needs a name: %r" % {k: raw.get(k) for k in ("name", "url")})
    mode = (raw.get("mode") or "").strip().lower()
    if mode and mode not in MODES:
        raise ValueError("mode must be one of %s, got %r" % (MODES, mode))
    tmin, tmax = _int_or_none(raw.get("team_min")), _int_or_none(raw.get("team_max"))
    solo = raw.get("solo_ok")
    if isinstance(solo, str):
        solo = {"yes": True, "true": True, "1": True, "no": False, "false": False, "0": False}.get(solo.strip().lower())
    if solo is None and tmin is not None:
        solo = tmin <= 1
    start = iso_date(raw.get("event_start"))
    key = dedupe_key(name, start)
    themes = raw.get("themes") or ""
    if isinstance(themes, (list, tuple)):
        themes = ", ".join(str(t) for t in themes)
    return {
        "id": hashlib.sha1(key.encode("utf-8")).hexdigest()[:10],
        "dedupe_key": key,
        "name": name,
        "organiser": (raw.get("organiser") or "").strip(),
        "platform": (raw.get("platform") or "manual").strip(),
        "mode": mode,
        "city": (raw.get("city") or "").strip(),
        "team_min": tmin, "team_max": tmax,
        "solo_ok": None if solo is None else int(bool(solo)),
        "fee": (str(raw.get("fee")).strip() if raw.get("fee") not in (None, "") else ""),
        "prize_pool": (str(raw.get("prize_pool")).strip() if raw.get("prize_pool") not in (None, "") else ""),
        "perks": (raw.get("perks") or "").strip(),
        "themes": themes.strip(),
        "reg_deadline": iso_date(raw.get("reg_deadline")),
        "submit_deadline": iso_date(raw.get("submit_deadline")),
        "event_start": start,
        "event_end": iso_date(raw.get("event_end")),
        "eligibility_text": _strip_html(raw.get("eligibility_text"))[:5000],
        "url": (raw.get("url") or "").strip(),
        "source": (raw.get("source") or raw.get("platform") or "manual").strip(),
        "first_seen": raw.get("first_seen") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


_INSERT = ("INSERT INTO hacks (id,dedupe_key,name,organiser,platform,mode,city,team_min,team_max,solo_ok,fee,"
           "prize_pool,perks,themes,reg_deadline,submit_deadline,event_start,event_end,eligibility_text,url,"
           "source,first_seen) VALUES (:id,:dedupe_key,:name,:organiser,:platform,:mode,:city,:team_min,"
           ":team_max,:solo_ok,:fee,:prize_pool,:perks,:themes,:reg_deadline,:submit_deadline,:event_start,"
           ":event_end,:eligibility_text,:url,:source,:first_seen)")
# On a duplicate, only fill fields that are still empty (first record wins; later sources add facts, not overwrite).
_FILLABLE = ("organiser", "mode", "city", "team_min", "team_max", "solo_ok", "fee", "prize_pool", "perks", "themes",
             "reg_deadline", "submit_deadline", "event_start", "event_end", "eligibility_text", "url")


def _find_duplicate(con, h):
    """Same dedupe_key, or same name when either side has no known start month (Unstop rows often lack dates)."""
    row = con.execute("SELECT * FROM hacks WHERE dedupe_key=?", (h["dedupe_key"],)).fetchone()
    if row:
        return row
    name, _, month = h["dedupe_key"].rpartition("|")
    if month:
        return con.execute("SELECT * FROM hacks WHERE dedupe_key=?", (name + "|",)).fetchone()
    for row in con.execute("SELECT * FROM hacks").fetchall():     # new row has no month: match any month
        if row["dedupe_key"].rpartition("|")[0] == name:
            return row
    return None


def add_hacks(con, raws):
    """Insert normalised hackathons. Duplicates keep the first record, gain empty fields, and note the new source."""
    added, dup, bad = [], [], []
    for raw in raws:
        try:
            h = normalise(raw)
        except (ValueError, AttributeError, TypeError) as e:
            bad.append("%s: %s" % (type(e).__name__, e))
            continue
        row = _find_duplicate(con, h)
        if row:
            seen = set(filter(None, row["also_seen"].split(",")))
            if h["platform"] != row["platform"]:
                seen.add(h["platform"])
            fills = {f: h[f] for f in _FILLABLE if row[f] in (None, "") and h[f] not in (None, "")}
            sets = ["also_seen=:also_seen"] + ["%s=:%s" % (f, f) for f in fills]
            con.execute("UPDATE hacks SET %s WHERE id=:id" % ", ".join(sets),
                        dict(fills, also_seen=",".join(sorted(seen)), id=row["id"]))
            dup.append(row["id"])
            continue
        con.execute(_INSERT, h)
        added.append(h["id"])
    con.commit()
    return {"added": len(added), "duplicates": len(dup), "invalid": len(bad), "added_ids": added, "errors": bad}


def set_status(con, hid, new, note=None):
    if new not in STATUSES:
        raise ValueError("unknown status %r; use one of %s" % (new, STATUSES))
    row = con.execute("SELECT status FROM hacks WHERE id=?", (hid,)).fetchone()
    if not row:
        raise KeyError("no hackathon with id %s" % hid)
    old = row["status"]
    if new != old and new not in TRANSITIONS[old]:
        raise ValueError("cannot move %s -> %s (allowed: %s)" % (old, new, sorted(TRANSITIONS[old]) or "none"))
    con.execute("UPDATE hacks SET status=?, note=COALESCE(?, note) WHERE id=?", (new, note, hid))
    con.commit()
    return {"id": hid, "from": old, "to": new}


def set_score(con, hid, score, reason=""):
    if not 0 <= int(score) <= 100:
        raise ValueError("score must be 0-100")
    cur = con.execute("UPDATE hacks SET score=?, score_reason=? WHERE id=?", (int(score), reason, hid))
    if cur.rowcount == 0:
        raise KeyError("no hackathon with id %s" % hid)
    con.commit()
    return {"id": hid, "score": int(score)}


def set_eligibility(con, hid, text):
    """Replace the stored eligibility/team sentence (the exact quote shown in the shortlist)."""
    cur = con.execute("UPDATE hacks SET eligibility_text=? WHERE id=?", (_strip_html(text)[:5000], hid))
    if cur.rowcount == 0:
        raise KeyError("no hackathon with id %s" % hid)
    con.commit()
    return {"id": hid, "eligibility_text": _strip_html(text)[:5000]}


def set_notion_ids(con, hid, reg=None, submit=None):
    cur = con.execute("UPDATE hacks SET reg_event_id=COALESCE(?, reg_event_id), "
                      "submit_event_id=COALESCE(?, submit_event_id) WHERE id=?", (reg, submit, hid))
    if cur.rowcount == 0:
        raise KeyError("no hackathon with id %s" % hid)
    con.commit()
    return {"id": hid, "reg_event_id": reg, "submit_event_id": submit}


def _clean(rows, with_text=False):
    out = [dict(r) for r in rows]
    for r in out:
        r.pop("dedupe_key", None)
        if not with_text:
            r["eligibility_text"] = (r["eligibility_text"] or "")[:300]
    return out


def list_hacks(con, status=None, limit=50, with_text=False):
    q = "SELECT * FROM hacks" + (" WHERE status=?" if status else "")
    q += " ORDER BY COALESCE(score,-1) DESC, first_seen DESC LIMIT ?"
    return _clean(con.execute(q, ([status] if status else []) + [limit]).fetchall(), with_text)


def due(con, days=7, today=None):
    """Hackathons still in play whose reg or submit deadline falls in [today, today+days]. Soonest first."""
    today = today or date.today()
    end = today + timedelta(days=days)
    marks = ",".join("?" * len(OPEN_STATUSES))
    rows = con.execute("SELECT * FROM hacks WHERE status IN (%s)" % marks, OPEN_STATUSES).fetchall()
    out = []
    for r in _clean(rows, True):
        # a reg deadline only matters before registering; the submit deadline always counts
        # (Devpost rows have only a submit date, so a 'new' row with one is still reported)
        kinds = [("reg_deadline", r["reg_deadline"])] if r["status"] != "registered" else []
        kinds.append(("submit_deadline", r["submit_deadline"]))
        for kind, d in kinds:
            if not d:
                continue
            dd = date.fromisoformat(d)
            if today <= dd <= end:
                out.append({"id": r["id"], "name": r["name"], "status": r["status"], "kind": kind, "date": d,
                            "days_left": (dd - today).days, "url": r["url"]})
    return sorted(out, key=lambda x: (x["date"], x["name"]))


def export_csv(con, path):
    rows = con.execute("SELECT * FROM hacks ORDER BY first_seen, name").fetchall()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel reads UTF-8
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            d = dict(r)
            d["solo_ok"] = "" if d["solo_ok"] is None else ("yes" if d["solo_ok"] else "no")
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
    du = sub.add_parser("due")
    du.add_argument("--days", type=int, default=7)
    el = sub.add_parser("elig")
    el.add_argument("id")
    el.add_argument("text")
    nt = sub.add_parser("notion")
    nt.add_argument("id")
    nt.add_argument("--reg")
    nt.add_argument("--submit")
    sub.add_parser("export")
    a = p.parse_args(argv)

    d = data_dir(a.data)
    con = connect(os.path.join(d, "hacks.db"))
    try:
        if a.cmd == "init":
            res = {"ok": True, "db": os.path.join(d, "hacks.db")}
        elif a.cmd == "add":
            data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
            res = add_hacks(con, data if isinstance(data, list) else [data])
        elif a.cmd == "list":
            res = list_hacks(con, a.status, a.limit)
        elif a.cmd == "show":
            res = next((r for r in list_hacks(con, None, 100000, with_text=True) if r["id"] == a.id), None)
            if res is None:
                raise KeyError("no hackathon with id %s" % a.id)
        elif a.cmd == "status":
            res = set_status(con, a.id, a.new, a.note)
        elif a.cmd == "score":
            res = set_score(con, a.id, a.score, a.reason)
        elif a.cmd == "elig":
            res = set_eligibility(con, a.id, a.text)
        elif a.cmd == "due":
            res = due(con, a.days)
        elif a.cmd == "notion":
            res = set_notion_ids(con, a.id, a.reg, a.submit)
        elif a.cmd == "export":
            res = export_csv(con, os.path.join(d, "tracker.csv"))
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1
    finally:
        con.close()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
