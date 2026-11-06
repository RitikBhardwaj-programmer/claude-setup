"""Convert a vault course note (Obsidian markdown) to Notion-flavored markdown, ready to send as is.

Usage: py -3 -I to_notion.py <in.md> <out.md> [--max-chars 30000]

Does every conversion the COA mirror needed (so no model has to rewrite content by hand):
- drops YAML frontmatter and the H1 title (Notion sets the title)
- <details><summary>Q</summary>A</details> -> <toggle>; a title starting "1." becomes "Q1."
  (Notion would turn it into a list item and blank the title)
- "> **Teacher:** ... / > **Me:** ..." dialogue -> one quote block with <br> line breaks
- other blockquotes -> <callout>, icon by label: How to read 🧭 gray, Pause ⏸️ yellow,
  Beyond lecture 📚 blue, Accuracy/Caption/Convention/Trap/Notation/Warning ⚠️ gray,
  unlabelled 💡 gray (the last box of the file: ⚠️ gray)
- [[Note name]] wikilinks -> bold text; RTN like [[R1]] (no space) stays
- table cells: a leading "+" and "`code` + x" become a bold **+** (Notion makes them bullets)
- "$" outside code -> "\\$" (a $...$ pair would become inline math)
- literal "*" outside code (a*, Σ*, (a+b)*, ∅*) -> "\\*" (Notion turns 0*1* into 0<i>1</i>);
  **bold**, *italic* and "* " bullets stay; a table cell starting "* q1" -> "`*` q1"
- unlabelled code fences -> ```txt (Notion otherwise guesses "javascript")
- blank lines before tables and toggles
With --max-chars, a long result is also written as <out>.part1.md, .part2.md ... split only at
top-level "---" or "## " lines, never inside a toggle, callout, table or code block.
Prints a JSON line with counts (toggles, tables, mermaid, callouts, quotes, chars, parts) to
compare with the page after upload instead of re-reading the whole page.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ICONS = [
    (r"how to read", "🧭", "gray_bg"),
    (r"pause", "⏸️", "yellow_bg"),
    (r"beyond lecture", "📚", "blue_bg"),
    (r"accuracy|caption|convention|trap|notation|warning|flag", "⚠️", "gray_bg"),
]
DIALOGUE = re.compile(r"^>\s*\*\*(Teacher|Me|Student|Learner|Tutor|Q|A)\b[^*]*:?\*\*")


def protect_code(text, blocks):
    """Swap line-start code fences for placeholders. Called twice: once on the raw text, and
    again after blockquotes are unwrapped, for fences that sat inside a "> " box."""

    def keep(m):
        lang = m.group(1) or "txt"
        blocks.append(f"```{lang}\n{m.group(2)}```")
        return f"\x00CODE{len(blocks) - 1}\x00"

    return re.sub(r"(?m)^```([\w+-]*)\n(.*?)^```", keep, text, flags=re.S)


def convert_quotes(text):
    lines, out, i = text.split("\n"), [], 0
    groups = []
    while i < len(lines):
        if lines[i].startswith(">"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            groups.append((len(out), lines[i:j]))
            out.append(None)
            i = j
        else:
            out.append(lines[i])
            i += 1
    for n, (pos, grp) in enumerate(groups):
        if all(DIALOGUE.match(g) or not g[1:].strip() for g in grp) and any(DIALOGUE.match(g) for g in grp):
            body = [g[1:].strip() for g in grp if g[1:].strip()]
            out[pos] = "> " + "<br>".join(body)
            continue
        body = [re.sub(r"^> ?", "", g) for g in grp]
        head = re.sub(r"[*_]", "", body[0]).strip().lower()
        icon, color = ("⚠️", "gray_bg") if n == len(groups) - 1 else ("💡", "gray_bg")
        for pat, ic, col in ICONS:
            if re.match(pat, head):
                icon, color = ic, col
                break
        out[pos] = f'<callout icon="{icon}" color="{color}">\n' + "\n".join(body).strip() + "\n</callout>"
    return "\n".join(out)


def fix_table_row(line):
    cells = line.split("|")
    for k in range(1, len(cells) - 1):
        c = cells[k]
        c = re.sub(r"^(\s*)\+(\s)", r"\1**+**\2", c)
        c = re.sub(r"`(\s+)\+(\s+)", r"`\1**+**\2", c)
        c = re.sub(r"^(\s*)\*(\s)", r"\1`*`\2", c)  # "* q1" final-state marker: Notion makes it a bullet
        cells[k] = c
    return "|".join(cells)


# An italic span opens with "*" at the start or after a space/opening bracket, and closes with "*"
# that is not followed by a letter. Every other single "*" (a*, Σ*, )*, ∅*, 0*1*) is a literal star.
ITALIC = re.compile(r"(?:^|(?<=[\s(\[{\"'“‘/—–-]))\*(?=[^\s*])(.+?)(?<=[^\s*\\])\*(?!\w)")


def escape_stars(line):
    """Escape literal stars outside code spans; keep **bold**, *italic* and a leading "* " bullet."""
    lead = ""
    m = re.match(r"^(\s*\* )", line)
    if m:
        lead, line = m.group(1), line[m.end():]
    parts = line.split("`")
    for k in range(0, len(parts), 2):
        p = parts[k].replace("\\*", "\x03").replace("**", "\x01")  # keep stars the author escaped
        p = ITALIC.sub(lambda m: "\x02" + m.group(1) + "\x02", p)
        p = p.replace("*", "\\*")
        parts[k] = p.replace("\x02", "*").replace("\x01", "**").replace("\x03", "\\*")
    return lead + "`".join(parts)


def escape_dollars(line):
    parts = line.split("`")
    for k in range(0, len(parts), 2):
        parts[k] = re.sub(r"(?<!\\)\$", r"\\$", parts[k])
    return "`".join(parts)


def split_parts(text, limit):
    lines, parts, cur, depth, in_table = text.split("\n"), [], [], 0, False
    for ln in lines:
        boundary = depth == 0 and not in_table and (ln == "---" or ln.startswith("## "))
        if boundary and cur and sum(len(x) + 1 for x in cur) > limit * 0.6:
            parts.append("\n".join(cur).strip() + "\n")
            cur = []
        cur.append(ln)
        depth += len(re.findall(r"<(toggle|callout)\b", ln)) - len(re.findall(r"</(toggle|callout)>", ln))
        in_table = ln.startswith("|")
    parts.append("\n".join(cur).strip() + "\n")
    return parts


def convert(text):
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"\A\s*# .*\n", "", text)
    blocks = []
    text = protect_code(text, blocks)
    text = convert_quotes(text)
    text = protect_code(text, blocks)

    def toggle(m):
        summary, body = m.group(1).strip(), m.group(2).strip()
        summary = re.sub(r"^(\d+)\.", r"Q\1.", summary)
        return f"<toggle>\n{summary}\n\n{body}\n</toggle>"

    text = re.sub(r"<details><summary>(.*?)</summary>(.*?)</details>", toggle, text, flags=re.S)
    text = re.sub(r"\[\[(?:[^\]|]*/)?([^\]|/]* [^\]|]*)\]\]", r"**\1**", text)
    text = "\n".join(escape_stars(escape_dollars(fix_table_row(ln) if ln.startswith("|") else ln))
                     for ln in text.split("\n"))
    text = re.sub(r"(?m)^(?!\|)(.+)\n(?=\||<toggle>)", r"\1\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return re.sub(r"\x00CODE(\d+)\x00", lambda m: blocks[int(m.group(1))], text), blocks


def main(argv):
    src, dst = Path(argv[1]), Path(argv[2])
    limit = int(argv[argv.index("--max-chars") + 1]) if "--max-chars" in argv else 0
    text, blocks = convert(src.read_text(encoding="utf-8"))
    dst.write_text(text, encoding="utf-8", newline="\n")
    parts = split_parts(text, limit) if limit and len(text) > limit else [text]
    if len(parts) > 1:
        for k, p in enumerate(parts, 1):
            dst.with_suffix(f".part{k}.md").write_text(p, encoding="utf-8", newline="\n")
    print(json.dumps({
        "out": str(dst), "chars": len(text), "parts": len(parts),
        "toggles": text.count("<toggle>"),
        "tables": len(re.findall(r"(?m)^\|[\s:|-]*-[\s:|-]*\|\s*$", text)),
        "mermaid": sum(b.startswith("```mermaid") for b in blocks),
        "callouts": text.count("<callout"),
        "quotes": len(re.findall(r"(?m)^> ", text)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
