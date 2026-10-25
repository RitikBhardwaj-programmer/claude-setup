---
name: course-notes
description: Turn a course's sources (YouTube playlist, book or PDF, slide deck) into per-unit study notes in the Brain vault, in two styles (Intuition and Revision), checked by scripts and mirrored to Notion. Modes - plan (decide units, styles, goal once per course), ingest (transcripts / PDF / PPTX text into the course folder), write (pilot unit, then the rest locally, in subagents or cloud sessions), verify (structure, links, timestamps, recompute numericals), mirror (Notion pages from a converter, no hand rewriting), status. Use when the user says "make notes from this playlist/book/PDF/slides", "notes for <subject> like COA", "continue the <course> notes", "mirror unit N to Notion", or /course-notes.
---

# course-notes

Why: the COA course (36 lectures, 11 units, 2026-10-25) worked, but a second session had to re-derive the whole pipeline: fetch script, three check scripts, six writer briefs, four Notion briefs. The Notion mirror alone cost about 1.18M subagent tokens because agents rewrote 470 KB by hand. This skill keeps what worked, as files.

Worked example: `C:\Users\DELL\Brain\Courses\COA (Janibul Bashir)\` (Overview, U01 = the approved pilot, transcripts, all units).

`SK` = this skill's folder. `PY` = `py -3 -I` (every script reconfigures stdout to UTF-8 itself).

## Course folder (one per course, in the vault)
```
Courses/<Course name>/
  Overview.md        the ONLY state file: sources, unit map + status, decisions, gotchas, Notion ids
  sources.tsv        lecture -> video id, minutes, title (YouTube courses)
  transcripts/       L<nn> <id>.<lang>.txt, or <book/deck>.md
  U01 <short> - Intuition.md / U01 <short> - Revision.md ...
```
Never keep course state in a separate handoff file: a stale one misled a session on 2026-10-25. Stamp each decision in Overview with its date; when one changes, strike it through and add the new one below it.

## plan (once per course)
1. Search the vault for the subject first (Vault Rules). Read `templates/Overview.md`.
2. Ask the hard constraints in ONE AskUserQuestion batch (only what is not already known):
   - goal (an exam such as GATE, a semester exam, deep understanding) and depth;
   - styles (default: Intuition + Revision, the U01 pair);
   - unit split (propose one from titles/chapters: 2-6 lectures or 1-3 chapters per unit);
   - output (vault only, or vault + Notion: which parent page);
   - writing mode for the units after the pilot (here / subagents / cloud sessions).
3. Write `Overview.md` from the template, then run `ingest`. Then write the **pilot** unit (U01) and stop for the user's review. Only after "good" do the rest run without per-unit review.

## ingest
```
PY SK/scripts/ingest.py playlist <url> "<course dir>"           # sources.tsv
PY SK/scripts/ingest.py youtube "<course dir>" [--only L05,L06]  # background: ~25 s per video
PY SK/scripts/ingest.py pdf <file.pdf> "<course dir>"            # text layer, else Marker OCR
PY SK/scripts/ingest.py pptx <file.pptx> "<course dir>"          # "## Slide n" sections + speaker notes
```
- Run YouTube fetches in the background, one batch at a time (no parallel batches: rate limits).
- Lines marked `hi` are English speech written in Devanagari: topics survive, numbers do not. List them in Overview Gotchas; the notes rebuild numbers from standard facts and say so.
- For a book: split the extracted `.md` by chapter headings before writing; cite page numbers instead of timestamps.

## write
Templates: `templates/intuition.md` and `templates/revision.md` hold the structure and rules. For the pilot, read them plus the COA U01 pair once. For later units the templates are enough; do not reread the whole worked example.
- **Here:** write unit by unit; read transcripts with offset/limit (some are 30k+ tokens).
- **Subagents:** one per 1-2 units, `run_in_background`, brief = `briefs/unit-writer.md` filled in.
- **Cloud sessions** (keep running when the PC sleeps):
  1. transcripts must be committed and pushed first; cloud sessions cannot fetch YouTube;
  2. one session per 1-2 units (balance by lecture count), brief = `briefs/unit-writer.md`;
     each writes only its own unit files on its own branch, never Overview/log/Index;
  3. start them in the same turn as the user's "go": the app refuses to start sessions in a turn
     that a background-task notification started;
  4. cloud sessions do not report back; watch with a background `git ls-remote --heads origin '<prefix>*'` loop.

## verify (before merging or mirroring any unit)
1. `PY SK/scripts/check_units.py "<course dir>" --sample 3`: frontmatter, sections, self-test count, links, mm:ss vs ?t=, foreign video ids, stamps past the video end; prints transcript text next to sampled claims. Read the samples.
2. Recompute **every** worked numerical in each Revision §4. Use a scratch script for encodings, floats, bit fields; trace tables (pipelines, caches, Booth) by hand. A fluent wrong answer is the main risk.
3. Read each §2 formula table once for wrong or confusing rows.
4. Fix in the vault file, then merge (cloud branches) and update Overview status. Ask before merging branches the user did not mention.

## mirror (Notion)
1. Convert each note: `PY SK/scripts/to_notion.py "<note>.md" "<out>.md" --max-chars 30000`. It does every conversion (toggles, callouts by label, dialogue quotes, bold `+` in cells, `\$`, `txt` fences) and prints counts. Over 30k chars it also writes `.partN.md` files split at safe boundaries.
2. Create pages with `briefs/notion-mirror.md` (a Sonnet subagent per 2-3 units is enough): unit page (emoji icon, lecture links, topics line), then the Revision child, then the Intuition child, under the course parent.
3. Verify by the printed counts (toggles, tables, mermaid, callouts) on one fetch per page; do not re-read pages twice.
4. Update the status table on the Notion parent and in Overview.
Known Notion quirks are handled by the converter; new ones go into Overview Gotchas and this converter.

## status
Read Overview: unit table, open decisions, gotchas. Report what is done, drafting, todo, and the next action.

## Rules
- Exam accuracy beats narrative. Recompute numbers; state conventions (e.g. PC-relative base, split-cycle register file).
- Cite a timestamp/page only for what the source really says. GATE or textbook material the source does not teach goes in a box marked **Beyond lecture**.
- Never present rebuilt content (garbled captions) as the lecturer's words; say so in the accuracy notes.
- Write `[ [R1] ]`, never `[[R1]]` (it becomes a wikilink).
- Emojis are fine inside notes and Notion pages (visual markers); keep them out of messages the user sends as themselves.
- Vault Rules: `author: ai`, dates YYYY-MM-DD, one `log.md` line per session, never delete notes. Commit and push only with the user's OK.
