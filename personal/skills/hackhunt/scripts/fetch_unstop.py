"""Fetch open hackathons from Unstop's public search JSON and print raw hackathon dicts for `hacks_db.py add`.
Stdlib only.

Usage:
  py -3 fetch_unstop.py [--pages 2] [--delay 2] > unstop.json

Endpoint (no login): https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&oppstatus=open
Rate rules (hackhunt SKILL.md rule 3): default 2 pages, at most 3 per run (clamped in code), at least 2 s between pages,
stop at the last page. Unstop has no event-start field, so `event_start` stays empty. `eligibility_text` holds the
listing's eligibility tags only (not a quoted rule sentence): read the detail page before ranking.
Errors go to stderr as JSON; exit 1 on failure.
"""
import argparse
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://unstop.com/api/public/opportunity/search-result"
UA = "Mozilla/5.0 (personal hackathon finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
MAX_PAGES = 3
DEFAULT_PAGES = 2   # leaves 1 of the 3 loads per site (rule 3) for a detail page
MIN_DELAY = 2.0
PER_PAGE = 15


def _date(s):
    """'2026-12-16T00:00:00+05:30' -> '2026-12-16' (the date part as Unstop shows it); '' if absent."""
    m = re.match(r"\d{4}-\d{2}-\d{2}", s or "")
    return m.group(0) if m else ""


def _num(v):
    """Safe number: 150000, 1.5, '1,50,000' -> number; None, bool, junk, NaN, inf -> None. Never raises."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str):
        try:
            v = float(v.replace(",", "").replace("₹", "").strip())
        except ValueError:
            return None
    if not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return int(v) if v == int(v) else float(v)


def _money(n):
    return "{:,}".format(n)


def _dicts(seq):
    return [x for x in seq or [] if isinstance(x, dict)] if isinstance(seq, list) else []


def _prize_pool(prizes):
    cash = [(p, _num(p.get("cash"))) for p in _dicts(prizes) if p.get("prize_type") == "cash"]
    cash = [(p, n) for p, n in cash if n and n > 0]
    if not cash:
        return ""
    sym = "₹" if all(p.get("currency") == "fa-rupee" for p, _ in cash) else ""
    return sym + _money(sum(n for _, n in cash))


def _perks(prizes):
    out = []
    for p in _dicts(prizes):
        if p.get("prize_type") == "kind" and p.get("others"):
            out.append(str(p["others"]).strip())
        if p.get("pre_placement_internship"):
            out.append("pre-placement internship")
        if p.get("pre_placement_opportunity"):
            out.append("pre-placement opportunity")
    return "; ".join(dict.fromkeys(out))


def _fee(item):
    amounts = [n for n in (_num(s.get("amount")) for s in _dicts(item.get("payment_services"))) if n and n > 0]
    if amounts:
        return "₹" + _money(min(amounts))
    return "paid" if item.get("isPaid") else ""


def _city(item):
    locs = [x for x in item.get("locations") or [] if isinstance(x, str) and x.strip()]
    if locs:
        return ", ".join(locs)
    return ((item.get("address_with_country_logo") or {}).get("city") or "").strip()


def _int(v):
    n = _num(v)
    return None if n is None else int(n)


def parse_items(data):
    """Map Unstop's response ({"data": {"data": [...], "last_page": N}}) to raw hackathon dicts."""
    out = []
    for it in _dicts((data.get("data") or {}).get("data")):
        req = it.get("regnRequirements") or {}
        tmin, tmax = _int(req.get("min_team_size")), _int(req.get("max_team_size"))
        region = (it.get("region") or "").strip().lower()
        filters = [f.get("name", "") for f in _dicts(it.get("filters")) if f.get("type") == "eligible" and f.get("name")]
        other = [f.get("name", "") for f in _dicts(it.get("filters")) if f.get("type") != "eligible" and f.get("name")]
        skills = [s.get("skill_name") or s.get("skill") or "" for s in _dicts(it.get("required_skills"))]
        row = {
            "name": it.get("title") or "",
            "organiser": (it.get("organisation") or {}).get("name") or "",
            "platform": "unstop",
            "mode": region if region in ("online", "offline", "hybrid") else "",
            "city": _city(it),
            "fee": _fee(it),
            "prize_pool": _prize_pool(it.get("prizes")),
            "perks": _perks(it.get("prizes")),
            "themes": [x for x in other + skills if x],
            "reg_deadline": _date(req.get("end_regn_dt")),
            "event_end": _date(it.get("end_date")),
            "eligibility_text": ("Open to (listing tags): " + ", ".join(filters)) if filters else "",
            "url": it.get("seo_url") or "",
            "source": "unstop",
        }
        if tmin is not None:
            row["team_min"] = tmin
            row["solo_ok"] = tmin == 1
        if tmax is not None:
            row["team_max"] = tmax
        out.append(row)
    return out


def fetch_page(page, fetcher=None):
    q = urllib.parse.urlencode([("opportunity", "hackathons"), ("oppstatus", "open"), ("page", page),
                                ("per_page", PER_PAGE)])
    url = API + "?" + q
    if fetcher:
        return fetcher(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_all(pages=DEFAULT_PAGES, delay=MIN_DELAY, fetcher=None):
    pages = max(1, min(int(pages), MAX_PAGES))
    delay = max(float(delay), MIN_DELAY)
    out = []
    for p in range(1, pages + 1):
        data = fetch_page(p, fetcher)
        rows = parse_items(data)
        out.extend(rows)
        last = _int((data.get("data") or {}).get("last_page")) or p
        if not rows or p >= last:
            break
        if p < pages:
            time.sleep(delay)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=DEFAULT_PAGES, help="listing pages of 15 (default 2, maximum 3)")
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between pages (minimum 2)")
    a = ap.parse_args(argv)
    try:
        rows = fetch_all(a.pages, a.delay)
    except Exception as e:  # network, HTTP or JSON shape change: report, do not invent rows
        print(json.dumps({"ok": False, "source": "unstop", "error": "%s: %s" % (type(e).__name__, e)}), file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
