"""Fetch internship listings from the Adzuna API. Stdlib only.

Usage:
  set ADZUNA_APP_ID / ADZUNA_APP_KEY in your environment (never in files), then:
  py -3 fetch_adzuna.py [--countries in,us,gb,de,sg] [--what "software intern"] [--pages 2] > jobs.json

Prints a JSON list of raw job dicts (feed it to `jobs_db.py add`). Free-tier friendly: few pages, pauses.
Countries are Adzuna codes: in=India, us, gb, de, sg. Run `--what "machine learning intern"` for other queries.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
CURRENCY = {"in": "INR", "us": "USD", "gb": "GBP", "de": "EUR", "sg": "SGD"}


def stipend_text(r, country):
    lo, hi = r.get("salary_min"), r.get("salary_max")
    if not lo and not hi:
        return ""
    cur = CURRENCY.get(country, "")
    est = " (estimated)" if str(r.get("salary_is_predicted")) == "1" else ""
    if lo and hi and round(lo) != round(hi):
        return "%s %d-%d per year%s" % (cur, lo, hi, est)
    return "%s %d per year%s" % (cur, lo or hi, est)


def parse_results(data, country):
    out = []
    for r in data.get("results", []):
        out.append({"source": "adzuna-" + country, "title": r.get("title"),
                    "company": (r.get("company") or {}).get("display_name"),
                    "location": (r.get("location") or {}).get("display_name", ""),
                    "url": r.get("redirect_url"), "description": r.get("description", ""),
                    "stipend": stipend_text(r, country), "first_seen": (r.get("created") or "")[:10] or None})
    return out


def fetch_page(country, page, what, app_id, app_key, timeout=30):
    q = urllib.parse.urlencode({"app_id": app_id, "app_key": app_key, "results_per_page": 50, "what": what,
                                "content-type": "application/json"})
    url = API.format(country=country, page=page) + "?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "jobhunt-personal/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--countries", default="in,us,gb,de,sg")
    p.add_argument("--what", default="software intern")
    p.add_argument("--pages", type=int, default=2)
    p.add_argument("--pause", type=float, default=1.0)
    a = p.parse_args(argv)
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print(json.dumps({"ok": False, "error": "missing_keys",
                          "detail": "Set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables "
                                    "(free keys: developer.adzuna.com). Never put them in files."}), file=sys.stderr)
        return 2
    jobs, failed, calls = [], 0, 0
    for country in a.countries.split(","):
        for page in range(1, a.pages + 1):
            if calls:
                time.sleep(a.pause)
            calls += 1
            try:
                got = parse_results(fetch_page(country, page, a.what, app_id, app_key), country)
            except (urllib.error.URLError, OSError, ValueError) as e:
                failed += 1
                # never echo the URL: it carries the key
                print("adzuna %s page %d: FAILED %s" % (country, page, type(e).__name__ + ": " + str(e).replace(app_key, "***")),
                      file=sys.stderr)
                break
            print("adzuna %s page %d: %d jobs" % (country, page, len(got)), file=sys.stderr)
            jobs += got
            if len(got) < 50:
                break
    json.dump(jobs, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if failed and not jobs else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
