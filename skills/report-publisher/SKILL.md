---
name: report-publisher
description: Turn a Markdown report into a professional themed web page (published as an Artifact) plus an A4 PDF, with diagrams, tables, verdict pills and automatic layout and page checks. Use when the user wants a report, review, specification or write-up "for teachers", "for the vendor", "as a PDF", "as a web page", or "to share", or says "make a report/PDF of this". Not for code docs inside a repo.
---

# report-publisher

This pipeline made four real reports (a Wi-Fi survey, a lab test, a design review and a vendor spec). It packages the steps that worked, so they are not rebuilt each time.

**Setup:**
- **Python:** use the `python` value in `~/.claude/setup.json` if that file exists. Otherwise use `python3` (or `py -3` on Windows). It needs `markdown-it-py` and `pypdfium2`; if either is missing, install them with `pip install markdown-it-py pypdfium2`, after asking the user. Below this is called `MPY`.
- **`SK`** is this skill's folder, `~/.claude/skills/report-publisher`.
- **Chrome or Chromium** is needed for the PDF step. Set `CHROME=/path/to/chrome` if it is not found.

## 1. Agree the brief (one question batch)
Ask only what the request does not answer:
- **Audience:** teachers, vendor, college IT. This sets the tone.
- **Format:** web page + PDF (default), PDF only, or Markdown.
- **Hard constraints:** scale, limits, deadlines, what must be included.
Use the light-only navy theme unless the user asks otherwise.

## 2. Write the Markdown
- Line 1 is `# Heading`, which becomes the page H1. The first paragraph(s) become the intro (`--intro N`).
- Each `## Section` becomes a card-free section with a rule above it.
- Tables: cells that are exactly `Pass` / `Partial` / `Gap` or `MUST` / `SHOULD` / `INFO` become pills.
- Diagrams: write SVG files and put `[[figure: diagrams/arch.svg | Caption]]` on its own line.
  - SVG classes from the theme: `box`, `box hl`, `box add`, `box ok`, `box no`, `t1`, `t2`, `lab`, `warn`, `arrow`, `head`, `nb` / `nbt` (numbered badges), `life`.
  - Give every `<marker>` a unique id per SVG.
  - Keep text inside its box: about 7 px per character at `t2` size.
- Score bar: `[[score: pass=4, partial=4, gap=8]]`.
- Images: `![alt](img/photo.jpg)`, with the files copied into the output folder.
- Label every claim as measured, sourced (link), **estimate** or **inference**.
- **Redact first:** look at every photo or screenshot for passwords, keys or personal data, and blur them with PIL (crop → GaussianBlur → paste) before using it.

## 3. Build
```bash
MPY SK/scripts/build.py report.md --out reports/<name> --title "Short Name" \
    --eyebrow "Project · Report type" --meta "Date=6 Oct 2026" --meta "Scale=10,000 students"
```
It prints the counts of sections, tables and figures and the local images to publish, and it fails if an image is missing. For a page with custom charts (JS-drawn SVG), build first, then add the chart `<div class="chart">` and script by hand. `theme.css` already styles `.chart`, `.legend`, `.tip`, `.axis` and `.grid`.

## 4. Check the layout (no screenshots needed)
1. Serve the folder: `python -m http.server <port> --bind 127.0.0.1` (Bash, `run_in_background`).
2. Open it in the browser pane. Call `resize_window` (for example 1200×900) **before** checking, because a hidden pane reports width 0.
3. Run `SK/scripts/check.js` with `javascript_exec`. Fix every overlap, outside label, spill, broken image, local link and any horizontal overflow, then run it again.
   - The theme's grid children have `min-width: 0`. Keep that, or wide SVGs and tables push the page sideways.
   - Scope SVG `min-width` rules to the chart SVG only. A bare `.chart svg` also enlarges the small legend icons.
4. Screenshots time out when the app window is in the background. Rely on `check.js`, and take one screenshot only if the pane is visible.
5. Stop the server when done.

## 5. PDF
```bash
MPY SK/scripts/to_pdf.py reports/<name> --name Report-Name.pdf
```
- It uses Chrome headless with a throwaway profile. Edge printed nothing without an error.
- It prints characters per page and warns about nearly empty pages. That warning usually means a big block is marked `break-inside: avoid`; let it break.
- To look at pages visually, render one to PNG and Read it: `MPY -c "import pypdfium2 as p; p.PdfDocument('X.pdf')[0].render(scale=0.6).to_pil().save('page1.png')"`.

## 6. Publish and deliver
- Publish with the Artifact tool: `file_path` = `index.html`, `files` = the local images listed by build.py, plus an `icon` and a one-sentence `description`. Republish the same path to update it.
- Send the PDF with SendUserFile (`display: attach`).
- Tell the user the page is private until they share it.
- Report what was checked and what was not.

## Gotchas collected
- Bash heredocs with quotes or Windows paths break: write helper scripts to a file with the Write tool.
- On Windows, `PYTHONIOENCODING=utf-8` stops cp1252 crashes on `→` and `−`.
- Fonts come from Google Fonts only (the Artifact CSP allows it). The theme already links Source Serif 4, Source Sans 3 and JetBrains Mono.
