---
name: augment-lens
description: "Check an idea, a project change or a discussion topic with the automation-vs-augmentation lens: which parts should be fully automated, which should amplify a human who keeps the judgment, where the human must stay sharp, and what can go wrong (so-so automation, automation bias, deskilling). Ends with a short verdict, a better shape of the idea and a first step. Use whenever the user presents an idea ('I want to build/automate/add X', 'what if we...', 'thinking about...'), proposes a change to a project, tool or workflow, or wants to discuss or evaluate a plan, even if they never mention automation or augmentation; also on /augment-lens. Skip for factual lookups, plain bug fixes, explanations, and work the user has already decided and only wants done. For a high-stakes choice between several options, llm-council is the heavier tool; augment-lens can run first as a quick pass."
---

# Augment lens

Every idea that uses a tool sits somewhere on a spectrum. At one end, **automation** removes the human from a task. At the other end, **augmentation** keeps the human in charge and makes them more capable. Neither end always wins. Repetitive, well-specified work should be fully automated. Judgment work should be augmented. The value of this lens is to make that split explicit, task by task, and to catch the known failure modes early.

Evidence and sources behind the checklist: `C:\Users\DELL\Brain\Chats\2026-10-07 Automation vs augmentation analysis.md`. Read it only when the user asks why a rule exists or wants sources.

## Step 1: Frame

- Restate the idea in one sentence.
- If it concerns the current project, read only what you need to make the review specific (the named file, the project `CLAUDE.md`, or the relevant module). Do not explore widely.
- Separate **known facts** (exists, measured, tested) from **assumptions** (hoped, untested).
- If the idea is too vague to split into tasks, ask one clarifying question, then continue.

## Step 2: Split into tasks and place each one

List the 3–6 main tasks inside the idea. For each, choose one:

| Choose | When |
|---|---|
| **Automate** | repetitive, well specified, low judgment, cheap to verify (tests, backups, formatting, data moves) |
| **Augment** | needs judgment, context, taste or creativity; the tool drafts or suggests, a human decides |
| **Manual** | high stakes and hard to verify, or a skill the user must keep practising |

## Step 3: Run the checks

1. **Human role:** for each augmented task, name exactly where the human decides. Is that the right place?
2. **Frontier check:** can the human tell when the tool is wrong? If not, add a check (test, second source, sample review). Tools fail on tasks that look as easy as ones they handle well.
3. **Skill decay:** which skill could the user lose by relying on the tool? Is that acceptable? If not, keep a manual path or an explain-why step.
4. **So-so automation:** does the idea only move effort (onto the user, a reviewer or a customer) without a real gain?
5. **Expert slowdown:** if the user is already expert at this task, will reviewing tool output cost more than doing it?
6. **Complementary change:** what process, data, training or structure must change before the gain appears?
7. **Metric:** one number to compare before and after (time, error rate, quality score). Feelings of speed are unreliable.

Skip checks that clearly do not apply. Do not pad.

## Step 4: Output

Keep it short. Use this shape:

```
**Idea:** <one sentence>

| Task | Automate / Augment / Manual | Human role | Main risk |
|---|---|---|---|
| ... | ... | ... | ... |

**Verdict:** <one line: e.g. "Good idea; automate the sync, augment the review, keep the final call manual.">
**Better shape:** <2–4 bullets: how to change the idea>
**Watch out for:** <the 1–2 checks from Step 3 that matter most>
**First step:** <one concrete action>
**Metric:** <what to measure>
```

## Rules

- Follow the user's CLAUDE.md communication rules (Simplified Technical English prose, bracket-explain every technical term).
- Give a recommendation, not a neutral survey. Disagree when the evidence says so.
- Do not run the lens on trivial changes (typo, rename, one-line fix).
- This is a review step. Do not start building the idea unless the user asks.
