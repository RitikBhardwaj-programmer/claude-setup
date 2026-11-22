"""Enrich Devpost hackathon rows with team size and eligibility from each event's /rules page. Stdlib only.

Usage:
  py -3 fetch_devpost.py | py -3 fetch_devpost_rules.py [--limit 10] [--delay 2] > devpost_rules.json

Reads a JSON list of raw hackathon dicts on stdin (the output of fetch_devpost.py), fetches `<event url>/rules` for
the first --limit Devpost rows (default 10, at most 20, 2 s pause between pages), and prints the same rows:
  * `team_max` from the page's CSS rule `Team max size: N` (only if the row has none),
  * `eligibility_text` from the numbered "Eligibility" section, tags stripped, capped at 600 characters
    (appended after any text the row already has, such as "Invite only: ...").
A row stays unchanged when its page has no such text, fails to load, or shows a Cloudflare challenge ("Just a
moment"). Each such case is reported on stderr as one JSON line; the run itself never fails because of one page.
A Cloudflare challenge or an HTTP 403/429 stops all further fetching (reported once); the remaining rows pass
through unchanged.
For a challenged page, run stealth_fetch.py (Scrapling) by hand. Exit 1 only if stdin is not a JSON list.
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (personal hackathon finder; read-only; contact via GitHub RitikBhardwaj-programmer)"
ELIG_CAP = 600
MAX_LIMIT = 20
MIN_DELAY = 2.0
CHALLENGE = re.compile(r"Just a moment", re.I)  # Cloudflare challenge title; normal pages also load challenge-platform JS


class Challenged(Exception):
    pass


def rules_url(url):
    """'https://x.devpost.com/?ref=1' -> 'https://x.devpost.com/rules'; '' if not a Devpost event URL."""
    p = urllib.parse.urlsplit((url or "").strip())
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or not (host == "devpost.com" or host.endswith(".devpost.com")):
        return ""
    path = p.path.rstrip("/")
    if not path.endswith("/rules"):
        path += "/rules"
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, "", ""))


def _text(fragment):
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


def parse_team_max(page):
    m = re.search(r"Team max size:\s*(\d+)", page)
    return int(m.group(1)) if m else None


def parse_eligibility(page, cap=ELIG_CAP):
    """Text of the heading that reads 'N. Eligibility' up to the next heading of the same level; '' if absent."""
    heads = list(re.finditer(r"<(h[1-6])\b[^>]*>(.*?)</\1>", page, re.S | re.I))
    for i, h in enumerate(heads):
        if re.match(r"\d+\.?\s*eligibility\b", _text(h.group(2)), re.I):
            end = len(page)
            for nxt in heads[i + 1:]:
                if nxt.group(1).lower() == h.group(1).lower():
                    end = nxt.start()
                    break
            return _text(page[h.end():end])[:cap].strip()
    return ""


def fetch_rules(url, fetcher=None):
    """Return the page HTML. `fetcher(url)` is injectable for tests."""
    if fetcher:
        return fetcher(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if CHALLENGE.search(body):
            return body  # Cloudflare answers 403 with the challenge page: let the caller detect it
        raise


def enrich_row(row, fetcher=None):
    """Return (new_row, note). note is '' on success, else a short reason the row stayed unchanged."""
    url = rules_url(row.get("url"))
    if not url:
        return row, "not a Devpost event URL"
    page = fetch_rules(url, fetcher)
    if CHALLENGE.search(page) and "Team max size" not in page and not parse_eligibility(page):
        raise Challenged(url)
    new = dict(row)
    tmax, elig = parse_team_max(page), parse_eligibility(page)
    if tmax is not None and not new.get("team_max"):
        new["team_max"] = tmax
    if elig:
        old = (new.get("eligibility_text") or "").strip()
        if elig not in old:
            new["eligibility_text"] = (old + " | " + elig) if old else elig
    if tmax is None and not elig:
        return new, "no team size or eligibility section found"
    return new, ""


def enrich_all(rows, limit=10, delay=MIN_DELAY, fetcher=None, report=None):
    report = report or (lambda d: None)
    delay = max(float(delay), MIN_DELAY)
    limit = max(0, min(int(limit), MAX_LIMIT))
    out, done, stopped = [], 0, False
    for row in rows:
        if stopped or done >= limit or not rules_url(row.get("url")):
            out.append(row)
            continue
        if done:
            time.sleep(delay)
        done += 1
        try:
            new, note = enrich_row(row, fetcher)
        except Challenged as e:
            out.append(row)
            stopped = True
            report({"ok": False, "source": "devpost_rules", "url": str(e),
                    "error": "Cloudflare challenge (Just a moment): stopped, remaining rows left unchanged"})
            continue
        except urllib.error.HTTPError as e:
            out.append(row)
            if e.code in (403, 429):
                stopped = True
                report({"ok": False, "source": "devpost_rules", "url": row.get("url"),
                        "error": "HTTP %d: stopped, remaining rows left unchanged" % e.code})
            else:
                report({"ok": False, "source": "devpost_rules", "url": row.get("url"), "error": "HTTPError: %s" % e})
            continue
        except Exception as e:  # one bad page must not stop the run
            out.append(row)
            report({"ok": False, "source": "devpost_rules", "url": row.get("url"), "error": "%s: %s" % (type(e).__name__, e)})
            continue
        out.append(new)
        if note:
            report({"ok": False, "source": "devpost_rules", "url": row.get("url"), "error": note})
    return out


def main(argv=None, stdin=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=10, help="max events to fetch (default 10, maximum 20)")
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between events (minimum 2)")
    a = ap.parse_args(argv)
    try:
        rows = json.loads((stdin or sys.stdin).read())
        if not isinstance(rows, list):
            raise ValueError("stdin must be a JSON list of hackathon dicts")
    except ValueError as e:
        print(json.dumps({"ok": False, "source": "devpost_rules", "error": "bad stdin: %s" % e}), file=sys.stderr)
        return 1
    out = enrich_all(rows, a.limit, a.delay, report=lambda d: print(json.dumps(d), file=sys.stderr))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
