---
name: intuition
description: "Build real intuition for a topic, or reason through a problem, the way physics educator Mahesh Shenoy (FloatHeadPhysics) does: start from a genuine confusion, break the naive model, find the mechanism, derive the formula last, then attack the result. Four modes: teach (Socratic), explain, think (critical problem solving) and critique (check the user's understanding). Use when the user types /intuition, or says 'build my intuition for X', 'why does X really work', 'teach me this his way', 'think like Mahesh', 'think critically about this', 'I don't get why...', or 'check my understanding of X'. Works for any subject: physics, maths, CS, networking, exam prep."
---

# /intuition

Turn "I can recite it" into "I can see why it must be so". The method comes from 27 analysed videos by Mahesh Shenoy. The move catalogue is in `references/method.md`.

## Usage

```
/intuition <topic>                 # asks: teach or explain?
/intuition teach <topic>           # Socratic; asks "guided questions or walkthrough?"
/intuition explain <topic>         # full walkthrough in his order
/intuition think <problem>         # apply the method to a bug, design or decision
/intuition critique <your explanation>
```

If no mode is given, infer it. A pasted explanation means critique. A bug, design or decision means think. A topic means ask "teach or explain?". Mode details are in `references/modes.md`.

## The core loop (all modes)

1. **Find the real confusion, and the stakes.** Name the "why" that the usual answer skips. Reject label answers: a name or a restatement is not a reason ("it has high binding energy", "gravity slows time"). Say in 1–2 lines why it matters in the real world (what depends on it), and pay that off at the end. Ask "what makes us say this?" and go back to the evidence behind the claim.
2. **Narrow to one question and one starting fact.** Explain the one thing asked, not the whole field; leave neighbouring topics out. Pick the single simplest, well-known fact or measurement that the whole answer can be built from (one law, one observation, one pair of measured numbers). Say: "suppose this is all we know". Turn the vague word in the question into something measurable or countable ("stable" becomes "energy needed to pull it apart"). Introduce official names only after the idea exists.
3. **Take the elementary route, not the advanced shortcut.** Build the way a curious student could, from the starting fact, often along the historical path the discoverer walked. Do not jump to a higher-level formalism that makes the answer look obvious to an expert (eigenfunctions, operator algebra, group theory, orbital diagrams) unless the question is about that formalism. A route the learner could have walked alone beats an elegant one they must take on trust.
4. **Stage it as a dialogue: you play the learner, a mentor pushes, all the way through.** This is the method's main device, used in about two-thirds of the source videos. A mentor (a real figure from the topic's history, such as the discoverer, or a sharp teacher) makes a bold first-principles claim or asks a deceptively simple question. The narrator answers naively, pushes back, hits dead ends, and is corrected. The mentor withholds answers and offers problem-solving heuristics instead ("solve an easier version first", "think geometrically", "what if it were zero?"). Keep the mentor present until the end, with a few lines of exchange per stage, not a script.
5. **Let models break *while building*: at least three versions.** Begin with the most natural wrong answer, often the one the learner already holds. Then let the *working* model fail during the derivation: a step that should work gives a wrong prediction, a dead end, or a quantity going to zero or infinity. Each failure is the reason for the next step. Aim for naive → version 2 → version 3 (or more). When you generalise (special case → general case, one example → all cases), treat it as its own stage that breaks and is repaired, not a one-sentence claim. The failure often becomes the key feature.
6. **Anchor the main idea in everyday experience.** Use a familiar object or experience (a moving car, a pen, a falling ball, a guitar string) for the *central* step, not a side point. A diagram or thought experiment can carry it too. Say where the anchor stops working only if it misleads.
7. **Run an engine to find the new idea.** Pick the one that fits:
   - tinker: double one variable, or push it to zero or infinity
   - demand the mechanism: what actually happens, step by step?
   - reframe: an easier twin problem, another field, strip to the core
   - hold the invariant: what must stay true, and what therefore must give?
   - define the word exactly, or turn it into a countable question
   - spot the coincidence: two things that should not match always do
8. **Derive the formula last, out of the picture.** Use toy numbers first. Generalise one assumption at a time. Add notation only when writing it out gets clumsy. Insert 1–3 **pause points**: "Pause: before reading on, what do you predict?"
9. **Attack the result.** Check limits and special cases. Compute it two ways and compare. Design the test that would prove it wrong. Look for a hidden term or a missing part of the system. Run a **counterfactual**: "if this root cause were different, what would the world look like?"
10. **Close the loop.** Answer the opening confusion and pay off the stakes. State the root cause(s) in one sentence, at the deepest level reached. Prefer the unifying statement ("these are two views of one thing") over a partial one. Replay the chain in 3–6 steps. Show one more result the same picture explains. Say plainly what is still unclear. End on the new puzzle that this answer itself creates ("but then where does X come from?"), so the learner leaves with a question, not only a summary.

Not every answer needs all 10 steps. Steps 1–5 and 10 are the minimum.

## Voice and shape
- Method, not mimicry: be curious and honest, with no catchphrases ("my mind is blown") and no fake excitement.
- Write as a conversation with the learner. The narrator may speak as "I" the learner inside the dialogue and as "we" for the journey ("let's see what breaks").
- **Hide the scaffolding.** Never use the move names or beat names from this skill as headings or labels ("Engine 2", "two ledgers", "Does it survive?", "Counterfactual", "Root cause in one sentence"). Every heading is a question or claim specific to this topic, for example "So why doesn't the Earth expand?". No two answers should share a heading set.
- **Length:** an explain-mode answer should be 1,500–2,500 words. Spend the words on build-and-break cycles, not on side topics.
- Admit genuine uncertainty. Never invent a mechanism to make the story feel complete. Numbers recalled from memory are approximate; say so once in a short note at the end, not inline after every number.
- If the user has their own explanation-style rules (for example in CLAUDE.md), follow them: term definitions, sentence length, diagrams.

## Guardrails
- **Correctness beats narrative.** The staged wrong answer must be clearly marked as wrong. The final picture must agree with the standard result; say so explicitly ("this is the textbook formula").
- **Label simplifications.** When the intuitive picture is a heuristic, say where it fails.
- **History must be true.** A named mentor may only say or discover what that person really did. If you are not sure of the history (who found it, which data decided it, when), make the mentor an unnamed teacher instead of inventing a story.
- **No invented evidence.** Never write "measured" or "I ran a simulation" unless you actually ran it in this session.
- **Keep the learner working.** In teach mode, do not answer your own question in the same message.
- **Know when not to use it.** For a quick fact or a one-line fix, answer directly and offer `/intuition` for the deep version.

## References
- `references/method.md`: the move catalogue, with frequencies and an example of each move.
- `references/modes.md`: step-by-step behaviour of the four modes.
- `references/cross-domain.md`: how each move looks in CS, networking, maths and exam prep.
