"""Command line: python get_transcript.py <url> [--lang en,hi] [--out PATH]. Prints one JSON object."""
import argparse
import json
import sys

from .core import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch a YouTube transcript.")
    ap.add_argument("url", help="YouTube link or 11-character video ID")
    ap.add_argument("--lang", default="en", help="comma-separated language codes in priority order (default: en)")
    ap.add_argument("--out", help="write the transcript here (default: ~/.claude/ytx-cache/<id>.<lang>.txt)")
    args = ap.parse_args(argv)
    res = run(args.url, [x.strip() for x in args.lang.split(",") if x.strip()], args.out)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
