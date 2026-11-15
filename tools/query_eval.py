"""Retrieval check for `query` on this repo's own code graph.

Usage:
  PILOTHIFY_BACKEND=none pilothify extract . --code-only
  python -m tools.query_eval [pilothify-out/graph.json] [--show]

tools/query_eval_cases.json holds plain-language questions about pilothify,
each with the function that answers it, split into `tune` and `holdout`.
Change the scorer while looking only at `tune`; `holdout` says whether the
change generalises. Reports, per split, how often the answer seeds the
traversal, lands in the first five NODE lines or appears at all, and the mean
reciprocal rank. A change that lowers holdout needs a reason.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pilothify.serve import _load_graph, _query_graph_text

CASES_FILE = Path(__file__).with_name("query_eval_cases.json")
NODE = re.compile(r"^NODE (.+?) \[src=")


def evaluate(G, cases: list[dict], show: bool = False) -> dict:
    seed = top5 = found = 0
    rr = 0.0
    for case in cases:
        out = _query_graph_text(G, case["q"], depth=2, token_budget=2000)
        start = out.split("Start: ", 1)[1].split(" | ", 1)[0] if "Start: " in out else ""
        labels = [m.group(1) for line in out.splitlines() if (m := NODE.match(line))]
        rank = labels.index(case["want"]) + 1 if case["want"] in labels else None
        seed += f"'{case['want']}'" in start
        found += rank is not None
        top5 += bool(rank and rank <= 5)
        rr += 1 / rank if rank else 0.0
        if show and (not rank or rank > 5):
            print(f"  miss {case['want']:34} rank={rank}  {case['q'][:90]}")
    n = len(cases)
    return {"seed": seed, "top5": top5, "found": found, "mrr": round(rr / n, 3) if n else 0.0, "n": n}


def main(argv: list[str]) -> int:
    show = "--show" in argv
    paths = [a for a in argv if not a.startswith("--")]
    G = _load_graph(paths[0] if paths else "pilothify-out/graph.json")
    G.graph["_learning_overlay"] = {}  # measure the scorer, not saved lessons
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    for split in ("tune", "holdout"):
        print(split, json.dumps(evaluate(G, [c for c in cases if c["split"] == split], show)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
