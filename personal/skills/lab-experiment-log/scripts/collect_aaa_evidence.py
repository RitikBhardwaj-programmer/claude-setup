"""Collect read-only evidence from the AAA Docker lab for one time window, as Markdown.

Usage (stdlib only, Docker Desktop must be running):
  py -3 collect_aaa_evidence.py --lab "C:/Users/DELL/Networking Project/aaa-server" \
      --since "2026-10-05 20:30" --until "2026-10-05 23:45" [--date 2026-10-05] > evidence.md

All times are SERVER times (container TZ, Asia/Kolkata). AP timestamps are not used because the
lab AP's clock is wrong. Sources:
  1. radpostauth (SQLite, opened immutable=1): every Access-Accept / Access-Reject with the inner user.
  2. detail files radacct/<nas>/detail-YYYYMMDD: every accounting packet with the server receive time.
  3. radius container log (docker compose logs): Login OK / Login incorrect lines. Only covers the
     current container's lifetime; recreated containers lose older lines (say so in the note).
Rows from NAS 10.89.0.50 are the automated test suite, not real devices; they are marked.
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime

TEST_NAS = "10.89.0.50"


def run(lab, args):
    r = subprocess.run(["docker", "compose", *args], cwd=lab, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 and not r.stdout:
        raise RuntimeError(r.stderr.strip()[-400:])
    return r.stdout


def sqlite(lab, query):
    return run(lab, ["--profile", "test", "run", "--rm", "--no-deps", "--entrypoint", "sqlite3", "tests",
                     "-header", "-separator", " | ", "file:/radius-acct/sqlite/radius.db?immutable=1", query])


def parse_detail(text):
    """Yield dicts per accounting packet; key '_ts' is the server receive time."""
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if not lines:
            continue
        try:
            ts = datetime.strptime(" ".join(lines[0].split()), "%a %b %d %H:%M:%S %Y")
        except ValueError:
            continue
        rec = {"_ts": ts}
        for ln in lines[1:]:
            m = re.match(r"\s*([A-Za-z0-9-]+) = (.*)", ln)
            if m:
                rec[m.group(1)] = m.group(2).strip().strip('"')
        yield rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD HH:MM (server time)")
    ap.add_argument("--until", required=True)
    ap.add_argument("--date", help="detail-file date YYYY-MM-DD (default: date of --since)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    since = datetime.strptime(a.since, "%Y-%m-%d %H:%M")
    until = datetime.strptime(a.until, "%Y-%m-%d %H:%M")
    day = (a.date or a.since[:10]).replace("-", "")

    print(f"## Evidence (server time, {a.since} to {a.until})\n")
    print(f"_Collected {datetime.now():%Y-%m-%d %H:%M} with collect_aaa_evidence.py (read-only)._\n")

    print("### Login results (radpostauth)\n")
    q = ("SELECT authdate, username, reply, IFNULL(class,'') AS class FROM radpostauth "
         f"WHERE authdate >= '{since:%Y-%m-%d %H:%M}' AND authdate <= '{until:%Y-%m-%d %H:%M}:59.999' ORDER BY id")
    try:
        rows = [r for r in sqlite(a.lab, q).splitlines() if r.strip()]
        print("```\n" + ("\n".join(rows) if len(rows) > 1 else "(no rows)") + "\n```\n")
    except RuntimeError as e:
        print(f"_Could not read radpostauth: {e}_\n")

    print("### Accounting packets (detail files, server receive time)\n")
    try:
        files = run(a.lab, ["--profile", "test", "run", "--rm", "--no-deps", "--entrypoint", "sh", "tests", "-c",
                            f"ls /radius-acct/radacct/*/detail-{day} 2>/dev/null"]).split()
    except RuntimeError as e:
        files = []
        print(f"_Could not list detail files: {e}_\n")
    print("| Received | NAS | Type | Session | User | Device | IP | Time (s) | In (B) | Out (B) | Cause |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    n = 0
    for f in files:
        nas = f.split("/")[-2]
        text = run(a.lab, ["--profile", "test", "run", "--rm", "--no-deps", "--entrypoint", "cat", "tests", f])
        for r in parse_detail(text):
            if not since <= r["_ts"] <= until:
                continue
            n += 1
            tag = " (test suite)" if nas == TEST_NAS else ""
            print(f"| {r['_ts']:%H:%M:%S} | {nas}{tag} | {r.get('Acct-Status-Type', '')} | {r.get('Acct-Session-Id', '')} | "
                  f"{r.get('User-Name', '')} | {r.get('Calling-Station-Id', '')} | {r.get('Framed-IP-Address', '')} | "
                  f"{r.get('Acct-Session-Time', '')} | {r.get('Acct-Input-Octets', '')} | {r.get('Acct-Output-Octets', '')} | "
                  f"{r.get('Acct-Terminate-Cause', '')} |")
    if not n:
        print("| (no packets in window) |||||||||||")
    print()

    print("### RADIUS log lines (current container only)\n")
    try:
        log = run(a.lab, ["logs", "--no-color", "radius"])
        keep = [ln.split("|", 1)[-1].strip() for ln in log.splitlines()
                if re.search(r"Login OK|Login incorrect|Ignoring request|Error", ln)]
        inwin = []
        for ln in keep:
            m = re.match(r"(\w{3} \w{3}\s+\d+ \d\d:\d\d:\d\d \d{4})", ln)
            if m and since <= datetime.strptime(" ".join(m.group(1).split()), "%a %b %d %H:%M:%S %Y") <= until:
                inwin.append(ln)
        print("```\n" + ("\n".join(inwin) if inwin else "(none: container may have been recreated since)") + "\n```")
    except RuntimeError as e:
        print(f"_Could not read container log: {e}_")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError:
        sys.exit("docker not found: start Docker Desktop first")
