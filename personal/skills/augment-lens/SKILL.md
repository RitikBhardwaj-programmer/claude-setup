---
name: augment-lens
description: "Run this FIRST, before any clarifying questions, plan or code, whenever the user brings an idea or asks to build, automate, add or change something new ('I want to auto-reply to emails', 'I want to build/automate/add X', 'what if we...', 'thinking about...', 'let's add...', 'can we make X do Y on its own'), proposes a change to a project, tool or workflow, or wants to evaluate a plan, even if they never mention automation; also on /augment-lens. 'I want X' is an idea to check, not a decided task. It is a short automation-vs-augmentation pass: which parts to automate, which to keep with a human who decides, the risks (so-so automation, automation bias, deskilling), a verdict and a first step. Skip only for factual lookups, explanations, bug fixes, trivial edits, or when the user says to skip the review ('just build it', 'skip the lens'). For a high-stakes choice between several options, llm-council is the heavier tool; augment-lens can run first as a quick pass."
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

When the user also wants the idea built, put this output first and the build questions after it, in the same message. Answer their choices in the light of the verdict (e.g. recommend "draft for review" when the lens says "augment").

## Rules

- Follow the user's CLAUDE.md communication rules (Simplified Technical English prose, bracket-explain every technical term).
- Give a recommendation, not a neutral survey. Disagree when the evidence says so.
- Do not run the lens on trivial changes (typo, rename, one-line fix).
- This is a review step. Do not start building the idea unless the user asks.
