"""Nodes in different files that open with the same identifier key are linked."""
import networkx as nx
import pytest

from pilothify.build import build_from_json
from pilothify.key_links import SAME_KEY_RELATION, identifier_key, link_shared_keys


@pytest.mark.parametrize("label, key", [
    ("BUG-ADM-15-01: bật lại cờ", "BUG-ADM-15-01"),
    ("ADM-15-TC16 ca test", "ADM-15-TC16"),
    ("D-20 · Chốt kỹ thuật", "D-20"),
    ("**GR-06**: không lộ số liệu", "GR-06"),
    ("R-46a vai trước đầu vào", "R-46a"),
    ("ADM-ADR-0008: Frontend penctrl", "ADM-ADR-0008"),
])
def test_identifier_key_reads_the_key_a_label_opens_with(label, key):
    assert identifier_key(label) == key


@pytest.mark.parametrize("label", [
    "Q5: duyệt ống chống spam",   # local numbering, collides across documents
    "G2 việc của Đội Game",
    "pen-api backend",            # lowercase name, not a key
    "X-API-Key header",           # no digit
    "Ca test ADM-15",             # key not at the start
    "ADM-15_draft",               # the key runs on into an identifier
    None,
])
def test_identifier_key_ignores_labels_without_a_leading_key(label):
    assert identifier_key(label) is None


def _doc(nid, label, source_file, file_type="document"):
    return {"id": nid, "label": label, "file_type": file_type, "source_file": source_file}


def test_same_key_in_two_files_is_linked_to_the_better_connected_node():
    G = nx.Graph()
    G.add_node("report_bug", **_doc("report_bug", "BUG-ADM-15-01: bật lại cờ", "qe/reports/ADM-15.md"))
    G.add_node("case_bug", **_doc("case_bug", "BUG-ADM-15-01: PUT mang khoá cũ", "qe/cases/ADM-15.md"))
    G.add_node("report", **_doc("report", "Báo cáo QE ADM-15", "qe/reports/ADM-15.md"))
    G.add_edge("report", "report_bug", relation="references")

    assert link_shared_keys(G) == 1
    data = G.edges["case_bug", "report_bug"]
    assert data["relation"] == SAME_KEY_RELATION
    assert (data["_src"], data["_tgt"]) == ("case_bug", "report_bug")
    assert data["confidence"] == "INFERRED" and data["confidence_score"] == 0.85
    assert link_shared_keys(G) == 0  # idempotent


def test_same_key_within_one_file_or_on_code_nodes_is_not_linked():
    G = nx.Graph()
    G.add_node("a", **_doc("a", "D-20: JIT chỉ dưới /ctrl", "decisions.md"))
    G.add_node("b", **_doc("b", "D-20 · Chốt kỹ thuật", "decisions.md"))
    G.add_node("c", **_doc("c", "D-20", "src/Decisions.java", file_type="code"))
    assert link_shared_keys(G) == 0


def test_build_from_json_links_shared_keys():
    G = build_from_json({
        "nodes": [
            _doc("docs_a_d20", "D-20 · Chốt kỹ thuật", "docs/a.md"),
            _doc("docs_b_d20", "D-20: JIT chỉ dưới /ctrl", "docs/b.md"),
        ],
        "edges": [],
    })
    assert G.edges["docs_a_d20", "docs_b_d20"]["relation"] == SAME_KEY_RELATION


def test_a_bare_key_resolves_to_the_node_its_matches_are_linked_to():
    from pilothify.serve import _resolve_single_node

    G = build_from_json({
        "nodes": [
            _doc("report_bug", "BUG-ADM-15-01: bật lại cờ", "qe/reports/ADM-15.md"),
            _doc("case_bug", "BUG-ADM-15-01: PUT mang khoá cũ", "qe/cases/ADM-15.md"),
            _doc("report", "Báo cáo QE ADM-15", "qe/reports/ADM-15.md"),
        ],
        "edges": [{"source": "report", "target": "report_bug", "relation": "references",
                   "confidence": "EXTRACTED", "source_file": "qe/reports/ADM-15.md"}],
    })
    assert _resolve_single_node(G, "BUG-ADM-15-01") == ("report_bug", None)


def test_a_bare_key_shared_by_unlinked_nodes_stays_ambiguous():
    from pilothify.serve import _resolve_single_node

    G = nx.Graph()
    G.add_node("a", **_doc("a", "ADM-15: màn cờ", "a.md"))
    G.add_node("b", **_doc("b", "ADM-15 · thẻ việc", "b.md"))
    nid, refusal = _resolve_single_node(G, "ADM-15")
    assert nid is None and refusal.startswith("Ambiguous")
