---
name: hackhunt
description: Find, rank and track hackathons for the user (India, online and offline) with eligibility and deadlines first. Modes - scan (Devpost, MLH, Unstop and Devfolio scripts, browser as fallback, curated corporate challenges), shortlist (rank with the exact team/eligibility sentence quoted), status (due this week, counts per stage). Use on /hackhunt, "find me hackathons", "what hackathons are open", "any deadlines this week", "scan Unstop/Devfolio". Never registers, submits, pays or logs in for the user.
---

# hackhunt

Why: good hackathons are lost to rules found late (Innovathon 2.0 was dropped because of a minimum-3-member team rule). This skill finds hackathons from sources that allow reading, shows the **exact team and eligibility sentence** for each one, ranks them, and tracks deadlines. **The user decides, registers and submits.** Scope: find + rank + deadlines only. No idea generation, no submission drafts.

## Hard rules (obey in every mode)
1. **Never register, apply, submit, pay or click a final confirm button** on any hackathon site, even if the user says "just register me": tell them to do it. Never fill a registration form.
2. **Never log in.** No passwords, no tokens, no sign-in on the user's behalf. If a page needs a login, say so and skip it.
3. **Unstop and Devfolio: read-only, human pace.** At most 3 page loads per site per run, counting listing pages, detail/event pages and challenge URLs on those domains (including subdomains like `*.devfolio.co`), a few seconds between pages, no repeated re-scans the same day. Script requests count toward the 3 loads per site: `fetch_unstop.py` and `fetch_devfolio.py` default to `--pages 2`, which leaves 1 load for a detail page (hard cap 3 and a 2 s pause are enforced in code). "No re-scan the same day" is a manual rule: no code enforces it, so check before you run a script again. If a page shows a CAPTCHA or "unusual traffic": stop that site and tell the user.
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
- **Scrapling venv** (only for `stealth_fetch.py`, the Cloudflare fallback): `PYS` = `~/.claude/tools/scrape-venv/Scripts/python.exe`. If it is missing, ask the user, then run `py -3 -m venv ~/.claude/tools/scrape-venv` and `PYS -m pip install "scrapling[fetchers]"`. It uses the system Chrome (`real_chrome=True`), not a bundled browser.

