"""Fetch public job postings from Greenhouse, Lever and Ashby boards listed in companies.yaml. Stdlib only.

Usage:
  py -3 fetch_ats.py [--companies FILE] [--only slug1,slug2] [--all] [--keyword intern,trainee] > jobs.json

Prints one JSON list of raw job dicts (feed it to `jobs_db.py add`). By default only titles that match an
internship keyword are kept; --all keeps everything. Errors per company go to stderr and the run continues.
Uses the public, no-login board APIs. One request per company, sequential, with a short pause.

companies.yaml (simple subset of YAML, parsed here without PyYAML):
  companies:
    - name: Figma
      ats: greenhouse        # greenhouse | lever | ashby
      slug: figma
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_COMPANIES = os.path.join(os.environ.get("JOBHUNT_DIR") or "C:/Users/DELL/JobHunt", "companies.yaml")
DEFAULT_KEYWORDS = ["intern", "internship", "trainee", "co-op", "working student", "student", "graduate"]
URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


def load_companies(path):
    """Parse the `- key: value` list subset of YAML. Raises ValueError on a bad entry."""
    items, cur = [], None
    with open(path, encoding="utf-8-sig") as f:
        for n, line in enumerate(f, 1):
            line = line.split(" #")[0].rstrip() if not line.lstrip().startswith("#") else ""
            if not line.strip() or line.strip() == "companies:":
                continue
            m = re.match(r"^\s*(-\s+)?([A-Za-z_]+):\s*(.*)$", line)
            if not m:
                raise ValueError("%s:%d cannot parse %r" % (path, n, line))
            if m.group(1):
                cur = {}
                items.append(cur)
            if cur is None:
                raise ValueError("%s:%d key before first '- ' entry" % (path, n))
            cur[m.group(2)] = m.group(3).strip().strip("'\"")
    for c in items:
        if c.get("ats") not in URLS or not c.get("slug"):
            raise ValueError("bad company entry (need ats in %s and slug): %r" % (sorted(URLS), c))
        c.setdefault("name", c["slug"])
    return items


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def parse_greenhouse(data, company):
    out = []
    for j in data.get("jobs", []):
        out.append({"source": "greenhouse", "company": j.get("company_name") or company,
                    "title": j.get("title"), "location": (j.get("location") or {}).get("name", ""),
                    "url": j.get("absolute_url"), "description": _clean(j.get("content")),
                    "deadline": j.get("application_deadline") or "", "first_seen": (j.get("first_published") or "")[:10] or None})
    return out


def parse_lever(data, company):
    out = []
    for j in data:
        cat = j.get("categories") or {}
        loc = cat.get("location") or ""
        if not loc and j.get("country"):
            loc = j["country"]
        out.append({"source": "lever", "company": company, "title": j.get("text"), "location": loc,
                    "remote": True if j.get("workplaceType") == "remote" else None,
                    "url": j.get("hostedUrl"), "description": j.get("descriptionPlain") or _clean(j.get("description"))})
    return out


def parse_ashby(data, company):
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        out.append({"source": "ashby", "company": company, "title": j.get("title"), "location": j.get("location") or "",
                    "remote": True if j.get("isRemote") else None, "url": j.get("jobUrl"),
                    "description": j.get("descriptionPlain") or _clean(j.get("descriptionHtml")),
                    "first_seen": (j.get("publishedAt") or "")[:10] or None})
    return out


PARSERS = {"greenhouse": parse_greenhouse, "lever": parse_lever, "ashby": parse_ashby}


def keep(job, keywords):
    title = (job.get("title") or "").lower()
    return any(re.search(r"\b" + re.escape(k.lower()) + r"\b", title) for k in keywords)


def fetch_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "jobhunt-personal/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_company(c, keywords, keep_all=False, fetcher=fetch_json):
    data = fetcher(URLS[c["ats"]].format(slug=c["slug"]))
    jobs = PARSERS[c["ats"]](data, c["name"])
    return jobs if keep_all else [j for j in jobs if keep(j, keywords)]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--companies", default=DEFAULT_COMPANIES)
    p.add_argument("--only", help="comma-separated slugs to fetch")
    p.add_argument("--all", action="store_true", help="keep non-internship titles too")
    p.add_argument("--keyword", help="comma-separated title keywords (replaces the default list)")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between companies")
    a = p.parse_args(argv)
    try:
        companies = load_companies(a.companies)
    except (OSError, ValueError) as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1
    if a.only:
        want = set(a.only.split(","))
        companies = [c for c in companies if c["slug"] in want]
    keywords = a.keyword.split(",") if a.keyword else DEFAULT_KEYWORDS
    jobs, failed = [], 0
    for i, c in enumerate(companies):
        if i:
            time.sleep(a.pause)
        try:
            got = fetch_company(c, keywords, a.all)
            print("%s (%s/%s): %d jobs" % (c["name"], c["ats"], c["slug"], len(got)), file=sys.stderr)
            jobs += got
        except (urllib.error.URLError, OSError, ValueError) as e:
            failed += 1
            print("%s (%s/%s): FAILED %s" % (c["name"], c["ats"], c["slug"], e), file=sys.stderr)
    json.dump(jobs, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if failed and not jobs else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
