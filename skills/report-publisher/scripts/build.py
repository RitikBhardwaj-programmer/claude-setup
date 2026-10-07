"""Build a themed report page (index.html) from Markdown.

Run with a Python that has markdown-it-py (see SKILL.md: setup.json "python", else python3):
  python3 build.py REPORT.md --out DIR
      [--title "Tab title"] [--eyebrow "Project · type"] [--meta "Label=Value" ...] [--intro N]

Markdown conventions:
  - First line "# Heading" becomes the page H1; the next N paragraphs (--intro, default 1) become the intro.
  - Each "## " heading becomes a <section>.
  - Table cells that are exactly Pass/Partial/Gap or MUST/SHOULD/INFO become coloured pills.
  - A line "[[figure: path/to/diagram.svg | Caption text]]" inlines that SVG (path relative to the .md).
  - A line "[[score: pass=4, partial=4, gap=8]]" draws a stacked score bar.
  - External links open in a new tab. Local image paths are listed so they can go in Artifact `files`.
"""
import argparse
import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt

SKILL = Path(__file__).resolve().parent.parent
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;'
         '8..60,600;8..60,700&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600'
         '&display=swap">')
PILLS = {"Pass": ("ok", "pass"), "Partial": ("near", "partial"), "Gap": ("off", "gap"),
         "MUST": ("must", "MUST"), "SHOULD": ("should", "SHOULD"), "INFO": ("info", "INFO")}


def figure_block(md_dir, path, caption, n):
    svg = (md_dir / path.strip()).read_text(encoding="utf-8")
    cap = f"<figcaption><b>Figure {n}.</b> {html.escape(caption.strip())}</figcaption>" if caption.strip() else ""
    return f'<figure class="flow" role="img" aria-label="{html.escape(caption.strip() or path)}">{svg}{cap}</figure>'


def score_block(spec):
    vals = dict(kv.split("=") for kv in re.split(r"\s*,\s*", spec.strip()))
    segs = [("ok", "pass", int(vals.get("pass", 0))), ("near", "partial", int(vals.get("partial", 0))),
            ("off", "gap", int(vals.get("gap", 0)))]
    inner = "".join(f'<div class="seg {c}" style="flex:{v}">{v} {w}</div>' for c, w, v in segs if v)
    total = sum(v for *_, v in segs)
    return f'<div class="score" role="img" aria-label="Score: {", ".join(f"{v} {w}" for _, w, v in segs)} of {total}">{inner}</div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--eyebrow", default="")
    ap.add_argument("--meta", action="append", default=[])
    ap.add_argument("--intro", type=int, default=1)
    a = ap.parse_args()

    md_path = Path(a.md).resolve()
    src = md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = src.split("\n")
    if not lines[0].startswith("# "):
        sys.exit("First line must be '# Heading'")
    h1 = lines[0][2:].strip()
    body_md = "\n".join(lines[1:]).strip()

    # placeholders -> raw HTML tokens kept out of markdown rendering
    raw, fig_n = {}, 0

    def keep(block):
        key = f"RAWBLOCK{len(raw)}X"
        raw[key] = block
        return key

    def sub_fig(m):
        nonlocal fig_n
        fig_n += 1
        return keep(figure_block(md_path.parent, m.group(1), m.group(2) or "", fig_n))

    body_md = re.sub(r"^\[\[figure:\s*([^|\]]+?)\s*(?:\|\s*([^\]]*))?\]\]\s*$", sub_fig, body_md, flags=re.M)
    body_md = re.sub(r"^\[\[score:\s*([^\]]+)\]\]\s*$", lambda m: keep(score_block(m.group(1))), body_md, flags=re.M)

    # intro = up to N leading paragraphs that are not headings, tables or placeholders
    parts = re.split(r"\n\s*\n", body_md)
    k = 0
    while k < min(a.intro, len(parts)) and not re.match(r"(#|\||RAWBLOCK)", parts[k].lstrip()):
        k += 1
    intro_md = "\n\n".join(parts[:k])
    rest_md = "\n\n".join(parts[k:])

    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    body = md.render(rest_md)
    intro = md.render(intro_md) if intro_md else ""

    for k, (cls, label) in PILLS.items():
        body = body.replace(f"<td>{k}</td>", f'<td><span class="pill {cls}">{label}</span></td>')
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    body = re.sub(r'<pre><code(?: class="[^"]*")?>', '<pre class="code"><code>', body)
    for key, block in raw.items():
        body = body.replace(f"<p>{key}</p>", block).replace(key, block)

    out_parts, sid = [], 0
    for p in re.split(r"(?=<h2>)", body):
        if not p.strip():
            continue
        m = re.match(r"<h2>(.*?)</h2>", p)
        if m:
            sid += 1
            p = p.replace(m.group(0), f'<header><h2 id="s{sid}">{m.group(1)}</h2></header>', 1)
            out_parts.append(f'<section aria-labelledby="s{sid}">{p}</section>')
        else:
            out_parts.append(p)
    body = "\n".join(out_parts)

    def ext_links(s):
        return re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', s)
    body, intro = ext_links(body), ext_links(intro)

    meta = "".join(f"<span><b>{html.escape(k)}</b> {html.escape(v)}</span>"
                   for k, v in (m.split("=", 1) for m in a.meta))
    hero = ('<header class="hero">'
            + (f'<div class="eyebrow">{html.escape(a.eyebrow)}</div>' if a.eyebrow else "")
            + f"<h1>{html.escape(h1)}</h1>"
            + (f'<div class="intro">{intro}</div>' if intro else "")
            + (f'<div class="meta">{meta}</div>' if meta else "") + "</header>")

    css = (SKILL / "assets" / "theme.css").read_text(encoding="utf-8") + "\n" + \
          (SKILL / "assets" / "components.css").read_text(encoding="utf-8") + \
          "\n.doc img { max-width: 100%; height: auto; border: 1px solid var(--rule); border-radius: 4px; }\n"
    title = a.title or h1
    page = (f'<meta charset="utf-8">\n<title>{html.escape(title)}</title>\n{FONTS}\n<style>\n{css}</style>\n'
            f'<div class="wrap doc">{hero}\n{body}\n</div>\n')
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")

    imgs = sorted(set(re.findall(r'<img src="([^"]+)"', page)) - {s for s in re.findall(r'<img src="(https?://[^"]+)"', page)})
    missing = [i for i in imgs if not (out / i).is_file()]
    sys.stdout.reconfigure(encoding="utf-8")
    n_tables = body.count('class="tbl"')
    print(f"wrote {out / 'index.html'}  sections={sid} tables={n_tables} figures={fig_n}")
    if imgs:
        print("local images (add to Artifact files):", ", ".join(imgs))
    if missing:
        print("MISSING images (copy them into --out):", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
