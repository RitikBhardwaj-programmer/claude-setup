<!-- Brief for a Notion-mirror subagent (Sonnet is enough). Fill the <...> parts. -->

Mirror these finished units to Notion: **<U0N, U0M>**. The content is already converted; send it as is.

Load the Notion tools first with ToolSearch: "select:mcp__f9a4be84-a5e9-4152-8091-74b52935b744__notion-fetch,mcp__f9a4be84-a5e9-4152-8091-74b52935b744__notion-create-pages,mcp__f9a4be84-a5e9-4152-8091-74b52935b744__notion-update-page".

Inputs (made by `to_notion.py`; do not edit or re-convert them, do not shorten anything):
<list of out files, with their .partN files where they exist, and each file's printed counts: toggles, tables, mermaid, callouts>

Per unit, under parent page `<parent page id>`, with notion-create-pages (`parent: {type: "page_id", page_id: ...}`, `allow_async: false`):
1. Unit page: title "<U0N full unit name>", icon <emoji>. Body: "Lectures Lx–Ly: [Lx <title>](https://youtu.be/<id>) · ..." and one "Topics: ..." line from the note's section headings.
2. Child "U0N Revision — <short topic list>" (icon ⚡), content = the Revision file.
3. Child "U0N Intuition — <H1 question after the dash>" (icon 🧠), content = the Intuition file.
For a file with parts: create the page with part1, then append each further part with notion-update-page `insert_content` (position end), in order.

Verify each child with ONE notion-fetch: toggle count, table count, Mermaid count and callout count equal the given counts; the last section is present; no toggle title is blank. Fix only what differs (update_content).

Report: per page, title and id; any count that differs and what you did. Do not touch the parent's status table or any other page; do not edit files on disk.
