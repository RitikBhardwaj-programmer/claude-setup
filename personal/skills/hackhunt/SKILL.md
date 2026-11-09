---
name: hackhunt
description: Find, rank and track hackathons for the user (India, online and offline) with eligibility and deadlines first. Modes - scan (Devpost and MLH scripts, Unstop and Devfolio read in the browser, curated corporate challenges), shortlist (rank with the exact team/eligibility sentence quoted), status (due this week, counts per stage). Use on /hackhunt, "find me hackathons", "what hackathons are open", "any deadlines this week", "scan Unstop/Devfolio". Never registers, submits, pays or logs in for the user.
---

# hackhunt

Why: good hackathons are lost to rules found late (Innovathon 2.0 was dropped because of a minimum-3-member team rule). This skill finds hackathons from sources that allow reading, shows the **exact team and eligibility sentence** for each one, ranks them, and tracks deadlines. **The user decides, registers and submits.** Scope: find + rank + deadlines only. No idea generation, no submission drafts.

## Hard rules (obey in every mode)
1. **Never register, apply, submit, pay or click a final confirm button** on any hackathon site, even if the user says "just register me": tell them to do it. Never fill a registration form.
2. **Never log in.** No passwords, no tokens, no sign-in on the user's behalf. If a page needs a login, say so and skip it.
3. **Unstop and Devfolio: read-only, human pace.** At most 3 page loads per site per run, counting listing pages, detail/event pages and challenge URLs on those domains (including subdomains like `*.devfolio.co`), a few seconds between pages, no repeated re-scans the same day. If a page shows a CAPTCHA or "unusual traffic": stop that site and tell the user.
4. **Eligibility is the point.** Every shortlist row quotes the exact team/eligibility sentence you used, with its source. If team size or eligibility is not stated, write `CHECK: team size not stated` (never a guess, never "probably solo").
5. **Scam / low-trust flags:** a fee to "guarantee" selection or a prize, no organiser identity, contact only by WhatsApp/Telegram, prize claims with no sponsor. Show a ⚠ with the reason. A normal entry fee only lowers the score.
6. **No secrets in files or chat.** Private data (prefs, challenges, hacks.db, tracker.csv) stays in the data folder, never in claude-setup or GitHub.
7. **No calendar or Notion writes.** The user asks for deadlines in chat (`status` mode); this skill does not create calendar events or To-Do pages.
8. Report failures honestly (a fetcher errored, a site was skipped). Do not fill gaps with made-up hackathons or dates.

## Setup
- **`SK`** = `~/.claude/skills/hackhunt`. **`DATA`** = `C:/Users/DELL/HackHunt` (`HACKHUNT_DIR` env var overrides). **`PY`** = `py -3` (scripts are standard-library only).
- Files in DATA: `prefs.yaml` (travel, fee, team, score weights), `challenges.yaml` (curated national/corporate challenges, each with an official URL and how it was checked), `hacks.db`, `tracker.csv`.
- Skills and interests: read `C:/Users/DELL/JobHunt/profile.yaml` (one profile, no second copy). If `prefs.yaml` or `profile.yaml` is missing or has `<...>` placeholders, stop and ask.
- Windows: set `PYTHONIOENCODING=utf-8` if Python prints non-ASCII; write multi-line JSON to a file, not long heredocs.

## Tools (all print JSON; run from anywhere)
```bash
PY SK/scripts/fetch_devpost.py [--pages 3] > devpost.json      # Devpost public listing JSON
PY SK/scripts/fetch_mlh.py [--season 2027] [--country IN] [--all] > mlh.json   # MLH season page (India + digital by default)
PY SK/scripts/hacks_db.py add < hacks.json         # normalise + dedupe into DATA/hacks.db
PY SK/scripts/hacks_db.py list [--status new] [--limit 50]
PY SK/scripts/hacks_db.py show ID                  # full record incl. eligibility_text
PY SK/scripts/hacks_db.py score ID 82 "one-line reason"
PY SK/scripts/hacks_db.py status ID shortlisted [--note "..."]
PY SK/scripts/hacks_db.py elig ID "exact team/eligibility sentence"   # replace the stored quote
PY SK/scripts/hacks_db.py due [--days 7]           # reg/submit deadlines in the next N days
PY SK/scripts/hacks_db.py export                   # DATA/tracker.csv
```
Statuses: `new → shortlisted → registered → submitted → advanced / won / out`; `skipped` only from `new`/`shortlisted`. The tool refuses illegal moves (e.g. new → registered): that error is correct, tell the user. Only the user can say they registered or submitted.