## Tools (all print JSON except `stealth_fetch.py`, which prints page text or HTML; run from anywhere)
```bash
PY SK/scripts/fetch_devpost.py [--pages 3] > devpost.json      # Devpost public listing JSON
PY SK/scripts/fetch_mlh.py [--season 2027] [--country IN] [--all] > mlh.json   # MLH season page (India + digital by default)
PY SK/scripts/fetch_unstop.py [--pages 2] > unstop.json          # Unstop public search JSON (team range, fee, prizes, reg deadline)
PY SK/scripts/fetch_devfolio.py [--pages 2] > devfolio.json      # Devfolio search API (team size, dates, FAQ fee/eligibility)
PY SK/scripts/fetch_devpost_rules.py [--limit 10] < devpost.json > devpost_rules.json   # adds team_max + eligibility from each /rules page
PYS SK/scripts/stealth_fetch.py URL [--text|--html]              # Cloudflare fallback, one URL per call (scrape-venv Python)
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

1. **Devpost** and **MLH**: run the two fetch scripts. For Devpost, pipe through the enrichment step first: `fetch_devpost.py | fetch_devpost_rules.py --limit 10 | hacks_db.py add` (the listing has no team size or eligibility; the rules pages give `team_max` and the Eligibility section). A failed rules page is reported on stderr and that row stays without them; a Cloudflare challenge or HTTP 403/429 stops the enrichment (the other rows pass through unchanged), so re-run later or handle those rows one by one: read it with `stealth_fetch.py --html` or in the browser before ranking. MLH: pipe to `hacks_db.py add`; rows are mostly US events, the India filter keeps a few.
2. **Unstop** (rule 3): `fetch_unstop.py | hacks_db.py add`. The public JSON gives name, organiser, team range, fee, mode, city, prizes and the registration deadline as a date (no countdown maths). `eligibility_text` holds listing tags only: open the detail page for the full rules of rows that look worth it. **If the script fails**, fall back to `https://unstop.com/hackathons?oppstatus=open` in the built-in browser (max 3 pages; cards show team range, fee, mode, tags and "N days left" = today + N; skip the date for "N months left") and build JSON with `"platform": "unstop"`.
3. **Devfolio** (rule 3): `fetch_devfolio.py | hacks_db.py add`. The search API gives name, mode, city, team min/max, dates, registration deadline, themes, and the "team size", "fee" and "who can participate" FAQ answers when the organiser wrote them (otherwise those stay empty: write `CHECK: team size not stated`). **If the script fails**, fall back to `https://devfolio.co/hackathons/open` in the browser; team size and fee are on the event page (`<slug>.devfolio.co`, FAQ block). Open event pages only for promising rows.
   **Cloudflare:** if a page shows a Cloudflare challenge, run `stealth_fetch.py` with the scrape-venv Python (use `--html` when you need CSS-only text such as Devpost's `Team max size`). Turnstile solving is allowed on public listing and detail/rules pages only, never on login, register or apply pages (`stealth_fetch.py` refuses linkedin.com, naukri.com and login/signin/signup/register/apply paths in code).
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
- **Vault cross-check first (any mode, before you show or ask about a registered, submitted or advanced row).** Why: results get saved to the Brain vault (`C:/Users/DELL/Brain`) but not to `hacks.db`, so the tracker lags (on 2026-11-25 it still said "registered" for Catalyst, whose Top 10 result was in `Projects/CareCircle/Overview.md`). For each such row, Grep the vault `*.md` files for the event name (and its project name if a note links one), and read the matching lines. If a dated line states the submission or result, apply the moves in order (e.g. `submitted` then `advanced`), with a note that cites the vault note path. If the vault and the tracker conflict, or the line is vague, ask the user. Never guess. A vault line counts as the user's own report. Ask the user only about rows the vault does not answer.
- `hacks_db.py due --days 7` first (soonest first), then `list` per status for counts and a table of shortlisted/registered/submitted rows with dates. Export `tracker.csv`.
- Registering: never do it for the user. When they say they registered, run `status ID registered --note "team: ..."`.
- Updating: `status ID submitted|advanced|won|out --note "..."` as the user reports results.
- Metric: **rounds advanced per hackathon entered** = (advanced + won) ÷ (registered or later). Report it with the sample size and say it is meaningless below ~10 entries. Hours spent are user-reported only: ask, never estimate.
- Habit suggestion: scan weekly; pick at most 2 at a time.

## Gotchas
Live checks done on 2026-10-18 (read-only; Devpost JSON and MLH page by script, Unstop and Devfolio in the built-in browser, 2 pages each):
- **Devpost** `https://devpost.com/api/hackathons?status[]=open&status[]=upcoming&page=N` returns JSON (9 per page, `meta.total_count` 191), no login. robots.txt allows it. It is an unofficial endpoint: if `fetch_devpost.py` fails, report it and read the site in the browser instead. Fields: title, organization_name, displayed_location (`Online` or a city), `submission_period_dates` (text like `Aug 31 - Oct 23, 2026`), themes, `prize_amount` (HTML with a currency symbol), url. **No team size, fee or eligibility**, and no registration deadline: `event_start` is the submission-window start, so the same event from another platform may not dedupe (different month). Rules pages are at `<slug>.devpost.com/rules`. The 403 seen on 2026-10-18 came from WebFetch only: plain urllib read them on 2026-11-10, which `fetch_devpost_rules.py` uses. On 2026-11-25 plain urllib met a Cloudflare challenge on the first rules page, while `stealth_fetch.py <slug>.devpost.com/rules --text` read 7 pages in a row: plan a stealth pass for the top rows. Most Devpost hackathons are US-sponsor online events; the PayPal rules quote allows individual entry and excludes only sanctioned countries (India not listed).
- **MLH** `https://www.mlh.com/seasons/<year>/events`: data is JSON inside `<script data-page="app">` (`props.upcomingEvents`, 76 events for 2027). Only 1 was in India on this date (`hackCBS 9.O`, New Delhi, 2026-10-31); the rest are US/EMEA. Fields: name, startsAt, endsAt, formatType (physical / hybrid_physical / digital), venueAddress.country, websiteUrl. No team size, fee, prize or reg deadline. If the layout changes, `fetch_mlh.py` fails loudly.
- **Unstop** `https://unstop.com/hackathons?oppstatus=open`: needs about 5 s to render; `get_page_text` then shows ~15 cards per page with team range, fee, mode or address, eligibility tags (truncated with `+N`), "N days left", registered count. Dates shown are "Posted" dates and a relative countdown, not a deadline field. Detail pages (`/hackathons/<slug>-<id>`) show team size, prize/perks and "Dates & Deadlines" tabs, but long descriptions are cut at "Read More". Clicking a card did not navigate in the pane: read the `href`s with JavaScript and navigate. Many listings are small college events (some include fees of Rs 200-1200).
- **Devfolio** `https://devfolio.co/hackathons/open`: no login needed; cards show name, theme, ONLINE/OFFLINE, `STARTS dd/mm/yy`, participant count. Event pages (`<slug>.devfolio.co/overview`) show dates, "APPLICATIONS CLOSE IN" countdown, prizes, and FAQ items `Team size` and `Registration costs?`. The page can redirect to `/overview`.
- **challenges.yaml** facts come from official pages where possible. On 2026-10-18 only sih.gov.in was read directly; Google Solution Challenge, Flipkart GRiD, HackOn with Amazon and others are `secondary` (Internshala listing or search results) and must be confirmed on the official page. hack2skill.com refused the connection from the build session.
- Unstop "N days left" is relative to the day you read the page; write the computed date into `reg_deadline`, not the countdown.
- Dedupe key is normalised name + event-start month, so two spellings of the same event in different months stay separate. Check before shortlisting twice.
- Probe on 2026-11-10: plain urllib reads Unstop (`https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&oppstatus=open&page=N&per_page=15`, `data.data[]`, `data.last_page`) and Devfolio (`POST https://api.devfolio.co/api/search/hackathons` with `{"type":"application_open","from":N,"size":S}`, `hits.hits[]._source`, `hits.total.value`). Devfolio dates are UTC and are converted to the event's timezone. Unstop has no event-start field, so `event_start` is empty there.
- Tests (`py -3 -m unittest` in `scripts/`) use fixtures trimmed from real responses (2026-10-18 and 2026-11-10); no network. Challenges are not scripted, so no tests cover them. `stealth_fetch.py` tests cover argument parsing and text stripping only, not the browser.
