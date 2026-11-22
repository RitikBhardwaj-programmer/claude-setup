# Model data for routing cards

Source: [Artificial Analysis](https://artificialanalysis.ai/) model pages (`/models/<slug>`) and the [Intelligence Index v5 article](https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v5) (published 2026-10-27), fetched **2026-10-30**. Each page shows its own effort variant. Numbers are API prices; on a subscription plan (Pro, Max) they map roughly to how fast the 5-hour and weekly usage limits are used up.

v5 is not comparable with the v4 numbers this file had before (2026-10-08): about 60% of v5 is private tests, and the median task uses ~59k output tokens instead of ~35k, so every cost per task went up. Compare models only within one index version.

| Model (variant on the page) | Intelligence Index v5 | Cost per index task | Price per 1M tokens in / out | Cache hit |
|---|---|---|---|---|
| Claude Fable 5.2 (max) | 65 (#1 of 74, v5.0.1, fetched 2026-11-10) | $26.54 | $8 / $40 | 0.025× input ($0.20) |
| Claude Fable 5.2 (high) | 62 (v5.0.1, from a search summary of the AA `claude-fable-5-2-high` page, 2026-11-10) | $9.08 | $8 / $40 | 0.025× input |
| Claude Fable 5.2 (medium) | 56 (secondary blog only, not confirmed on AA) | $3.80 | $8 / $40 | 0.025× input |
| Claude Opus 5.5 (max) | 58 (#2 of 57) | $10.04 | $4 / $20 | 0.05× input |
| Claude Sonnet 5.5 (max) | 54 (#8 of 57); 55 (#13 of 74) on v5.0.1, fetched 2026-11-10 | $10.02 | $2 / $10 | 0.05× input |
| Claude Fable 5.1 (max) | 49 (#17 of 57) | $12.99 | $10 / $50 | 0.025× input |
| Claude Haiku 5.5 (max) | 36 | $0.41 | $0.10 / $0.50 (prompt ≤100K); $0.50 / $2.50 (prompt >100K) | 0.1× input |
| Claude Opus 5.5 (low) | 35 | $0.98 | $4 / $20 | 0.05× input |

Other coding data (2026-10):
- AA Coding Agent Index (scores model and tool together): Claude Code + Opus 5.5 (max) = 62, the top score ([AA on X](https://x.com/ArtificialAnlys/status/2115494553780367384)).
- FrontierCode 2.0 (AA, private coding tasks): Opus 5.5 46%, Sonnet 5.5 42%.
- Terminal-Bench 4.0 (vendor-reported, Anthropic launch posts): Sonnet 5.5 70.6%, Opus 5.5 66.4%, Fable 5.1 55.8%, Haiku 5.5 39.2%.
- Prices, cache multipliers and the Haiku 100K step: [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing).

What this means for routing (inference from the table):
- **At max effort, Sonnet is dominated by Opus:** the same cost per task ($10.02 vs $10.04) for 4 fewer points. Opus uses fewer tokens per task, so its 2× token price does not show. Do not run Sonnet at max; use Opus instead. Sonnet's value is at medium or high effort on a clear plan, and on terminal-heavy work (Terminal-Bench 4.0).
- **Effort moves cost more than the model does:** Opus 5.5 costs $10.04 per task at max and $0.98 at low. Pick the effort with as much care as the model.
- **Opus at low effort is dominated by Haiku at max:** 35 vs 36 points, $0.98 vs $0.41. For cheap work, use Haiku, not a strong model at low effort.
- **Fable 5.1 is dominated:** it scores lower than Opus and Sonnet and costs more per task. Use Fable 5.2 instead.
- **Fable 5.2 at high effort dominates Opus and Sonnet at max:** 62 points for $9.08, against 58 for $10.04 and 54–55 for $10.02. Use it for quiet-failure work (design, crypto, recovery logic, review). Fable 5.2 at max costs about 3× more ($26.54) for 3 more points, so keep max for rare cases.
- **Rows fetched on different dates use different index builds** (v5 with 57 models on 2026-10-30, v5.0.1 with 74 models on 2026-11-10). Opus, Haiku and Fable 5.1 were not re-fetched on 2026-11-10. Sonnet 5.5 at medium effort has no measurement.
- **Haiku costs ~25× less per task than Sonnet** ($0.41 vs $10.02) but scores much lower. Use it for search, reading and mechanical work, where its output is easy to check. Its price goes up 5× when a prompt passes 100K tokens.
- **The tokenizer of Claude 4.7 and later makes ~30% more tokens for the same text.** This affects all current models the same way, so it does not change the choice between them. It only matters when you compare with older models.

## Refresh rule
Refresh this file when it is older than 60 days, when a new Claude model appears, or when Artificial Analysis releases a new index version. Fetch `https://artificialanalysis.ai/models/<slug>` (for example `claude-fable-5-2`, `claude-fable-5-2-high`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`) and the latest index article, and update the table and the date.
