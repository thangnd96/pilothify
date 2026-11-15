"""God nodes rank the code a reader needs, not the scaffolding around it.

On a real corpus the top of the ranking was a test base class, a test render
helper and a package pinned in a workspace manifest. Nodes from test code and
config/data files are now left out unless asked for.
"""
from __future__ import annotations

import networkx as nx

from pilothify.analyze import god_nodes


def _star(G: nx.Graph, hub: str, source_file: str, leaves: int) -> None:
    G.add_node(hub, label=hub, source_file=source_file, file_type="code")
    for i in range(leaves):
        leaf = f"{hub}_caller_{i}"
        G.add_node(leaf, label=leaf, source_file=f"src/feature_{i}.ts", file_type="code")
        G.add_edge(leaf, hub, relation="calls")


def _graph() -> nx.Graph:
    G = nx.Graph()
    _star(G, "GameIntegrationTest", "pen-api/src/test/java/world/GameIntegrationTest.java", 9)
    _star(G, "renderRoute()", "FE/platform/shell/src/testing.tsx", 8)
    _star(G, "@playwright/test", "FE/pnpm-workspace.yaml", 7)
    _star(G, "SpinService", "pen-api/src/main/java/world/SpinService.java", 5)
    return G


def test_test_and_config_hubs_do_not_outrank_production_code():
    assert [g["label"] for g in god_nodes(_graph(), top_n=1)] == ["SpinService"]


def test_they_still_rank_on_request():
    gods = god_nodes(_graph(), top_n=3, include_tests_and_config=True)
    assert [g["label"] for g in gods] == ["GameIntegrationTest", "renderRoute()", "@playwright/test"]


def test_a_test_only_corpus_still_has_god_nodes():
    G = nx.Graph()
    _star(G, "Harness", "tests/harness.py", 4)
    for node, data in G.nodes(data=True):
        data["source_file"] = "tests/" + data["source_file"].split("/")[-1]
    assert god_nodes(G, top_n=1)[0]["label"] == "Harness"
