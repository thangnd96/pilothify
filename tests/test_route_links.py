"""Spring handlers carry the route they serve, and docs naming it link to them."""
from pathlib import Path

import networkx as nx

from pilothify.build import build_from_json
from pilothify.extract import extract
from pilothify.route_links import ROUTE_RELATION, link_routes

CONTROLLER = """\
package x;
@RestController
@RequestMapping("/api/v1/game/cinema/screen")
class CinemaController {
  @PostMapping("/playback") void playback() {}
  @PutMapping void setScreen() {}
  @RequestMapping(value = {"/x", "/y"}, method = RequestMethod.DELETE) void clear() {}
  @GetMapping(path = "/{id}") void read() {}
  @GetMapping(Paths.BASE + "/z") void computed() {}
  void plain() {}
}
@RequestMapping(ProbeController.BASE)
class ProbeController {
  static final String BASE = "/api/v1/qe-probe";
  static final String LIMITED = "/limited";
  @GetMapping("/ping") void ping() {}
  @GetMapping(LIMITED + "/{id}") void limited() {}
}
@RequestMapping(Paths.CTRL)
class ElsewhereController {
  @GetMapping("/a") void elsewhere() {}
}
"""


def _routes(tmp_path):
    src = tmp_path / "CinemaController.java"
    src.write_text(CONTROLLER)
    result = extract([src], cache_root=tmp_path)
    return {
        n["label"]: (n.get("attributes") or {}).get("route")
        for n in result["nodes"] if n["label"].endswith("()")
    }


def test_spring_handlers_carry_the_route_joined_to_the_class_prefix(tmp_path):
    routes = _routes(tmp_path)
    assert routes[".playback()"] == "POST /api/v1/game/cinema/screen/playback"
    assert routes[".setScreen()"] == "PUT /api/v1/game/cinema/screen"
    assert routes[".clear()"] == "DELETE /api/v1/game/cinema/screen/x, DELETE /api/v1/game/cinema/screen/y"
    assert routes[".read()"] == "GET /api/v1/game/cinema/screen/{id}"


def test_the_declaring_class_string_constants_resolve(tmp_path):
    routes = _routes(tmp_path)
    assert routes[".ping()"] == "GET /api/v1/qe-probe/ping"
    assert routes[".limited()"] == "GET /api/v1/qe-probe/limited/{id}"


def test_an_unreadable_path_or_prefix_or_no_mapping_gets_no_route(tmp_path):
    routes = _routes(tmp_path)
    assert routes[".computed()"] is None  # another class's constant
    assert routes[".elsewhere()"] is None  # the class prefix cannot be read, so no "/a"
    assert routes[".plain()"] is None


def _graph():
    G = nx.Graph()
    G.add_node("h_play", label=".playback()", file_type="code", source_file="C.java",
               attributes={"route": "POST /api/v1/game/cinema/screen/playback"})
    G.add_node("h_read", label=".read()", file_type="code", source_file="C.java",
               attributes={"route": "GET /api/v1/game/cinema/screen/{id}"})
    return G


def _doc(G, nid, label):
    G.add_node(nid, label=label, file_type="document", source_file="docs/spec.md")


def test_exact_route_mention_is_extracted_and_a_versionless_one_inferred():
    G = _graph()
    _doc(G, "exact", "GET /api/v1/game/cinema/screen/{screenId} trả màn hình")
    _doc(G, "suffix", "Điều khiển phát (POST /game/cinema/screen/playback)")
    assert link_routes(G) == 2
    exact = G.edges["exact", "h_read"]
    assert exact["relation"] == ROUTE_RELATION and exact["confidence"] == "EXTRACTED"
    suffix = G.edges["suffix", "h_play"]
    assert suffix["confidence"] == "INFERRED" and suffix["confidence_score"] == 0.95
    assert (suffix["_src"], suffix["_tgt"]) == ("suffix", "h_play")


def test_wrong_verb_glob_and_ambiguous_suffix_do_not_link():
    G = _graph()
    G.add_node("h_other", label=".playback()", file_type="code", source_file="D.java",
               attributes={"route": "POST /api/v1/ctrl/cinema/screen/playback"})
    _doc(G, "verb", "GET /api/v1/game/cinema/screen/playback")
    _doc(G, "glob", "Mọi lệnh dưới /api/v1/game/** theo sub")
    _doc(G, "ambiguous", "POST /cinema/screen/playback")  # ends both handlers' paths
    assert link_routes(G) == 0


def test_build_from_json_links_routes():
    G = build_from_json({
        "nodes": [
            {"id": "c_play", "label": ".playback()", "file_type": "code", "source_file": "C.java",
             "attributes": {"route": "POST /api/v1/game/cinema/screen/playback"}},
            {"id": "docs_spec", "label": "POST /game/cinema/screen/playback", "file_type": "document",
             "source_file": "docs/spec.md"},
        ],
        "edges": [],
    })
    assert G.edges["docs_spec", "c_play"]["relation"] == ROUTE_RELATION
