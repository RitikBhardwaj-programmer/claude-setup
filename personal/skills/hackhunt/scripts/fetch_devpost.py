"""Fetch open and upcoming hackathons from Devpost's public listing JSON (unofficial endpoint) and print raw
hackathon dicts for `hacks_db.py add`. Stdlib only.

Usage:
  py -3 fetch_devpost.py [--pages 3] [--delay 2] > devpost.json

Devpost robots.txt allows /api/. Listing JSON has no team size, fee or eligibility: those stay empty and the
skill must read the hackathon's own page (rules) before ranking. Errors go to stderr as JSON; exit 1 on failure.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

API = "https://devpost.com/api/hackathons"
UA = "Mozilla/5.0 (personal hackathon finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"


def _d(month, day, year):
    return datetime.strptime("%s %s %s" % (month, int(day), year), "%b %d %Y").strftime("%Y-%m-%d")


def parse_range(text):
    """'Aug 31 - Oct 23, 2026' / 'Oct 05 - 27, 2026' / 'Dec 20, 2026 - Jan 10, 2027' -> (start, end) ISO, or ('','')."""
    t = (text or "").strip()
    m = re.fullmatch(r"(%s) (\d+), (\d{4}) - (%s) (\d+), (\d{4})" % (_MONTHS, _MONTHS), t)
    if m:
        return _d(m[1], m[2], m[3]), _d(m[4], m[5], m[6])
    m = re.fullmatch(r"(%s) (\d+) - (%s) (\d+), (\d{4})" % (_MONTHS, _MONTHS), t)
    if m:
        end = _d(m[3], m[4], m[5])
        start = _d(m[1], m[2], m[5])
        if start > end:                       # "Dec 20 - Jan 10, 2027": the start is in the previous year
            start = _d(m[1], m[2], int(m[5]) - 1)
        return start, end
    m = re.fullmatch(r"(%s) (\d+) - (\d+), (\d{4})" % _MONTHS, t)
    if m:
        return _d(m[1], m[2], m[4]), _d(m[1], m[3], m[4])
    m = re.fullmatch(r"(%s) (\d+), (\d{4})" % _MONTHS, t)
    if m:
        d = _d(m[1], m[2], m[3])
        return d, d
    return "", ""


def parse_prize(html_text):
    """'$<span data-currency-value>138,000</span>' -> '$138,000'. Empty if not present."""
    return re.sub(r"<[^>]+>", "", html_text or "").strip()


def parse_hackathons(data):
    out = []
    for h in data.get("hackathons", []):
        loc = (h.get("displayed_location") or {}).get("location") or ""
        online = loc.strip().lower() == "online"
        start, end = parse_range(h.get("submission_period_dates"))
        out.append({
            "name": h.get("title", ""),
            "organiser": h.get("organization_name") or "",
            "platform": "devpost",
            "mode": "online" if online else ("offline" if loc.strip() else ""),
            "city": "" if online else loc,
            "prize_pool": parse_prize(h.get("prize_amount")),
            "themes": [t.get("name", "") for t in (h.get("themes") or [])],
            "submit_deadline": end,
            "event_start": start,
            "event_end": end,
            "eligibility_text": ("Invite only: " + h["eligibility_requirement_invite_only_description"])
            if h.get("invite_only") and h.get("eligibility_requirement_invite_only_description") else "",
            "url": h.get("url", ""),
            "source": "devpost",
        })
    return out


def fetch_page(page, fetcher=None):
    q = urllib.parse.urlencode([("status[]", "open"), ("status[]", "upcoming"), ("page", page)])
    url = API + "?" + q
    if fetcher:
        return fetcher(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_all(pages=3, delay=2.0, fetcher=None):
    out = []
    for p in range(1, pages + 1):
        data = fetch_page(p, fetcher)
        rows = parse_hackathons(data)
        out.extend(rows)
        if not rows:
            break
        if p < pages:
            time.sleep(delay)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=3, help="listing pages of 9 (default 3)")
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args(argv)
    try:
        rows = fetch_all(a.pages, a.delay)
    except Exception as e:  # network, HTTP or JSON shape change: report, do not invent rows
        print(json.dumps({"ok": False, "source": "devpost", "error": "%s: %s" % (type(e).__name__, e)}), file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
