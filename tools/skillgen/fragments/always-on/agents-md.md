## pilothify

This project has a knowledge graph at pilothify-out/.

When the user types `/pilothify`, use the installed pilothify skill or instructions first.

Rules:
- When pilothify-out/graph.json exists, run `pilothify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `pilothify path "<A>" "<B>"` for relationships and `pilothify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or grep output.
- Dirty pilothify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip pilothify. Only skip pilothify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If pilothify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read pilothify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `pilothify update .` to keep the graph current (AST-only, no API cost).
- A committed pilothify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
