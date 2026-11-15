---
trigger: always_on
description: Consult the knowledge graph at pilothify-out/ for codebase questions.
---

## pilothify

This project has a knowledge graph at pilothify-out/.

Rules:
- For codebase or architecture questions, when `pilothify-out/graph.json` exists, first run `pilothify query "<question>"` (CLI) or `query_graph` (MCP). Use `pilothify path "<A>" "<B>"` / `shortest_path` for relationships and `pilothify explain "<concept>"` / `get_node` for focused concepts. These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output.
- If pilothify-out/wiki/index.md exists, navigate it instead of reading raw files
- Read pilothify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context
- After modifying code, run `pilothify update .` to keep the graph current (AST-only, no API cost)
