---
name: explain
description: "Explain a topic, file, function, error or architecture in the clearest format: ASD-STE100-style prose (80% mode by default), a diagram, or an interactive HTML page. Use when the user types /explain, or asks to explain, break down, walk through, or help them understand something and the answer needs more than a few sentences. Add --strict for full STE (runbooks, step-by-step procedures)."
---

# /explain

Explain one thing so the reader understands it fast. Pick the format that fits the content, not the longest one.

## Usage

```
/explain <topic | file | symbol | error>          # auto-pick format, 80% STE prose
/explain <target> --diagram                       # force a diagram
/explain <target> --html                          # force an interactive HTML page
/explain <target> --strict                        # full ASD-STE100 prose
```

## Step 1: Gather evidence

- If the target is in the codebase, read the real code first. If `graphify-out/graph.json` exists, start with `graphify explain "<target>"` or `graphify query`.
- If the target is a general concept, answer from knowledge. Search the web only if facts may be recent or uncertain.
- Never explain code you have not read. Mark guesses as guesses.

## Step 2: Choose the format

| Content shape | Format |
|---|---|
| A concept, a decision, a "why" | 80% STE prose |
| A flow, pipeline, call chain, state machine, architecture, dependencies | Diagram + short STE caption |
| Numbers, compounding, trade-offs, parameters to adjust, side-by-side options | Interactive HTML page (sliders, tables, toggles) |
| A procedure the reader will follow step by step | `--strict` STE numbered steps |

A flag from the user overrides this table. When two formats fit, use prose plus one diagram. Do not produce all formats.

For diagrams: use the session's diagram/visual tool if one exists; otherwise a Mermaid block. For HTML: publish as an artifact if the session supports it; otherwise write one self-contained `.html` file.

## Step 3: Write in STE

### 80% mode (default)

Follow the spirit of ASD-STE100, not every rule:

- Sentences: up to ~20 words for instructions, ~25 for descriptions.
- One idea per sentence. Active voice. Present tense where possible.
- Paragraphs: at most ~6 sentences. Use lists for parallel items.
- Common words with one clear meaning. Prefer "use" over "utilize", "start" over "initiate", "show" over "demonstrate".
- No noun stacks longer than 3 words. Write "the cache for session tokens", not "session token cache invalidation logic".
- Lead with the answer, then the detail.
- Keep a natural tone. Short connecting words ("so", "but", "because") are fine.

### Strict mode (`--strict`)

All of the above, plus:

- Instructions: max 20 words, imperative verb first ("Run", "Open", "Set").
- One instruction per step. Put warnings and conditions before the step they apply to.
- Use each word with one meaning only. Do not use synonyms for the same thing.
- No "-ing" forms as nouns or adjectives where a simple verb works.

### Never simplify these

Code, identifiers, file paths, commands, config keys, error messages, version numbers and technical terms stay exact. STE rules apply only to the prose around them. Do not drop a fact to make a sentence shorter. Split the sentence instead.

## Step 4: Check before sending

- Every claim comes from the code you read or from known facts.
- The first sentence answers the question.
- No sentence over ~25 words (20 in strict mode).
- No filler: "It's worth noting", "In essence", "Let's dive in", "Great question".
- Nothing important was lost to shortening.

## Output shape

1. One-line answer.
2. The body, in the chosen format.
3. Optional: "Where to look next", with 1–3 file links or concepts.
