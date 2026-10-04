---
name: llm-council
description: "Pressure-test a decision, idea, or plan by running it past a council of 5 sub-agent advisors who each think from a different angle, review each other anonymously, and hand the results to a chairman who gives one clear verdict. Use this whenever the user says 'council this', 'run the council', 'war room this', 'pressure-test this', 'stress-test this', or 'debate this', and also when they bring a real decision with stakes and several options ('should I X or Y', 'I'm torn between', 'is this the right move', 'validate my idea', 'is this a viable startup', 'get multiple perspectives'), even if they never say the word council. Skip it for factual lookups, simple yes/no questions, writing or summarizing tasks, and casual 'should I' questions with no real trade-off."
---

# LLM Council

One AI gives one answer, and you can't tell whether that answer is sharp or lazy. The council makes the answer earn its place: five advisors with deliberately different angles answer independently, then each reviews the others without knowing who wrote what, and a chairman reads everything and commits to a recommendation. The value comes from the disagreements, so don't smooth them out anywhere in the process.

Method credit: Andrej Karpathy's "LLM Council" idea, with the five-advisor structure adapted from Ole Lehmann's skill (github.com/aiwithremy/claude-skills-llm-council). This version is a rewrite for Claude Code.

## When it's worth running

Use it when being wrong is expensive and the answer genuinely isn't obvious: pricing, positioning, pivots, hiring, build-vs-buy, "is this idea worth pursuing". A full run is 11 sub-agent calls, so don't spend that on questions with one right answer. If the user already knows what they want and only wants agreement, say so briefly, because the council will probably push back.

## The five advisors

They are thinking styles, not job titles, chosen so they pull against each other.

1. **The Contrarian** assumes the idea has a fatal flaw and hunts for it. Not a pessimist; the friend who asks the question you're avoiding.
2. **The First Principles Thinker** ignores the question as asked and works out what problem is really being solved. Sometimes the best output is "you're asking the wrong question".
3. **The Expansionist** looks for upside nobody else is pricing in: a bigger market, an adjacent opportunity, something undervalued. Ignores risk on purpose.
4. **The Outsider** knows nothing about the user, the field, or the history. Catches things that are obvious to insiders and confusing to everyone else.
5. **The Executor** cares only whether it can be done and what happens on Monday morning. Calls out any idea with no clear first step.

Tensions built in: Contrarian vs Expansionist (downside vs upside), First Principles vs Executor (rethink vs do), with the Outsider keeping everyone honest.

## Running a session

### 1. Frame the question

First gather context, briefly. Read the project's `CLAUDE.md` / `README.md`, any memory notes, and any file the user named; the goal is the two or three facts that make advice specific instead of generic. Do not go hunting for long.

Then write one neutral framed question containing: the decision, the key facts (from the user and from files), and what is at stake. Two rules keep the council honest:

- **Separate what is known from what is assumed.** For a startup or product question, state plainly what exists today (built, running, used by real people, earning money) and what has never been tested. Never present hopes as evidence.
- **Don't steer.** Leave out your own opinion and the answer the user seems to want.

If the question is too vague to frame ("council this: my business"), ask one clarifying question, then continue. Keep the framed question for the transcript.

### 2. Convene the advisors (5 sub-agents, one message)

Launch all five with the Agent tool in a single message so they run in parallel and can't see each other. Sequential runs let early answers bleed into later ones.

Each advisor gets its style, the framed question, and these ground rules. The Outsider gets a stripped version of the framed question: a plain description of what the thing is and who it is for, with no internal jargon and no workspace details, because it can only play a stranger if it is treated like one.

```
You are [Advisor Name] on an LLM Council.

Your thinking style: [description from above]

A user has brought this to the council:
---
[framed question]
---

Respond from your angle only; the other advisors cover the rest. Be direct and specific, lean fully into your style, and don't try to be balanced. You have no internet access, so anything you say about markets, competitors, prices, or user behavior is an assumption: label it as one, and never invent statistics or sources. 150-300 words, no preamble.
```

### 3. Anonymous peer review (5 sub-agents, one message)

Collect the five responses and label them Response A to E using a genuinely random assignment, so position can't hint at the author. Keep the mapping to yourself.

Launch five new sub-agents (one per advisor style is fine, or five neutral reviewers). Each sees the framed question and all five anonymized responses and answers: (1) which response is strongest and why, (2) which has the biggest blind spot, (3) what did all five miss? Reference responses by letter, under 200 words.

### 4. Chairman

Launch one more sub-agent with everything: the framed question, the five responses now labelled by advisor, and the five reviews. It writes the verdict with the structure below, states a real recommendation (never "it depends"), and may side with a lone dissenter when that advisor's reasoning is strongest. It should also call out any advisor claim that rested on an unverified assumption, so the user knows which parts need real evidence.

### 5. Present in chat

Show the verdict directly in the conversation. Do not create an HTML report or other files.

```
## Council Verdict: {short topic}
### Where the Council Agrees
### Where the Council Clashes
### Blind Spots the Council Caught
### The Recommendation
### The One Thing to Do First
```

Keep it scannable: short bullets, a single next step (not ten). Follow it with one line saying which conclusions are assumptions the user should verify before acting.

### 6. Transcript (only if asked)

Save the framed question, advisor responses, reviews, and verdict to a markdown file only when the user asks, or when the decision is big enough to revisit later.
