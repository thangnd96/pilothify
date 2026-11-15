"""Retrieval check for `query` on this repo's own code graph.

Usage:
  PILOTHIFY_BACKEND=none pilothify extract . --code-only
  python -m tools.query_eval [pilothify-out/graph.json]

Thirty plain-language questions about pilothify, each with the function that
answers it. Reports, per question, whether the answer seeds the traversal and
where it ranks among the NODE lines, plus totals. Run it before and after a
change to the query scorer; a change that lowers the totals needs a reason.
"""
from __future__ import annotations

import json
import re
import sys

from pilothify.serve import _load_graph, _query_graph_text

CASES = [
    ("how do docs that mention an endpoint get linked to the handler serving it", "link_routes()"),
    ("where are identifier keys shared across documents linked together", "link_shared_keys()"),
    ("how is the query answer cut to fit the token budget", "_subgraph_to_text()"),
    ("how are the start nodes of a query chosen", "_pick_seeds()"),
    ("what does the PreToolUse hook do before a grep or read", "_run_hook_guard()"),
    ("how is a saved answer recalled for a similar question", "_recall_saved_answer()"),
    ("how are lessons aggregated from saved memory outcomes", "aggregate_lessons()"),
    ("how is the route of a spring request mapping computed", "_java_spring_route()"),
    ("how do express router registrations become route nodes", "_js_server_routes()"),
    ("which asset folders are left out of the vision pass", "asset_media_folder()"),
    ("how are python files extracted with tree-sitter", "extract_python()"),
    ("how does save-result write a question and answer to memory", "save_query_result()"),
    ("how are vietnamese questions scored", "_score_vietnamese_query()"),
    ("how is the pilothify section written into CLAUDE.md", "claude_install()"),
    ("how are C++ member declarations merged with their definitions", "_merge_cpp_member_declarations()"),
    ("how is the learning sidecar loaded and marked stale", "load_learning_overlay()"),
    ("how is a route string split into verb and path", "_parse_route()"),
    ("how is the semantic extraction cache saved", "save_semantic_cache()"),
    ("how does the code graph rebuild after a commit", "_rebuild_code()"),
    ("how are communities detected in the graph", "cluster()"),
    ("how is the interactive html graph written", "to_html()"),
    ("how does the plugin bundle check find stale files", "stale()"),
    ("how does the adherence tool classify a tool call", "classify()"),
    ("how is an identifier key like BUG-ADM-15-01 parsed from a label", "identifier_key()"),
    ("how do lessons lift the ranking of proven nodes", "_apply_learning_boost()"),
    ("how many times does the hook nudge an agent per session", "_nudge_allowed()"),
    ("how are FastAPI and Flask decorator routes read", "_python_routes()"),
    ("how are NestJS controller routes read", "_nest_routes()"),
    ("how does detect classify the files in a folder", "detect()"),
    ("how is the graph built from extraction json", "build_from_json()"),
]

NODE = re.compile(r"^NODE (.+?) \[src=")


def run(graph_path: str) -> dict:
    G = _load_graph(graph_path)
    G.graph["_learning_overlay"] = {}
    rows = []
    for question, want in CASES:
        out = _query_graph_text(G, question, depth=2, token_budget=2000)
        start = out.split("Start: ", 1)[1].split(" | ", 1)[0] if "Start: " in out else ""
        labels = [m.group(1) for line in out.splitlines() if (m := NODE.match(line))]
        rank = labels.index(want) + 1 if want in labels else None
        rows.append({"q": question, "want": want, "seed": f"'{want}'" in start, "rank": rank,
                     "seeds": start})
    n = len(rows)
    summary = {
        "seed": sum(r["seed"] for r in rows),
        "top5": sum(1 for r in rows if r["rank"] and r["rank"] <= 5),
        "found": sum(1 for r in rows if r["rank"]),
        "mrr": round(sum(1 / r["rank"] for r in rows if r["rank"]) / n, 3),
        "n": n,
    }
    return {"summary": summary, "rows": rows}


if __name__ == "__main__":
    res = run(sys.argv[1] if len(sys.argv) > 1 else "pilothify-out/graph.json")
    for r in res["rows"]:
        mark = "S" if r["seed"] else " "
        print(f"{mark} rank={str(r['rank']):>4}  {r['want']:34} {r['seeds'][:110]}")
    print(json.dumps(res["summary"]))
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)
