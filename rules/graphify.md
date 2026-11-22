# graphify
A project may have a knowledge graph at graphify-out/ (god nodes, communities, cross-file relationships). `/graphify` builds one; follow the installed skill (`~/.claude/skills/graphify/SKILL.md`).
- If graphify-out/graph.json exists, answer codebase questions with `graphify query "<question>"` first. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. They return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