Raw hackathon dict fields: `name` (required), `organiser`, `platform`, `mode` (online/offline/hybrid), `city`, `team_min`, `team_max`, `solo_ok`, `fee`, `prize_pool`, `perks`, `themes`, `reg_deadline`, `submit_deadline`, `event_start`, `event_end` (dates as `YYYY-MM-DD`; leave empty when unknown), `eligibility_text` (the quoted sentence), `url`, `source`.

## Mode: scan
Goal: add fresh hackathons to the database. Tell the user which sources you will use first; skip any that fail and say so.

1. **Devpost** and **MLH**: run the two fetch scripts, pipe each to `hacks_db.py add`. Devpost listing has no team size or eligibility (stay empty; read the event's `/rules` page in the browser before ranking the ones that matter). MLH rows are mostly US events; the India filter keeps a few.
2. **Unstop** (rule 3): open `https://unstop.com/hackathons?oppstatus=open` in the built-in browser, read the page text (max 3 pages). Each card gives name, organiser, team range (`2 - 4 Members` or `Individual Participation`), fee if any, mode/address, eligibility tags, and "N days left" (registration deadline = today + N; skip the date for "N months left"). Open a detail page only for rows that look worth it (the full rules sit behind "Read More"/Details). Build JSON with `"platform": "unstop"`.
3. **Devfolio** (rule 3): open `https://devfolio.co/hackathons/open`. Cards give name, theme, ONLINE/OFFLINE, start date (`STARTS dd/mm/yy`) and a participant count; team size and fee are on the event page (`<slug>.devfolio.co`, FAQ block "Team size", "Registration costs?"). Open event pages only for promising rows.
4. **Corporate/national challenges**: read `challenges.yaml`. Open each `url` (WebFetch, or the browser if it fails), refresh dates, quote the team/eligibility sentence, and add with `"platform": "challenge"`. Cycles that ended stay as rows with a past `reg_deadline` (the shortlist filter drops them) and a note for the next expected window. Update `challenges.yaml` `checked` lines when you verify something.
5. `hacks_db.py export`. Print a summary: sources run/skipped/failed, rows added, duplicates. Then continue to **shortlist** unless the user only asked to scan.

## Mode: shortlist
Goal: a short ranked list the user can disagree with.

1. `hacks_db.py list --status new --limit 200`; read `prefs.yaml` and `profile.yaml`.
2. **Hard filter** (set `skipped` with a note, show the count): all dates already passed (`reg_deadline` or `submit_deadline` before today, and no later date); abroad offline (not India, not online) unless the page says travel is paid; not a tech/building hackathon (quiz, dance, robotics race, "Law/Medical" only); student-ineligible by the quoted sentence (e.g. startups only, working professionals only, not open to India). **A fee never drops a row.**
3. **Eligibility check:** for each survivor you want to rank, make sure `eligibility_text` holds the actual team/eligibility sentence. If it is only a listing tag, open the event's rules/FAQ page (rule 3 limits apply) and store the sentence with `hacks_db.py elig ID "exact sentence"` (it replaces the stored text; re-adding only fills empty fields). Use `show ID` for the quote, because `list` cuts `eligibility_text` to 300 characters. If it cannot be found, keep the row with `CHECK: team size not stated`.
4. **Fit score 0-100** with `hacks_db.py score ID N "reason"`, weights from `prefs.yaml`:
   - Career value, 30: PPI/internship/interview perk, sponsor brand, finals at a company.
   - Theme fit / learning, 25: themes vs skills in `profile.yaml` (strong counts full, working half, learning small).
   - Prize, 20: pool vs likely competition (use registrations; 60,000 registered on a $300 prize is low).
   - Practicality, 25: online > India offline; solo-allowed bonus; team events keep full points but show the rule ("needs 3-4: ask friends"); entry fee and travel cost lower the score; deadline too close to prepare lowers it.
   Be calibrated: most land 40-70, use 85+ rarely. The reason names the strongest match and the biggest gap in one line.
5. Show a table of the top 15: `id | score | name | organiser | mode/city | team rule | fee | deadline (reg / submit) | ⚠ | quoted eligibility sentence + source | link`. The quoted sentence is mandatory (rule 4). Ask: "Shortlist which? (ids, or 'top 5')". Set chosen ones to `shortlisted`; never shortlist without the user's pick, except when they said "top N". Then `export`.

## Mode: status
- `hacks_db.py due --days 7` first (soonest first), then `list` per status for counts and a table of shortlisted/registered/submitted rows with dates. Export `tracker.csv`.
- Registering: never do it for the user. When they say they registered, run `status ID registered --note "team: ..."`.
- Updating: `status ID submitted|advanced|won|out --note "..."` as the user reports results.
- Metric: **rounds advanced per hackathon entered** = (advanced + won) ÷ (registered or later). Report it with the sample size and say it is meaningless below ~10 entries. Hours spent are user-reported only: ask, never estimate.
- Habit suggestion: scan weekly; pick at most 2 at a time.

## Gotchas
Live checks done on 2026-10-18 (read-only; Devpost JSON and MLH page by script, Unstop and Devfolio in the built-in browser, 2 pages each):
- **Devpost** `https://devpost.com/api/hackathons?status[]=open&status[]=upcoming&page=N` returns JSON (9 per page, `meta.total_count` 191), no login. robots.txt allows it. It is an unofficial endpoint: if `fetch_devpost.py` fails, report it and read the site in the browser instead. Fields: title, organization_name, displayed_location (`Online` or a city), `submission_period_dates` (text like `Aug 31 - Oct 23, 2026`), themes, `prize_amount` (HTML with a currency symbol), url. **No team size, fee or eligibility**, and no registration deadline: `event_start` is the submission-window start, so the same event from another platform may not dedupe (different month). Rules pages are at `<slug>.devpost.com/rules` and returned 403 to WebFetch; the browser worked. Most Devpost hackathons are US-sponsor online events; the PayPal rules quote allows individual entry and excludes only sanctioned countries (India not listed).
- **MLH** `https://www.mlh.com/seasons/<year>/events`: data is JSON inside `<script data-page="app">` (`props.upcomingEvents`, 76 events for 2027). Only 1 was in India on this date (`hackCBS 9.O`, New Delhi, 2026-10-31); the rest are US/EMEA. Fields: name, startsAt, endsAt, formatType (physical / hybrid_physical / digital), venueAddress.country, websiteUrl. No team size, fee, prize or reg deadline. If the layout changes, `fetch_mlh.py` fails loudly.
- **Unstop** `https://unstop.com/hackathons?oppstatus=open`: needs about 5 s to render; `get_page_text` then shows ~15 cards per page with team range, fee, mode or address, eligibility tags (truncated with `+N`), "N days left", registered count. Dates shown are "Posted" dates and a relative countdown, not a deadline field. Detail pages (`/hackathons/<slug>-<id>`) show team size, prize/perks and "Dates & Deadlines" tabs, but long descriptions are cut at "Read More". Clicking a card did not navigate in the pane: read the `href`s with JavaScript and navigate. Many listings are small college events (some include fees of Rs 200-1200).
- **Devfolio** `https://devfolio.co/hackathons/open`: no login needed; cards show name, theme, ONLINE/OFFLINE, `STARTS dd/mm/yy`, participant count. Event pages (`<slug>.devfolio.co/overview`) show dates, "APPLICATIONS CLOSE IN" countdown, prizes, and FAQ items `Team size` and `Registration costs?`. The page can redirect to `/overview`.
- **challenges.yaml** facts come from official pages where possible. On 2026-10-18 only sih.gov.in was read directly; Google Solution Challenge, Flipkart GRiD, HackOn with Amazon and others are `secondary` (Internshala listing or search results) and must be confirmed on the official page. hack2skill.com refused the connection from the build session.
- Unstop "N days left" is relative to the day you read the page; write the computed date into `reg_deadline`, not the countdown.
- Dedupe key is normalised name + event-start month, so two spellings of the same event in different months stay separate. Check before shortlisting twice.
- Tests (`py -3 -m unittest` in `scripts/`) use fixtures trimmed from real 2026-10-18 responses; no network. Unstop/Devfolio/challenges are not scripted, so no tests cover them.
