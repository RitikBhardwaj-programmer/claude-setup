"""PDF router for Claude Code.

Picks the best way for Claude to read a PDF:
  - small PDF (<= PDF_ROUTER_MAX_NATIVE_PAGES pages) -> native Read (page images + text)
  - large PDF with a text layer -> extract the text with pypdfium2 (seconds), then Grep/Read it
  - large scanned PDF -> convert once with Marker (OCR) to Markdown, then Grep/Read the .md
  - small details (handwriting, drawings, tiny labels) -> render a zoomed PNG and Read the image

Subcommands:
  pretool          PreToolUse hook for Read (JSON on stdin)
  prompt           UserPromptSubmit hook (JSON on stdin)
  info <pdf>       print the routing decision for a PDF
  text <pdf>       extract the text layer into the cache, print the .txt path
  convert <pdf>    convert a PDF with Marker into the cache, print the .md path
                   (falls back to `text` if Marker fails and the PDF has a text layer)
  render <pdf> <page> [zoom] [x0,y0,x1,y1]
                   render one page (1-based) to PNG at `zoom` (default 2.0), optionally
                   cropped to a box given as fractions of the page (0..1), print the .png path.
                   Needs no Poppler.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Read needs pdftoppm (Poppler) for its pages: parameter, which is required above 10 pages.
# Without Poppler, native reading only works up to 10 pages.
MAX_NATIVE_PAGES = int(os.environ.get("PDF_ROUTER_MAX_NATIVE_PAGES", "10"))
CACHE_ROOT = Path.home() / ".claude" / "cache" / "pdf-md"
VENV_SCRIPTS = Path.home() / ".claude" / "tools" / "marker-venv" / "Scripts"
PYTHON = VENV_SCRIPTS / "python.exe"
SCRIPT = Path(__file__).resolve()
MIN_CHARS_PER_PAGE = 50  # below this on average, treat the PDF as scanned


def inspect(pdf):
    """Return (page_count, has_text_layer) or (None, None) if unreadable."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf))
    except Exception:
        return None, None
    try:
        n = len(doc)
        sample = sorted({int(i * (n - 1) / 4) for i in range(5)}) if n > 1 else [0]
        chars = 0
        for i in sample:
            page = doc[i]
            textpage = page.get_textpage()
            chars += len(textpage.get_text_range().strip())
            textpage.close()
            page.close()
        return n, (chars / len(sample)) >= MIN_CHARS_PER_PAGE
    finally:
        doc.close()


def cache_dir(pdf):
    st = pdf.stat()
    key = f"{str(pdf).lower()}|{st.st_size}|{st.st_mtime_ns}"
    return CACHE_ROOT / f"{pdf.stem[:40]}-{hashlib.sha1(key.encode()).hexdigest()[:10]}"


def cached_md(pdf):
    d = cache_dir(pdf)
    if not d.is_dir():
        return None
    mds = sorted(d.rglob("*.md"))
    return mds[0] if mds else None


def cached_txt(pdf):
    p = cache_dir(pdf) / f"{pdf.stem[:40]}.txt"
    return p if p.is_file() else None


def sub_cmd(name, pdf, *extra):
    args = " ".join(extra)
    return f'"{PYTHON.as_posix()}" "{SCRIPT.as_posix()}" {name} "{pdf}"' + (f" {args}" if args else "")


def render_hint(pdf):
    return (f"For handwriting, drawings or tiny labels, render a zoomed PNG and Read it: "
            f"{sub_cmd('render', pdf, '<page>', '3', '[x0,y0,x1,y1]')} (crop box = fractions 0..1 of the page).")


def decide(pdf):
    """Return (allow: bool, message: str)."""
    pages, has_text = inspect(pdf)
    if pages is None:
        return True, f"[pdf-router] Could not inspect {pdf.name} (encrypted or damaged). Try native Read."
    kind = "text PDF" if has_text else "scanned/image PDF (no text layer)"
    if pages <= MAX_NATIVE_PAGES:
        return True, (f"[pdf-router] {pdf.name}: {pages} pages, {kind}. Method: native Read "
                      f"(page images + text), without a pages: parameter. {render_hint(pdf)}")
    md, txt = cached_md(pdf), cached_txt(pdf)
    if md or txt:
        done = md or txt
        return False, (f"[pdf-router] {pdf.name} has {pages} pages ({kind}); it is already extracted. "
                       f"Do not read the PDF natively. Grep and Read this file instead: {done} . "
                       f"{render_hint(pdf)}")
    if has_text:
        return False, (f"[pdf-router] {pdf.name} has {pages} pages ({kind}), more than {MAX_NATIVE_PAGES}. "
                       f"Method: fast text extraction (seconds, no OCR). Run with the Bash tool: "
                       f"{sub_cmd('text', pdf)} . It prints the .txt path (pages marked '===== PAGE n ====='). "
                       f"Then Grep and Read the .txt. For tables or layout, use {sub_cmd('convert', pdf)} "
                       f"in the background instead (Marker, minutes). {render_hint(pdf)}")
    return False, (f"[pdf-router] {pdf.name} has {pages} pages ({kind}), more than {MAX_NATIVE_PAGES}. "
                   f"Method: Marker -> Markdown with OCR (slow). Run this with the Bash tool in the background "
                   f"(it can take minutes on CPU): {sub_cmd('convert', pdf)} . It prints the .md path when done. "
                   f"Then Grep and Read the .md. If Marker fails, render pages with "
                   f"{sub_cmd('render', pdf, '<page>', '2')} and Read the PNGs. Tell the user you are converting it.")


def emit(obj):
    sys.stdout.write(json.dumps(obj))


