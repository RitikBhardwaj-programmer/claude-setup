"""Structural checks on a course's unit notes, plus a timestamp spot-check.

Usage: py -3 -I check_units.py <course-dir> [--units U02,U03] [--sample 3]

Reads:
- <course-dir>/Overview.md units table: rows like "| U02 Data representation | L5–L7 | ...".
- <course-dir>/sources.tsv (optional): lecture -> video id, for timestamp checks.
- <course-dir>/transcripts/L<nn> <id>.<lang>.txt (optional): for --sample.
Checks per note: frontmatter fields, author: ai, every [[link]] resolves to a note in the folder
(or a vault path ending in /Overview), balanced <details>, required sections, self-test count
10-15 (Revision), mm:ss == ?t= seconds, video ids belong to the unit's lectures (cross-unit links
are listed, not failed), timestamps inside the video length.
--sample N prints N random timestamps per Intuition note next to the transcript text, so a
human or model can confirm the claim matches what the lecturer says.
"""
import random
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
FM = ["title", "type", "author", "course", "unit", "lectures", "style", "source", "created", "tags"]
REV_SECTIONS = ["## 1.", "## 2.", "## 3.", "## 4.", "## 5."]
INT_PARTS = ["Mini-glossary", "Closing the loop", "Accuracy notes", "Pause"]
STAMP = re.compile(r"\[([\d:]+)\]\(https://youtu\.be/([\w-]+)\?t=(\d+)\)")


def secs(mmss):
    return sum(int(p) * 60 ** i for i, p in enumerate(reversed(mmss.split(":"))))


def unit_map(course):
    units = {}
    for line in (course / "Overview.md").read_text(encoding="utf-8").splitlines():
        # lecture cell: "L5–L7", "L15", or a list with part suffixes such as "L14, L15a, L15b"
        m = re.match(r"\|\s*(U\d{2})\b[^|]*\|([^|]*)\|", line)
        nums = [int(n) for n in re.findall(r"L(\d+)[a-z]?", m.group(2))] if m else []
        if nums:
            units[m.group(1)] = (min(nums), max(nums))
    return units


def lec_num(lec):
    """'L07' -> 7, 'L15a' -> 15 (parts of one lecture share its number)."""
    return int(re.match(r"L(\d+)", lec).group(1))


def load_sources(course):
    ids, trans = {}, {}  # ids: lecture number -> set of video ids (a split lecture has several)
    tsv = course / "sources.tsv"
    if tsv.exists():
        for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
            lec, vid = line.split("\t")[:2]
            ids.setdefault(lec_num(lec), set()).add(vid)
    for t in (course / "transcripts").glob("L* *.txt") if (course / "transcripts").exists() else []:
        lec, rest = t.stem.split(" ", 1)
        ids.setdefault(lec_num(lec), set()).add(rest.split(".")[0])
        lines = [(secs(m.group(1)), m.group(2)) for m in
                 re.finditer(r"^\[([\d:]+)\] (.*)$", t.read_text(encoding="utf-8"), re.M)]
        trans[rest.split(".")[0]] = lines
    return ids, trans


def check(f, names, allowed, trans):
    txt = f.read_text(encoding="utf-8")
    probs, notes = [], []
    parts = txt.split("---")
    fm = parts[1] if len(parts) > 2 else ""
    probs += [f"frontmatter missing {k}" for k in FM if not re.search(rf"^{k}:", fm, re.M)]
    if "author: ai" not in fm:
        probs.append("author not ai")
    for link in re.findall(r"\[\[([^\]]+)\]\]", txt):
        target = link.split("|")[0]
        if target not in names and not target.endswith("/Overview"):
            probs.append(f"dangling [[{target}]]")
    if txt.count("<details>") != txt.count("</details>"):
        probs.append("unbalanced <details>")
    if "style: revision" in fm:
        probs += [f"missing section {s}" for s in REV_SECTIONS if s not in txt]
        n = txt.split("## 5.")[-1].count("<summary>Q")
        if not 10 <= n <= 15:
            probs.append(f"self-test count {n}")
    else:
        probs += [f"missing '{p}'" for p in INT_PARTS if p not in txt]
        if "Still open" not in txt and "Back to the course map" not in txt:
            notes.append("no 'Still open' pointer (fine only for the last unit)")
    for mm, vid, t in STAMP.findall(txt):
        if abs(secs(mm) - int(t)) > 1:
            probs.append(f"stamp {mm} != t={t}")
        if allowed and vid not in allowed:
            notes.append(f"cross-unit link to {vid} at {mm}")
        if vid in trans and trans[vid] and int(t) > trans[vid][-1][0] + 30:
            probs.append(f"stamp {mm} past end of {vid}")
    words = len(re.findall(r"\w+", txt))
    return words, sorted(set(probs)), sorted(set(notes)), txt


def main(argv):
    course = Path(argv[1])
    only = set(argv[argv.index("--units") + 1].split(",")) if "--units" in argv else set()
    sample = int(argv[argv.index("--sample") + 1]) if "--sample" in argv else 0
    units, (ids, trans) = unit_map(course), load_sources(course)
    names = {p.stem for p in course.glob("*.md")}
    bad = 0
    for f in sorted(course.glob("U[0-9][0-9] * - *.md")):
        u = f.name[:3]
        if only and u not in only:
            continue
        lo, hi = units.get(u, (0, -1))
        allowed = {v for n in range(lo, hi + 1) for v in ids.get(n, ())}
        words, probs, notes, txt = check(f, names, allowed, trans)
        bad += bool(probs)
        print(f"{f.name}: {words} words; {'OK' if not probs else 'PROBLEMS: ' + '; '.join(probs)}")
        for n in notes:
            print(f"    note: {n}")
        if sample and "style: intuition" in txt:
            hits = [(m.start(), m.group(2), int(m.group(3))) for m in STAMP.finditer(txt)]
            for pos, vid, s in random.Random(7).sample(hits, min(sample, len(hits))):
                ctx = txt[max(0, pos - 220):pos].replace("\n", " ")
                near = " ".join(x for t, x in trans.get(vid, []) if s - 10 <= t <= s + 25)
                print(f"    -- NOTE: ...{ctx}\n       TRANSCRIPT @{s}s: {near[:260]}")
    print(f"\n{bad} file(s) with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
