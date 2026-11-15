"""Vietnamese questions against a graph of (mostly English) code identifiers.

The query scorer folds diacritics, so a Vietnamese word became a short ASCII
fragment that prefix-matched unrelated identifiers: "trừ" (subtract) -> "tru"
-> `Truck`, "ví" (wallet) -> "vi" -> `view`. The answer looked confident and
was noise. A Vietnamese word now only counts where the graph holds that word,
diacritics included (e.g. a concept label from the semantic pass over docs).
"""
from __future__ import annotations

import unicodedata

import networkx as nx
import pytest

from pilothify.serve import _QUERY_NO_MATCH, _query_graph_text, _query_terms


def _graph(*extra: tuple[str, str, str]) -> nx.Graph:
    G = nx.Graph()
    nodes = [
        ("fe_icons_truck_truck", "Truck()", "FE/platform/ui/src/icons/line/Truck.tsx"),
        ("fe_lib_trusted_html", "trustedHtml()", "FE/platform/ui/src/lib/trusted-html.ts"),
        ("fe_view_vitals", "viewVitals()", "FE/platform/shell/src/vitals.ts"),
        ("api_spin_spinservice", "SpinService", "pen-api/src/main/java/world/spin/SpinService.java"),
        ("api_economy_walletapi", "WalletApi", "pen-api/src/main/java/economy/WalletApi.java"),
        ("fe_settings_configuracion", "configuracion()", "FE/apps/admin/src/settings/configuracion.ts"),
    ] + list(extra)
    for nid, label, src in nodes:
        G.add_node(nid, label=label, source_file=src, source_location="L1", file_type="code")
    G.add_edge("api_spin_spinservice", "api_economy_walletapi", relation="references", confidence="EXTRACTED")
    return G


def _start(text: str) -> str:
    line = next((l for l in text.splitlines() if "Start" in l), "")
    return line


def test_vietnamese_words_do_not_seed_on_folded_fragments():
    text = _query_graph_text(_graph(), "luồng quay vòng trừ tiền ví")
    assert text.startswith(_QUERY_NO_MATCH), text
    assert "Truck" not in text and "trustedHtml" not in text and "viewVitals" not in text
    # the miss says which words were set aside, so the caller can rephrase
    for word in ("trừ", "tiền", "ví"):
        assert word in text, text


def test_identifiers_inside_a_vietnamese_question_still_seed():
    text = _query_graph_text(_graph(), "luồng SpinService trừ tiền ví như thế nào")
    start = _start(text)
    assert "SpinService" in start, text
    assert "Truck" not in start and "trustedHtml" not in start


def test_vietnamese_words_match_labels_written_in_vietnamese():
    G = _graph(("docs_prd_tru_tien_vi", "Trừ tiền ví", "docs/PRD.md"))
    text = _query_graph_text(G, "trừ tiền ví như thế nào")
    start = _start(text)
    assert "Trừ tiền ví" in start, text
    assert "Truck" not in start


def test_decomposed_input_is_read_as_vietnamese():
    # macOS input methods can hand over NFD text (base letter + combining marks).
    question = unicodedata.normalize("NFD", "luồng quay vòng trừ tiền ví")
    text = _query_graph_text(_graph(), question)
    assert text.startswith(_QUERY_NO_MATCH), text
    assert "Truck" not in text


def test_vietnamese_function_words_are_not_query_terms():
    terms = _query_terms("ví là gì")
    assert "là" not in terms and "gì" not in terms
    assert "ví" in terms


@pytest.mark.parametrize("question", ["cómo funciona configuración", "wie funktioniert die configuración"])
def test_accented_words_of_other_languages_still_fold(question):
    # Spanish/German questions are not Vietnamese: folding still lets
    # "configuración" reach the unaccented identifier `configuracion()`.
    text = _query_graph_text(_graph(), question)
    assert "configuracion()" in _start(text), text