def hook_pretool():
    data = json.load(sys.stdin)
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path.lower().endswith(".pdf") or not os.path.isfile(path):
        return
    allow, msg = decide(Path(path).resolve())
    out = {"hookEventName": "PreToolUse"}
    if allow:
        out["additionalContext"] = msg
    else:
        out["permissionDecision"] = "deny"
        out["permissionDecisionReason"] = msg
    emit({"hookSpecificOutput": out})


PDF_PATH_RE = re.compile(r'"([^"]+?\.pdf)"|\'([^\']+?\.pdf)\'|([A-Za-z]:[\\/][^\r\n"<>|]*?\.pdf)|(\S+?\.pdf)\b',
                         re.IGNORECASE)


def hook_prompt():
    data = json.load(sys.stdin)
    prompt = data.get("prompt") or ""
    if ".pdf" not in prompt.lower():
        return
    cwd = data.get("cwd") or os.getcwd()
    notes, seen = [], set()
    for m in PDF_PATH_RE.finditer(prompt):
        # @"C:\...pdf" matches the last pattern from the @, so strip quotes as well as @.
        raw = next(g for g in m.groups() if g).lstrip("@").strip("\"'")
        p = Path(raw) if os.path.isabs(raw) else Path(cwd) / raw
        if not p.is_file():
            continue
        p = p.resolve()
        if p in seen:
            continue
        seen.add(p)
        notes.append(decide(p)[1])
    if notes:
        emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                     "additionalContext": "\n".join(notes)}})


def cmd_convert(pdf):
    out = cache_dir(pdf)
    md = cached_md(pdf)
    if md:
        print(md)
        return 0
    out.mkdir(parents=True, exist_ok=True)
    marker = VENV_SCRIPTS / "marker_single.exe"
    env = dict(os.environ)
    llama = find_llama_server()
    if llama and not env.get("LLAMA_CPP_BINARY"):
        env["LLAMA_CPP_BINARY"] = llama  # Marker's OCR (surya) spawns llama-server
    r = subprocess.run([str(marker), str(pdf), "--output_dir", str(out)], env=env)
    md = cached_md(pdf)
    if r.returncode != 0 or not md:
        print(f"Marker failed (exit {r.returncode}). Output dir: {out}", file=sys.stderr)
        if inspect(pdf)[1]:
            print("Falling back to text-layer extraction (no OCR, no layout).", file=sys.stderr)
            return cmd_text(pdf)
        print("No text layer: render pages with the `render` subcommand and Read the PNGs.", file=sys.stderr)
        return 1
    (out / "source.txt").write_text(str(pdf), encoding="utf-8")
    print(md)
    return 0


def find_llama_server():
    """llama-server from PATH, else from the winget package folder (PATH changes need a restart)."""
    import shutil
    found = shutil.which("llama-server")
    if found:
        return found
    pkgs = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Microsoft" / "WinGet" / "Packages"
    hits = sorted(pkgs.glob("ggml.llamacpp*/llama-server.exe")) if pkgs.is_dir() else []
    return str(hits[-1]) if hits else None


def cmd_text(pdf):
    """Extract the text layer of every page with pypdfium2; cache it as a .txt with page markers."""
    import pypdfium2 as pdfium
    target = cache_dir(pdf) / f"{pdf.stem[:40]}.txt"
    if target.is_file():
        print(target)
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    try:
        parts = [f"Source: {pdf}\n"]
        for i in range(len(doc)):
            page = doc[i]
            tp = page.get_textpage()
            parts.append(f"\n===== PAGE {i + 1} =====\n{tp.get_text_range()}")
            tp.close()
            page.close()
    finally:
        doc.close()
    target.write_text("".join(parts), encoding="utf-8")
    print(target)
    return 0


def cmd_render(pdf, page_no, zoom=2.0, box=None):
    """Render page `page_no` (1-based) at `zoom`, optionally cropped to fractional box; print the .png path."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        if not 1 <= page_no <= len(doc):
            print(f"Page {page_no} out of range (1..{len(doc)})", file=sys.stderr)
            return 2
        page = doc[page_no - 1]
        img = page.render(scale=zoom, may_draw_forms=True).to_pil()
        page.close()
    finally:
        doc.close()
    tag = f"p{page_no:03d}-z{zoom:g}"
    if box:
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            print("Crop box must be fractions 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1", file=sys.stderr)
            return 2
        w, h = img.size
        img = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
        tag += "-crop" + "_".join(f"{v:g}" for v in box)
    # Keep images readable but not huge: the Read tool downsizes very large images anyway.
    if max(img.size) > 2400:
        img.thumbnail((2400, 2400))
    out = cache_dir(pdf) / "render" / f"{tag}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    try:
        if cmd == "pretool":
            hook_pretool()
        elif cmd == "prompt":
            hook_prompt()
        elif cmd == "info":
            print(decide(Path(sys.argv[2]).resolve())[1])
        elif cmd == "convert":
            return cmd_convert(Path(sys.argv[2]).resolve())
        elif cmd == "text":
            return cmd_text(Path(sys.argv[2]).resolve())
        elif cmd == "render":
            zoom = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
            box = tuple(float(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else None
            if box is not None and len(box) != 4:
                print("Crop box needs 4 values: x0,y0,x1,y1", file=sys.stderr)
                return 2
            return cmd_render(Path(sys.argv[2]).resolve(), int(sys.argv[3]), zoom, box)
        else:
            print(__doc__)
            return 2
    except Exception as e:
        # Never break Claude's Read or prompt because of the router.
        if cmd in ("pretool", "prompt"):
            print(f"pdf-router error: {e}", file=sys.stderr)
            return 0
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
