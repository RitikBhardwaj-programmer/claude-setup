---
name: ambition
description: "Rewrite a task prompt so it aims higher in the right way: higher outcome (altitude), closer to raw data and expert method (depth), and borrowing from other fields (range). Based on Felix Rieseberg's 'How to be more ambitious' tutorial. Use on /ambition, or when the user says 'make this more ambitious', 'go deeper', 'am I thinking too small', 'what would an expert do here'. Output is a rewritten prompt plus a short list of what changed. Skip for typos, lookups, bug fixes with a clear cause, trivial edits, and when the user says 'just do it'."
---

# Ambition

Models can often do more than people ask. A vague, small prompt gets a vague, small answer. This skill rewrites a prompt so it asks for a better answer. It does not make the task bigger. **Rule: deeper, not bigger.** Do not add features, files or scope the user did not want.

Source: felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models (speed is skipped there; three kinds of ambition remain).

## Step 1: Altitude (aim at the outcome)

Write three lines:
- **Task:** what the user asked for.
- **Outcome:** what they want to be true afterwards.
- **Next:** what they will do with the result, and whether a repeatable process could replace this one-off task.

Offer one higher framing, for example: "summarize what changed" becomes "tell me what changed, why, and which three decisions are most urgent". Keep the original task as the first deliverable.

## Step 2: Depth (work like a top expert)

Answer these for the task, then rewrite the prompt with the answers:
1. What would a top professional do that the user has not asked for?
2. What is the rawest source material they would start from (database rows, logs, the source file, not a summary)?
3. Which methods and tools would they use (SQL, a statistical test, a simulation, a profiler) instead of a table in markdown?
4. How can the result be verified **without trusting the model or the user** (a test, a recomputation from raw data, an outside check)?
5. Which assumption in the prompt should be tested against the raw data instead of accepted? Turn it into: "Try to reproduce that from the data."

Pick demanding, specific goals, and say them plainly as reasonable.

## Step 3: Range (borrow from other fields)

- Replace nouns with verbs. "Churn report" becomes "find why people leave and predict who will". The verbs show which fields help (epidemiology, survival analysis, support triage).
- Name 2-3 relevant experts, plus one adversary (a red team or skeptic) who tries to break the result.
- Ask each expert to **do** their job (run the test, write the counter-argument). Do not ask them to role-play how an expert writes.

## Step 4: Output

Give exactly this:
1. **Rewritten prompt:** ready to run, in the user's voice, with raw sources, methods and the verification step named.
2. **What changed and why:** three lines, one per kind of ambition that you used.
3. **Assumptions:** one line each. Mark anything that costs money, is destructive, or widens scope as "needs your OK".

Then ask whether to run it. Do not run the rewritten prompt without a yes when it widens scope.

## Proportion (added after the A/B test)

In a blind test, skill-rewritten prompts gave better verification and more insight, but 2-3 times longer answers, more scope creep, and lower usefulness on advice and planning tasks. So:
- Keep the original deliverable and its format. Add at most two things: one verification step and one insight.
- Use personas (Step 3) only for decisions, risk reviews and security or code review. For plans, study guides and summaries, skip them.
- Keep the rewritten prompt under about 120 words. Do not add new tools, setups or deliverables the user did not ask for.
- Depth pays most when raw data or code exists to check (analysis, review). It pays least for open-ended planning.

## Limits

- If the task is small and clear, say so and return the original prompt. Not every task needs more ambition.
- Do not invent data sources. If the raw source is unknown, make "find the raw source" the first step.
- Do not add verification that needs tools the project does not have.
