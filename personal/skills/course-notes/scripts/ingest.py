"""Turn study sources into plain text inside a course folder.

Usage (run with: py -3 -I ingest.py ...):
  ingest.py playlist <playlist-url> <course-dir>   write <course-dir>/sources.tsv (L<nn>, id, minutes, title)
  ingest.py youtube <course-dir> [--only L05,L06]  fetch missing transcripts -> transcripts/L<nn> <id>.<lang>.txt
  ingest.py pdf <file.pdf> <course-dir>            text layer (or Marker OCR) -> transcripts/<stem>.md
  ingest.py pptx <file.pptx> <course-dir>          slide text -> transcripts/<stem>.md, one "## Slide n" per slide

Notes:
- YouTube fetching uses the youtube-transcript skill (ytx venv) with --lang en,hi and a 20 s pause
  between videos. Run it in the background for many videos (about 20-25 s per video).
- `hi` tracks are often English speech written in Devanagari: topics survive, exact numbers do not.
- The script changes to the home folder before calling Windows programs, because a very long
  working directory makes them fail ("path longer than allowed for a Win32 working directory").
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path.home()
YTX_PY = HOME / ".claude/tools/ytx-venv/Scripts/python.exe"
YTDLP = HOME / ".claude/tools/ytx-venv/Scripts/yt-dlp.exe"
YTX_SCRIPT = HOME / ".claude/skills/youtube-transcript/scripts/get_transcript.py"
PDF_ROUTER = HOME / ".claude/hooks/pdf_router.py"
MARKER_PY = HOME / ".claude/tools/marker-venv/Scripts/python.exe"


def run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          encoding="utf-8", cwd=str(HOME))


def read_sources(course):
    rows = []
    for line in (course / "sources.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        lec, vid, minutes, title = line.split("\t", 3)
        rows.append((lec, vid, minutes, title))
    return rows


def cmd_playlist(url, course):
    r = run([YTDLP, "--flat-playlist", "--print",
             "%(playlist_index)s\t%(id)s\t%(duration)s\t%(title)s", url])
    if r.returncode:
        sys.exit(r.stderr[-800:])
    lines = ["lecture\tid\tminutes\ttitle"]
    for row in r.stdout.splitlines():
        idx, vid, dur, title = row.split("\t", 3)
        minutes = str(round(float(dur) / 60)) if dur not in ("NA", "") else "?"
        lines.append(f"L{int(idx):02d}\t{vid}\t{minutes}\t{title}")
    course.mkdir(parents=True, exist_ok=True)
    (course / "sources.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines) - 1} videos -> {course / 'sources.tsv'}")


def cmd_youtube(course, only):
    out = course / "transcripts"
    out.mkdir(parents=True, exist_ok=True)
    todo = [r for r in read_sources(course) if not only or r[0] in only]
    first = True
    for lec, vid, _, _ in todo:
        if list(out.glob(f"{lec} {vid}.*.txt")):
            print(lec, vid, "cached")
            continue
        if not first:
            time.sleep(20)
        first = False
        r = run([YTX_PY, YTX_SCRIPT, f"https://www.youtube.com/watch?v={vid}", "--lang", "en,hi"])
        try:
            d = json.loads(r.stdout)
        except ValueError:
            print(lec, vid, "FAILED", (r.stderr or r.stdout)[-300:].replace("\n", " "))
            continue
        if not d.get("ok"):
            print(lec, vid, "FAILED", d.get("error", "")[:300])
            continue
        lang = d.get("language", "xx")
        dest = out / f"{lec} {vid}.{lang}.txt"
        if d.get("path") and Path(d["path"]).exists():
            shutil.copyfile(d["path"], dest)
        else:
            dest.write_text(d.get("text", ""), encoding="utf-8")
        flag = "  <- garbled-risk (hi track)" if lang == "hi" else ""
        print(lec, vid, lang, d.get("source"), f"{d.get('word_count')} words{flag}")


def cmd_pdf(pdf, course):
    out = course / "transcripts"
    out.mkdir(parents=True, exist_ok=True)
    r = run([MARKER_PY, PDF_ROUTER, "text", pdf])
    path = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if r.returncode or not path or Path(path).stat().st_size < 200:
        print("no usable text layer; converting with Marker (OCR), this can take minutes")
        r = run([MARKER_PY, PDF_ROUTER, "convert", pdf])
        path = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if not path or not Path(path).exists():
        sys.exit(f"PDF extraction failed: {(r.stderr or r.stdout)[-500:]}")
    dest = out / f"{Path(pdf).stem}.md"
    dest.write_text(Path(path).read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    print(f"{dest} ({dest.stat().st_size // 1024} KB)")


def cmd_pptx(pptx, course):
    out = course / "transcripts"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pptx) as z:
        slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                        key=lambda n: int(re.search(r"\d+", n.split("/")[-1]).group()))
        parts = [f"# {Path(pptx).stem}\n"]
        for i, name in enumerate(slides, 1):
            xml = z.read(name).decode("utf-8", errors="replace")
            paras = []
            for p in re.findall(r"<a:p>(.*?)</a:p>", xml, re.S):
                text = "".join(re.findall(r"<a:t>(.*?)</a:t>", p, re.S))
                if text.strip():
                    paras.append(text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
            notes = f"ppt/notesSlides/notesSlide{i}.xml"
            if notes in z.namelist():
                nt = " ".join(re.findall(r"<a:t>(.*?)</a:t>", z.read(notes).decode("utf-8", "replace")))
                if nt.strip() and not nt.strip().isdigit():  # a bare number is the slide-number field
                    paras.append(f"*Speaker notes:* {nt.strip()}")
            parts.append(f"## Slide {i}\n" + "\n".join(f"- {p}" for p in paras) + "\n")
    dest = out / f"{Path(pptx).stem}.md"
    dest.write_text("\n".join(parts), encoding="utf-8")
    print(f"{len(slides)} slides -> {dest}")


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    mode = argv[1]
    if mode == "playlist":
        cmd_playlist(argv[2], Path(argv[3]))
    elif mode == "youtube":
        only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else set()
        cmd_youtube(Path(argv[2]), only)
    elif mode == "pdf":
        cmd_pdf(Path(argv[2]).resolve(), Path(argv[3]))
    elif mode == "pptx":
        cmd_pptx(Path(argv[2]).resolve(), Path(argv[3]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
