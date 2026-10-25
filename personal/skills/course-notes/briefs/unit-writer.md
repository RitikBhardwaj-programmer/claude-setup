<!-- Brief for one writer (subagent or cloud session). Fill the <...> parts. For a cloud session,
     the "background" field takes the second block; the first block is the prompt. -->

Write the study notes for **<U0N name (Lx–Ly)>** [and **<U0M name (La–Lb)>**].

Setup (cloud only): the repo clones at `main`; first run `git fetch origin <base branch> && git checkout -b <unit branch> origin/<base branch>`.

Read first, in full: `<course dir>/Overview.md`, the skill templates `~/.claude/skills/course-notes/templates/intuition.md` and `revision.md` (cloud: the approved pilot pair `<course dir>/U01 ... - Intuition.md` / `- Revision.md` instead, since the skill is not installed there). Copy the structure, frontmatter, tone and depth exactly.

Sources: `<course dir>/transcripts/` files for <Lx–Ly> (read large ones with offset/limit). <List `hi` tracks: recover topics, rebuild numbers from standard facts, flag it in the accuracy notes.> Do NOT fetch from YouTube.
Topic hints: <exam-critical items this unit must cover, e.g. formulas, conventions, GATE patterns; mark Beyond lecture where the lecturer does not teach them>.

Create exactly these files in `<course dir>/`:
- `U0N <short> - Intuition.md`, `U0N <short> - Revision.md`
"Still open" link: U0N → [[U0(N+1) <short> - Intuition]].

Rules: timestamps only for what the lecturer really says (`▶ [mm:ss](https://youtu.be/<id>?t=<seconds>)`); exam add-ons in "Beyond lecture" boxes; recompute every numerical twice and show the working; write `[ [R1] ]` never `[[R1]]`; `author: ai`; created <YYYY-MM-DD>. Do NOT edit `Overview.md`, `Index.md` or `log.md`. Do NOT touch Notion.

Done = the files written [cloud: committed on branch `<unit branch>` and pushed]. Final message: the files, word counts, numbers you rebuilt (not from the source), anything you were unsure of.

---
(background, for a fresh/cloud session)
The user (an IT student; goal: <exam>) is building study notes for <course> in their Brain vault (repo RitikBhardwaj-programmer/Brain). Two notes per unit: Intuition (puzzle → naive model ❌ → breaks → better model → mechanism → formula last, analogies, Mermaid, Pause questions) and Revision (key facts, formula table, traps, 2–5 hidden-solution numericals, 10–15 hidden-answer self-test). U01 is the approved template. Style: real technical terms with a short bracketed plain-language explanation, concrete examples, start from the "why"; short active sentences. Exam accuracy beats narrative. A local session verifies and mirrors to Notion afterwards.
