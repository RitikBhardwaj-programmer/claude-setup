"""Fetch open-for-application hackathons from Devfolio's public search API and print raw hackathon dicts for
`hacks_db.py add`. Stdlib only.

Usage:
  py -3 fetch_devfolio.py [--pages 2] [--size 20] [--delay 2] > devfolio.json

Endpoint (no login): POST https://api.devfolio.co/api/search/hackathons with {"type":"application_open","from":N,"size":S}.
Response: hits.total.value (count) and hits.hits[]._source. Rate rules (hackhunt SKILL.md rule 3): default 2, at most 3 requests
per run (clamped in code), at least 2 s between requests. Dates are converted to the event's own timezone
(`timezone` field, e.g. Asia/Calcutta) before the date part is taken. `fee` and `eligibility_text` come from the
event's FAQ answers when a matching question exists; otherwise they stay empty (never guessed).
Errors go to stderr as JSON; exit 1 on failure.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.devfolio.co/api/search/hackathons"
UA = "Mozilla/5.0 (personal hackathon finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
MAX_PAGES = 3
DEFAULT_PAGES = 2   # leaves 1 of the 3 loads per site (rule 3) for a detail page
MAX_SIZE = 50
MIN_DELAY = 2.0
SIZE = 20

# a fee question must name registration / participation / entry next to fee / cost ("cost for accommodation" is not a fee)
_FEE_Q = re.compile(r"\b(registration|participation|entry)\b[^?.]{0,25}\b(fees?|costs?|charges?|free)\b|"
                    r"\b(fees?|costs?)\b[^?.]{0,25}\b(registration|participation|entry|register)\b", re.I)
_TEAM_Q = re.compile(r"team size|team of|team member|members? per team|how many (people|members)", re.I)
_ELIG_Q = re.compile(r"who can (participate|join|apply)|eligib|open to", re.I)


def _tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:  # no tzdata on this machine: IST is the only zone we can fix by hand
        if name in ("Asia/Calcutta", "Asia/Kolkata"):
            return timezone(timedelta(hours=5, minutes=30))
        return timezone.utc


def _local_date(iso, tzname):
    """'2026-11-13T18:30:00+00:00' + 'Asia/Calcutta' -> '2026-11-14'; '' if absent or unparsable."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).astimezone(_tz(tzname or "UTC")).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _clean(text, cap=300):
    t = re.sub(r"[*_`#]+", "", text or "")
    return re.sub(r"\s+", " ", t).strip()[:cap]


def _faq(faqs, pattern):
    for f in faqs or []:
        if pattern.search(f.get("question") or "") and (f.get("answer") or "").strip():
            return f
    return None


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_hits(data):
    """Map Devfolio's response ({"hits": {"hits": [{"_source": ...}]}}) to raw hackathon dicts."""
    out = []
    for h in ((data.get("hits") or {}).get("hits")) or []:
        s = h.get("_source") or {}
        setting = s.get("hackathon_setting") or {}
        tz = s.get("timezone")
        slug = s.get("slug") or ""
        online = s.get("is_online")
        tmin, tmax = _int(s.get("team_min")), _int(s.get("team_size"))
        faqs = s.get("hackathon_faqs")
        fee_faq, team_faq, elig_faq = _faq(faqs, _FEE_Q), _faq(faqs, _TEAM_Q), _faq(faqs, _ELIG_Q)
        elig = []
        if team_faq:
            elig.append("Team size: " + _clean(team_faq["answer"]))
        if elig_faq:
            elig.append("Who can participate: " + _clean(elig_faq["answer"]))
        host = s.get("hosted_by")
        row = {
            "name": s.get("name") or "",
            "organiser": (host.get("name") if isinstance(host, dict) else host) or "",
            "platform": "devfolio",
            "mode": "online" if online else ("offline" if online is not None else ""),
            "city": "" if online else (s.get("city") or ""),
            "fee": _clean(fee_faq["answer"], 200) if fee_faq else "",
            "themes": [t.get("name", "") for t in (s.get("themes") or []) if t.get("name")],
            "reg_deadline": _local_date(setting.get("reg_ends_at"), tz),
            "event_start": _local_date(s.get("starts_at"), tz),
            "event_end": _local_date(s.get("ends_at"), tz),
            "eligibility_text": " | ".join(elig),
            "url": "https://%s.devfolio.co/overview" % slug if slug else "",
            "source": "devfolio",
        }
        if tmin is not None:
            row["team_min"] = tmin
            row["solo_ok"] = tmin == 1
        if tmax is not None:
            row["team_max"] = tmax
        out.append(row)
    return out


def fetch_page(offset, size, fetcher=None):
    body = {"type": "application_open", "from": offset, "size": size}
    if fetcher:
        return fetcher(API, body)
    req = urllib.request.Request(API, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"User-Agent": UA, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_all(pages=DEFAULT_PAGES, size=SIZE, delay=MIN_DELAY, fetcher=None):
    """`fetcher(url, body)` returns the parsed JSON; tests pass a fake one."""
    pages = max(1, min(int(pages), MAX_PAGES))
    size = max(1, min(int(size), MAX_SIZE))
    delay = max(float(delay), MIN_DELAY)
    out = []
    for p in range(pages):
        data = fetch_page(p * size, size, fetcher)
        rows = parse_hits(data)
        out.extend(rows)
        total = _int(((data.get("hits") or {}).get("total") or {}).get("value"))
        if not rows or (total is not None and (p + 1) * size >= total):
            break
        if p + 1 < pages:
            time.sleep(delay)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=DEFAULT_PAGES, help="API requests (default 2, maximum 3)")
    ap.add_argument("--size", type=int, default=SIZE, help="hits per request (default 20, maximum 50)")
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between requests (minimum 2)")
    a = ap.parse_args(argv)
    try:
        rows = fetch_all(a.pages, a.size, a.delay)
    except Exception as e:  # network, HTTP or JSON shape change: report, do not invent rows
        print(json.dumps({"ok": False, "source": "devfolio", "error": "%s: %s" % (type(e).__name__, e)}), file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
