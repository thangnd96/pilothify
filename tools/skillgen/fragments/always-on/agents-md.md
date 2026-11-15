## pilothify

This project has a knowledge graph at pilothify-out/.

When the user types `/pilothify`, use the installed pilothify skill or instructions first.

Rules:
- When pilothify-out/graph.json exists, run `pilothify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `pilothify path "<A>" "<B>"` for relationships and `pilothify explain "<concept>"` for focused concepts.
- After a query helps or misleads, run `pilothify save-result --question "<q>" --answer "<gist>" --nodes <labels> --outcome useful|dead_end`; later queries start there.
- Dirty pilothify-out/ files are expected after hooks or incremental updates; dirty graph files are no reason to skip pilothify. Only skip pilothify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If pilothify-out/wiki/index.md exists, browse it instead of raw source.
- Read pilothify-out/GRAPH_REPORT.md only for architecture review or when query/path/explain fall short.
- After modifying code, run `pilothify update .` to keep the graph current (AST-only, free).
- A committed pilothify-out/graph.json is rewritten whole on every build; a large diff to it is expected, not churn to flag.
