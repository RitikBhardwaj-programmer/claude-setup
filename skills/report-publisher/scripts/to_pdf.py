"""Print a report folder's index.html to an A4 PDF with headless Chrome, then check every page.

Run with a Python that has pypdfium2 (see SKILL.md: setup.json "python", else python3):
  python3 to_pdf.py DIR [--name Report.pdf]        (set CHROME=/path/to/chrome if Chrome is not found)

Steps: serve DIR on a free localhost port -> write print.html (index.html + assets/print.css)
-> Chrome --headless=new --print-to-pdf with a throwaway profile -> delete print.html
-> print characters per page and warn about near-empty pages (a sign of a bad page break).
Edge headless was seen to exit 0 without writing a PDF, so Chrome is used.
"""
import argparse
import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CHROMES = [os.environ.get("CHROME", ""),
           r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
           "/Applications/Chromium.app/Contents/MacOS/Chromium",
           shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chromium-browser") or ""]
EMPTY_PAGE_CHARS = 400


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--name", default="report.pdf")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = Path(a.dir).resolve()
    page = (d / "index.html").read_text(encoding="utf-8")
    print_css = (SKILL / "assets" / "print.css").read_text(encoding="utf-8")
    if "</style>" not in page:
        sys.exit("index.html has no </style>; build it with build.py first")
    (d / "print.html").write_text(page.replace("</style>", print_css + "</style>", 1), encoding="utf-8")

    chrome = next((c for c in CHROMES if c and Path(c).is_file()), None)
    if not chrome:
        sys.exit("Chrome not found: install Google Chrome or set CHROME=/path/to/chrome")
    port = free_port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(QuietHandler, directory=str(d)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    profile = tempfile.mkdtemp(prefix="chrome-pdf-")
    pdf = d / a.name
    try:
        r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={profile}", "--virtual-time-budget=15000",
                            f"--print-to-pdf={pdf}", f"http://127.0.0.1:{port}/print.html"],
                           capture_output=True, text=True, timeout=180)
    finally:
        srv.shutdown()
        (d / "print.html").unlink(missing_ok=True)
        shutil.rmtree(profile, ignore_errors=True)
    if not pdf.is_file():
        print(r.stdout[-500:], r.stderr[-800:])
        sys.exit("PDF was not written")

    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    n, warn = len(doc), []
    for i in range(n):
        tp = doc[i].get_textpage()
        chars = len(tp.get_text_range().strip())
        tp.close()
        flag = ""
        if chars < EMPTY_PAGE_CHARS and i < n - 1:
            flag = "  <-- nearly empty: check page breaks"
            warn.append(i + 1)
        print(f"page {i + 1:2d}: {chars:5d} chars{flag}")
    doc.close()
    print(f"wrote {pdf} ({pdf.stat().st_size // 1024} KB, {n} pages)")
    if warn:
        print("WARNING nearly empty pages:", warn, "- a large block marked break-inside: avoid is the usual cause")
    return 0


if __name__ == "__main__":
    sys.exit(main())
