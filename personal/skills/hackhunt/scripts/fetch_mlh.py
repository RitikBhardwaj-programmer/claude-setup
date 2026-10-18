"""Fetch hackathons from the Major League Hacking season events page and print raw hackathon dicts for
`hacks_db.py add`. Stdlib only.

Usage:
  py -3 fetch_mlh.py [--season 2027] [--country IN] [--all] > mlh.json

The page embeds its data as JSON in <script data-page="app"> (Inertia app): props.upcomingEvents. By default
only events in --country (ISO code, default IN) or fully digital events are kept; --all keeps everything.
MLH lists no team size, fee or reg deadline: those stay empty. Errors go to stderr as JSON; exit 1 on failure.
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import date

UA = "Mozilla/5.0 (personal hackathon finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
FORMAT_MODE = {"physical": "offline", "hybrid_physical": "hybrid", "hybrid": "hybrid", "digital": "online"}
_SCRIPT = re.compile(r'<script data-page="app" type="application/json">(.*?)</script>', re.S)


def default_season(today=None):
    t = today or date.today()
    return t.year + 1 if t.month >= 8 else t.year        # MLH 2027 season runs Aug 2026 - mid 2027


def parse_events(html):
    m = _SCRIPT.search(html)
    if not m:
        raise ValueError("MLH page has no data-page script: page layout changed")
    props = json.loads(m.group(1)).get("props", {})
    if "upcomingEvents" not in props:
        raise ValueError("MLH data has no upcomingEvents: data shape changed")
    return props["upcomingEvents"]


def to_raw(e):
    addr = e.get("venueAddress") or {}
    mode = FORMAT_MODE.get(e.get("formatType"), "")
    path = e.get("url") or ""
    return {
        "name": e.get("name", ""),
        "organiser": "Major League Hacking (MLH member event)",
        "platform": "mlh",
        "mode": mode,
        "city": "" if mode == "online" else ", ".join(x for x in (addr.get("city"), addr.get("state")) if x)
        or e.get("location") or "",
        "themes": (e.get("customFields") or {}).get("hackathon_focus") or [],
        "event_start": (e.get("startsAt") or "")[:10],
        "event_end": (e.get("endsAt") or "")[:10],
        "url": e.get("websiteUrl") or ("https://www.mlh.com" + path if path.startswith("/") else path),
        "source": "mlh",
        "_country": addr.get("country", ""),
    }


def parse_page(html, country="IN", keep_all=False):
    out = []
    for e in parse_events(html):
        r = to_raw(e)
        c = r.pop("_country")
        if keep_all or c == country or r["mode"] == "online":
            out.append(r)
    return out


def fetch_html(season, fetcher=None):
    url = "https://www.mlh.com/seasons/%s/events" % season
    if fetcher:
        return fetcher(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--season", default=str(default_season()))
    ap.add_argument("--country", default="IN")
    ap.add_argument("--all", action="store_true", help="keep events from every country")
    a = ap.parse_args(argv)
    try:
        rows = parse_page(fetch_html(a.season), a.country, a.all)
    except Exception as e:
        print(json.dumps({"ok": False, "source": "mlh", "error": "%s: %s" % (type(e).__name__, e)}), file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
