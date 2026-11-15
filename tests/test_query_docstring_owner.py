"""A docstring that matches the question seeds the code it documents."""
from __future__ import annotations

import networkx as nx

from pilothify.serve import _query_graph_text


def _graph(directed: bool) -> nx.Graph:
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_node("f", label="_apply_boost()", file_type="code", source_file="serve.py", source_location="L10")
    G.add_node("r", label="Lift matched nodes that earlier answers proved useful.", file_type="rationale",
               source_file="serve.py", source_location="L11")
    G.add_node("other", label="lift_tables()", file_type="code", source_file="db.py", source_location="L1")
    G.add_edge("r", "f", relation="rationale_for")
    return G


def _start(out: str) -> str:
    return out.split("Start: ", 1)[1].split(" | ", 1)[0]


def test_the_documented_function_seeds_instead_of_its_docstring():
    for directed in (False, True):
        out = _query_graph_text(_graph(directed), "how do earlier answers lift matched nodes")
        assert _start(out).startswith("['_apply_boost()'"), out
        assert "Lift matched nodes" not in _start(out)


def test_a_docstring_without_an_owner_still_seeds():
    G = _graph(False)
    G.remove_edge("r", "f")
    out = _query_graph_text(G, "how do earlier answers lift matched nodes")
    assert "Lift matched nodes" in _start(out)


def test_a_multigraph_with_parallel_edges_still_seeds_the_owner():
    G = nx.MultiDiGraph(_graph(True))
    G.add_edge("r", "f", relation="rationale_for")  # a parallel edge
    out = _query_graph_text(G, "how do earlier answers lift matched nodes")
    assert _start(out).startswith("['_apply_boost()'"), out


def test_a_long_docstring_is_searchable_beyond_its_label(tmp_path):
    from pathlib import Path

    from pilothify.extract import extract
    from pilothify.build import build_from_json

    src = tmp_path / "mod.py"
    src.write_text(
        'def handler():\n'
        '    """Short first sentence that the label keeps for display in the graph.\n\n'
        '    Later on it ranks saved lessons by usefulness and recency, api_key=AKIAABCDEFGHIJKLMNOP.\n'
        '    """\n'
        '    return 1\n',
        encoding="utf-8",
    )
    result = extract([src], cache_root=tmp_path)
    (doc,) = [n for n in result["nodes"] if n.get("file_type") == "rationale"]
    assert doc["label"].endswith("…") and "recency" in doc["rationale"]
    assert "AKIAABCDEFGHIJKLMNOP" not in doc["rationale"]  # redacted like the label
    G = build_from_json(result)
    out = _query_graph_text(G, "where are saved lessons ranked by usefulness and recency")
    assert _start(out).startswith("['handler()'"), out
