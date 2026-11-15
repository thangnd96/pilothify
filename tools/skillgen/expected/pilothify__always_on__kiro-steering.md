---
inclusion: always
---

This project's knowledge graph lives in `pilothify-out/`. For codebase, architecture, or dependency questions, when `pilothify-out/graph.json` exists, first run `pilothify query "<question>"` (or `pilothify path "<A>" "<B>"` / `pilothify explain "<concept>"`). These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output. Read `GRAPH_REPORT.md` only for broad architecture review or when those commands do not surface enough context.
