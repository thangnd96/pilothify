## pilothify

For questions about this repo's architecture, structure, components, or how to add/modify/find
code, first run `pilothify query "<question>"` when `pilothify-out/graph.json`
exists. Use `pilothify path "<A>" "<B>"` for relationships and `pilothify explain "<concept>"`
for focused concepts. These return a scoped subgraph, usually much smaller than the full
report or raw grep output.

Triggers: "how do I…", "where is…", "what does … do", "add/modify a <component>",
"explain the architecture", or anything that depends on how files or classes relate.

If `pilothify-out/wiki/index.md` exists, use it for broad navigation. Read `pilothify-out/GRAPH_REPORT.md`
only for broad architecture review or when query/path/explain do not surface enough context. Only read
source files when (a) modifying/debugging specific code, (b) the graph lacks the detail, or
(c) the graph is missing or stale.

Type `/pilothify` in Copilot Chat to build or update the graph.
