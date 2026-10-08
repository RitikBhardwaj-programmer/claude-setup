# Model data for routing cards

Source: [Artificial Analysis](https://artificialanalysis.ai/) model pages (`/models/<slug>`), fetched **2026-10-08**. Each page shows its own effort variant. Numbers are API prices; on a subscription plan they map roughly to how fast the usage limit is used up.

| Model (variant on the page) | Intelligence Index (rank) | Cost per index task | Price per 1M tokens in / out |
|---|---|---|---|
| Claude Opus 5.5 | 58 (#1 of 225) | $5.98 | $4 / $20 |
| Claude Sonnet 5.5 (max) | 56 (#2 of 225) | $5.46 | $2 / $10 |
| Claude Fable 5.1 (max) | 53 (#5 of 225) | $7.63 | $10 / $50 |
| Claude Haiku 5.5 (high) | 38 | $0.08 | $0.10 / $0.50 |

What this means for routing (inference from the table):
- **Opus and Sonnet are close in score and in cost per task.** Opus uses fewer tokens per task, so its higher token price does not show up in full. Use Opus where a quiet failure is expensive. Use Sonnet for building from a clear plan.
- **Fable 5.1 is dominated:** it scores lower than Opus and Sonnet and costs more per task. Do not choose it unless a newer measurement says otherwise.
- **Haiku costs ~70× less per task than Sonnet** but scores much lower. Use it for search, reading and mechanical work, where its output is easy to check.
- The Coding Agent Index was not shown on these pages. For coding-heavy choices, check `artificialanalysis.ai` for that index.

## Refresh rule
Refresh this file when it is older than 60 days, or when a new Claude model appears. Fetch `https://artificialanalysis.ai/models/<slug>` (for example `claude-opus-5-5`, `claude-haiku-5-5-high`) and update the table and the date.
