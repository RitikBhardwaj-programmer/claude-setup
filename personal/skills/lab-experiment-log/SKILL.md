---
name: lab-experiment-log
description: Record a hardware or network lab experiment (AP tests, RADIUS/802.1X logins, Wi-Fi surveys, speed tests) as one evidence note right after it happens, with a server-clock timeline, raw log lines, database rows and pass/fail per expectation. Use when the user says "log this experiment", "save the results", "write up what we just tested", or when a live lab test in this session has just finished. Also use to reconstruct an older experiment from logs.
---

# lab-experiment-log

Why: on 2026-10-06 a report on the "S23 experiment" had to be rebuilt from an old chat transcript, plus a Docker restart to reach the database. One note written at test time would have made that a single file read.

## When
- At the end of any session where a real device was tested: AP, phone, laptop, switch, survey or speed test.
- Before containers are recreated. Container logs are lost then; only the database and detail files survive.

## Where
- AAA lab: `C:/Users/DELL/Networking Project/aaa-server/docs/experiments/YYYY-MM-DD-<slug>.md`. That folder is in the aaa-server git repo; don't commit unless asked.
- Other projects: `<project>/docs/experiments/` (create it).
- Then add a one-line pointer to the project memory (or vault) note and a line to the vault `log.md`.

## Steps
1. **Collect evidence while it still exists.** For the AAA lab (Docker must be running; all reads are read-only):
   ```bash
   PYTHONIOENCODING=utf-8 py -3 ~/.claude/skills/lab-experiment-log/scripts/collect_aaa_evidence.py \
     --lab "C:/Users/DELL/Networking Project/aaa-server" --since "YYYY-MM-DD HH:MM" --until "YYYY-MM-DD HH:MM"
   ```
   It prints Markdown with login results (radpostauth), every accounting packet with the **server receive time** (detail files), and RADIUS log lines. Rows from NAS `10.89.0.50` are the test suite.
   For other experiments, copy the raw numbers exactly: speed tests, signal bars, screenshots.
2. **Fill `template.md`** (next to this file). Rules:
   - Times come from the server clock. Say which clock any other time comes from. The lab AP clock is wrong.
   - Quote log lines and rows **verbatim** in code blocks. Don't paraphrase evidence.
   - State the expectation **before** the result, then mark each one pass / fail / not tested.
   - Separate **observed** facts from **inferences** (explanations not yet tested), and list the tests that would prove them.
   - **Redact:** never write passwords or secrets. Blur them in photos. Device MACs and lab IPs are fine.
3. **Link it:** add the note path to the project memory, and to any report built from it.

## Gotchas
- `docker compose logs` only covers the current container. Run the collector before `docker compose up --build`.
- Starting Docker Desktop also starts the lab RADIUS on the hostel LAN. Ask before starting it.
- A reconnect with cached keys (PMK caching) creates an accounting Start with **no** login row. That is evidence too, not a gap.
