"""Cloudflare fallback: fetch ONE public page with Scrapling's StealthyFetcher (real Chrome) and print its text or HTML.

Use it only when a plain urllib fetcher is blocked by a Cloudflare challenge ("Just a moment"). It is the only
place in this skill that uses Scrapling.

Run with the Scrapling venv Python (NOT `py -3`):
  C:/Users/DELL/.claude/tools/scrape-venv/Scripts/python.exe stealth_fetch.py URL [--text|--html]

  --text  (default) page text with tags, scripts and styles removed
  --html  the page HTML

Rules: one URL per call; public listing and detail/rules pages only. The code refuses linkedin.com, naukri.com
(and subdomains) and any path containing login, signin, signup, register or apply. It needs system Chrome (`real_chrome=True`): the bundled Playwright Chromium fails on this PC with a
"side-by-side configuration" error. Takes about 15-20 s because the challenge must finish. Errors go to stderr
as JSON; exit 1 on failure.
"""
import argparse
import html
import json
import re
import sys
import urllib.parse

TIMEOUT_MS = 90000


def html_to_text(page):
    """Strip scripts, styles and tags; decode entities; drop blank lines. Keeps one line break per block tag."""
    t = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", page or "", flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"</?(p|div|br|li|ul|ol|h[1-6]|tr|section|article|header|footer)\b[^>]*>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    lines = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in t.split("\n"))
    return "\n".join(ln for ln in lines if ln)


BANNED_HOSTS = ("linkedin.com", "naukri.com")
BANNED_PATH = re.compile(r"login|sign-?in|sign-?up|register|apply", re.I)


def check_url(url):
    """Raise ValueError for a URL this tool must never open: LinkedIn/Naukri, or a login/register/apply path."""
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower().rstrip(".")
    if p.scheme not in ("http", "https") or not host:
        raise ValueError("url must start with http:// or https://")
    if any(host == b or host.endswith("." + b) for b in BANNED_HOSTS):
        raise ValueError("refused: LinkedIn and Naukri pages are never opened (%s)" % host)
    if BANNED_PATH.search(urllib.parse.unquote(p.path)):
        raise ValueError("refused: login, signin, signup, register and apply pages are never opened (%s)" % p.path)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="one http(s) URL")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--text", action="store_true", help="print page text (default)")
    g.add_argument("--html", action="store_true", help="print page HTML")
    a = ap.parse_args(argv)
    try:
        check_url(a.url)
    except ValueError as e:
        ap.error(str(e))
    return a


def fetch_html(url):
    check_url(url)
    try:
        from scrapling.fetchers import StealthyFetcher  # lazy: only the scrape venv has it
    except ImportError:
        raise RuntimeError("scrapling is not installed in this Python. Use the scrape venv: "
                           "C:/Users/DELL/.claude/tools/scrape-venv/Scripts/python.exe "
                           '(setup: py -3 -m venv ~/.claude/tools/scrape-venv; then pip install "scrapling[fetchers]")')
    page = StealthyFetcher.fetch(url, headless=True, real_chrome=True, solve_cloudflare=True,
                                 network_idle=True, timeout=TIMEOUT_MS)
    status = getattr(page, "status", 200)
    if status and status >= 400:
        raise RuntimeError("HTTP %s from %s" % (status, url))
    return str(page.html_content)


def main(argv=None):
    a = parse_args(argv)
    try:
        page = fetch_html(a.url)
    except Exception as e:
        print(json.dumps({"ok": False, "source": "stealth_fetch", "url": a.url, "error": "%s: %s" % (type(e).__name__, e)}),
              file=sys.stderr)
        return 1
    print(page if a.html else html_to_text(page))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
