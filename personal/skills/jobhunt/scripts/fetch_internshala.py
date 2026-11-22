"""Fetch internship cards from Internshala's public category pages and print raw job dicts for `jobs_db.py add`.
Stdlib only (html.parser).

Usage:
  py -3 fetch_internshala.py [--category computer-science] [--pages 3] [--delay 3] > internshala.json

Page 1 is https://internshala.com/internships/<category>-internship/ and later pages are
.../<category>-internship/page-N/ (read from the pagination links). Rate rules (jobhunt SKILL.md rule 3): at most
3 pages per run (clamped in code), at least 3 s between pages, never log in. A page with no cards that looks like a
block page (CAPTCHA, "unusual traffic", Cloudflare, HTTP 403/429) stops the run with an error. The word "recaptcha"
alone does not count: normal pages carry a login-form key. Cards show no application deadline, so `deadline` stays
empty; duration, skills and posted age go into `description`.
Errors go to stderr as JSON; exit 1 on failure.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = "https://internshala.com"
UA = "Mozilla/5.0 (personal job finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
MAX_PAGES = 3
MIN_DELAY = 3.0
BLOCKED = re.compile(r"unusual traffic|verify (that )?you are (a )?human|are you a robot|just a moment|"
                     r"access denied|captcha (challenge|verification)|g-recaptcha-response|px-captcha", re.I)


class Blocked(Exception):
    pass


VOID = ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr")

class _Cards(HTMLParser):
    """Collect one dict per `individual_internship` card plus the page's pagination state.

    Depth is the length of a stack of counted (non-void, non-self-closing) open tags inside the current card.
    An end tag pops only if a matching counted start tag is open, so `<img />`, `<br>` and stray end tags
    cannot unbalance the depth.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self.is_last = None
        self._cur = None
        self._stack = []
        self._cap = None          # (field, depth outside the element) while collecting text

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, counted=False)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, counted=tag not in VOID)

    def _open(self, tag, attrs, counted):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "input" and a.get("id") == "isLastPage":
            self.is_last = a.get("value") == "1"
        if self._cur is None:
            if tag == "div" and "individual_internship" in cls and counted:
                self._cur = {"href": a.get("data-href") or "", "title": "", "company": "", "location": "",
                             "stipend": "", "duration": "", "posted": "", "skills": [], "about": "",
                             "wfh": False}
                self._stack = ["div"]
            return
        c = self._cur
        outside = len(self._stack)
        if counted:
            self._stack.append(tag)
        field = None
        if tag == "a" and "job-title-href" in cls:
            field = "title"
            c["href"] = c["href"] or a.get("href") or ""
        elif tag == "p" and "company-name" in cls:
            field = "company"
        elif tag == "span" and "stipend" in cls:
            field = "stipend"
        elif tag == "div" and "job_skill" in cls:
            field = "skill"
        elif tag == "div" and "text" in cls:
            field = "about"
        elif tag == "div" and "locations" in cls:
            field = "location"
        elif tag == "div" and {"status-success", "status-info", "status-inactive"} & set(cls):
            field = "posted"
        elif tag == "i" and "ic-16-calendar" in cls:
            c["_next_duration"] = True
        elif tag == "span" and c.get("_next_duration"):
            field = "duration"
            c["_next_duration"] = False
        if tag == "i" and "ic-16-home" in cls:
            c["wfh"] = True
        if field and counted and self._cap is None:
            self._cap = (field, outside)
            c["_buf"] = []

    def handle_endtag(self, tag):
        if self._cur is None or tag not in self._stack:
            return                       # stray end tag, or void tag: nothing was counted for it
        while self._stack and self._stack.pop() != tag:
            pass                         # also closes unclosed inner tags such as <li> or <p>
        depth = len(self._stack)
        if self._cap and depth <= self._cap[1]:
            field, _ = self._cap
            text = re.sub(r"\s+", " ", "".join(self._cur.pop("_buf", []))).strip()
            if field == "skill":
                if text:
                    self._cur["skills"].append(text)
            elif field == "posted":
                self._cur["posted"] = self._cur["posted"] or text
            else:
                self._cur[field] = self._cur[field] or text
            self._cap = None
        if depth == 0:
            self.cards.append(self._cur)
            self._cur = None
            self._cap = None

    def handle_data(self, data):
        if self._cur is not None and self._cap:
            self._cur["_buf"].append(data)


def parse_cards(page):
    p = _Cards()
    p.feed(page)
    p.close()
    return p.cards, p.is_last


def to_jobs(cards):
    out = []
    for c in cards:
        if not c["title"] or not c["company"]:
            continue
        loc = c["location"]
        remote = c["wfh"] or bool(re.search(r"work from home", loc, re.I))
        bits = []
        if c["duration"]:
            bits.append("Duration: " + c["duration"])
        if c["skills"]:
            bits.append("Skills: " + ", ".join(c["skills"]))
        if c["posted"]:
            bits.append("Posted: " + c["posted"])
        if c["about"]:
            bits.append(c["about"])
        out.append({
            "title": c["title"],
            "company": c["company"],
            "location": loc,
            "remote": remote,
            "stipend": c["stipend"],
            "deadline": "",
            "url": urllib.parse.urljoin(BASE + "/", c["href"]) if c["href"] else "",
            "description": ". ".join(bits),
            "source": "internshala",
        })
    return out


def check_blocked(page, n_cards):
    """Raise Blocked for a page with no cards that looks like a CAPTCHA / bot wall. 'recaptcha' alone is ignored."""
    if n_cards == 0 and BLOCKED.search(page):
        raise Blocked("block page (CAPTCHA, unusual traffic or Cloudflare challenge): stopped, do not retry today")


def page_url(category, page):
    path = "/internships/%s-internship/" % category
    return BASE + path + ("page-%d/" % page if page > 1 else "")


def fetch_page(category, page, fetcher=None):
    url = page_url(category, page)
    if fetcher:
        return fetcher(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise Blocked("HTTP %d from Internshala: stopped, do not retry today" % e.code)
        raise


def check_category(category):
    if not re.fullmatch(r"[a-z0-9-]+", category or ""):
        raise ValueError("category must match ^[a-z0-9-]+$ (the URL slug before '-internship')")
    return category


def fetch_all(category="computer-science", pages=MAX_PAGES, delay=MIN_DELAY, fetcher=None):
    check_category(category)
    pages = max(1, min(int(pages), MAX_PAGES))
    delay = max(float(delay), MIN_DELAY)
    out = []
    for p in range(1, pages + 1):
        page = fetch_page(category, p, fetcher)
        cards, is_last = parse_cards(page)
        check_blocked(page, len(cards))
        if p == 1 and not cards:
            raise RuntimeError("layout changed or empty: page 1 has no internship cards")
        out.extend(to_jobs(cards))
        if not cards or is_last:
            break
        if p < pages:
            time.sleep(delay)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", default="computer-science", help="URL slug before '-internship' (default computer-science)")
    ap.add_argument("--pages", type=int, default=MAX_PAGES, help="listing pages (default and maximum 3)")
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between pages (minimum 3)")
    a = ap.parse_args(argv)
    try:
        rows = fetch_all(a.category, a.pages, a.delay)
    except Exception as e:  # network, block page or layout change: report, do not invent rows
        print(json.dumps({"ok": False, "source": "internshala", "error": "%s: %s" % (type(e).__name__, e)}), file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
