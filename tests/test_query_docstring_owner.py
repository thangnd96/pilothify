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
