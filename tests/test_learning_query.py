"""`query` learns from work memory: lessons lift proven nodes, saved answers are recalled."""
from __future__ import annotations

import networkx as nx

from pilothify.ingest import save_query_result
from pilothify.serve import _apply_learning_boost, _query_graph_text, _recall_saved_answer

QUESTION = "How do docs that name an endpoint link to the Spring handler?"


def _graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("alpha", label="alpha_handler()", source_file="a.py", source_location="L1", community=0)
    G.add_node("beta", label="beta_handler()", source_file="b.py", source_location="L1", community=0)
    G.add_node("links", label="link_routes()", source_file="route_links.py", source_location="L52", community=1)
    G.add_node("build", label="build_from_json()", source_file="build.py", source_location="L9", community=1)
    G.add_node("spring", label="SpringEndpoint", source_file="docs/api.md", source_location="L3", community=2)
    G.add_edge("links", "build", relation="calls")
    G.add_edge("alpha", "beta", relation="calls")
    return G


def _start(text: str) -> str:
    return text.split("Start: ", 1)[1].split(" | ", 1)[0]


def _graph_path(tmp_path):
    out = tmp_path / "pilothify-out"
    out.mkdir()
    return out / "graph.json"


def _save(gp, question=QUESTION, outcome="useful", nodes=("link_routes()", "build_from_json()")):
    save_query_result(question=question, answer="link_routes() adds the edges",
                      memory_dir=gp.parent / "memory", source_nodes=list(nodes), outcome=outcome)


def test_a_preferred_lesson_lifts_a_slightly_weaker_match():
    G = _graph()
    ranked = [(1.0, "alpha"), (0.9, "beta")]
    boosted = _apply_learning_boost(G, ranked, {"beta": {"status": "preferred", "stale": False}})
    assert [nid for _, nid in boosted] == ["beta", "alpha"]


def test_a_stale_lesson_gives_no_lift():
    G = _graph()
    ranked = [(1.0, "alpha"), (0.9, "beta")]
    boosted = _apply_learning_boost(G, ranked, {"beta": {"status": "preferred", "stale": True}})
    assert [nid for _, nid in boosted] == ["alpha", "beta"]


def test_a_lesson_never_adds_a_node_the_question_did_not_match():
    G = _graph()
    boosted = _apply_learning_boost(G, [(1.0, "alpha")], {"links": {"status": "preferred"}})
    assert [nid for _, nid in boosted] == ["alpha"]


def test_a_similar_question_starts_from_the_saved_answer(tmp_path):
    gp = _graph_path(tmp_path)
    _save(gp)
    G = _graph()
    out = _query_graph_text(G, "how are docs naming an endpoint linked to a Spring handler",
                            graph_path=str(gp))
    assert f'Recalled from a saved answer to: "{QUESTION}"' in out
    assert _start(out).startswith("['link_routes()', 'build_from_json()'")


def test_an_answer_later_marked_dead_end_is_not_recalled(tmp_path):
    gp = _graph_path(tmp_path)
    _save(gp)
    _save(gp, outcome="dead_end")
    assert _recall_saved_answer(_graph(), "how do docs name an endpoint for a Spring handler",
                                str(gp)) == ([], "")


def test_an_unrelated_question_recalls_nothing(tmp_path):
    gp = _graph_path(tmp_path)
    _save(gp)
    assert _recall_saved_answer(_graph(), "how is the alpha handler called", str(gp)) == ([], "")


def test_a_cited_name_matching_two_nodes_is_skipped(tmp_path):
    gp = _graph_path(tmp_path)
    _save(gp, nodes=("dup()", "link_routes()"))
    G = _graph()
    G.add_node("d1", label="dup()", source_file="x.py")
    G.add_node("d2", label="dup()", source_file="y.py")
    nodes, _ = _recall_saved_answer(G, QUESTION, str(gp))
    assert nodes == ["links"]


def test_without_memory_or_lessons_the_answer_is_unchanged(tmp_path):
    gp = _graph_path(tmp_path)
    question = "how are docs naming an endpoint linked to a Spring handler"
    plain = _query_graph_text(_graph(), question)
    assert _query_graph_text(_graph(), question, graph_path=str(gp)).split("\n", 1)[1] == plain.split("\n", 1)[1]
