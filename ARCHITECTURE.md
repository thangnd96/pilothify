# Architecture

pilothify is an AI-assistant skill backed by a Python library. The skill (`pilothify/skill*.md`, generated from `tools/skillgen/`) orchestrates the library; the library and its CLI also run standalone.

## Pipeline

```
detect() → extract() → build() → cluster() → analyze helpers → report.generate() → export.to_*()
```

Each stage lives in its own module and they communicate through plain Python dicts and NetworkX graphs.

- **Code**: parsed with tree-sitter into an AST. Local, deterministic, no LLM. A second pass resolves calls, imports and inheritance across files.
- **Docs, papers, images**: a semantic pass run by the host assistant's subagents (the skill) or by a configured backend (`pilothify extract --backend ...`). Images, audio and video under an app's asset folders (`detect.asset_media_folder`) stay out of it and are reported, unless `PILOTHIFY_ASSET_MEDIA=1`.
- **Video, audio**: transcribed locally before the semantic pass.

## Module responsibilities

Signatures below are the real ones - `tests/test_architecture_doc.py` imports every symbol named here, so this table cannot drift from the code.

| Module | Entry point(s) | Input → Output |
|--------|----------------|----------------|
| `detect.py` | `detect(root)` | directory → scan summary dict: `files` grouped by category, plus `total_files`, `total_words`, `warning`, `scan_root`, … |
| `extract.py` | `extract(paths, *, root=None, ...)`, `collect_files(target)` | **list** of file paths → `{nodes, edges}` dict. `collect_files` expands a directory into that list, and lives here, not in `detect.py` |
| `build.py` | `build(extractions)`, `build_from_json(extraction)` | extraction dict(s) → `nx.Graph` |
| `key_links.py` | `link_shared_keys(G)`, `identifier_key(label)` | graph → graph with a `same_key_as` edge from each non-code node opening with a key (`BUG-ADM-15-01`, `D-20`) to that key's best-connected node in another file. Run at the end of `build_from_json` |
| `route_links.py` | `link_routes(G)` | graph → graph with a `references_route` edge from each doc node naming an endpoint to the handler whose `attributes.route` serves it (Java Spring handlers carry one). Run at the end of `build_from_json` |
| `cluster.py` | `cluster(G)` | graph → `{community_id: [node_id, ...]}` (the graph is not mutated) |
| `analyze.py` | `god_nodes(G)`, `surprising_connections(G)`, `suggest_questions(G, communities, community_labels)`, `find_import_cycles(G)`, `graph_diff(G_old, G_new)` | graph → one list/dict per analysis. There is no single `analyze()` entry point. `god_nodes` leaves out test code and config files unless `include_tests_and_config=True` |
| `report.py` | `generate(G, communities, cohesion_scores, community_labels, ...)` | graph + analysis → GRAPH_REPORT.md string |
| `export.py` | `to_json`, `to_html`, `to_obsidian`, `to_svg`, `to_graphml`, `to_canvas`, `to_cypher` | graph → graph.json, graph.html, Obsidian vault, graph.svg, … one function per format |
| `wiki.py` | `to_wiki(G, communities, output_dir, ...)` | graph → one markdown article per community + `index.md` |
| `callflow_html.py` | `write_callflow_html(...)` | pilothify-out files → Mermaid architecture/call-flow HTML |
| `ingest.py` | `ingest(url, target_dir, ...)` | URL → file saved to corpus dir |
| `cache.py` | `check_semantic_cache(files, root)`, `save_semantic_cache(nodes, edges, ...)` | files → cached nodes / edges / hyperedges + the list of files still needing extraction |
| `security.py` | `validate_url`, `safe_fetch`, `validate_graph_path`, `sanitize_label` | URL / path / label → validated value, or raises |
| `validate.py` | `validate_extraction(data)`, `assert_valid(data)` | extraction dict → **list of schema error strings** (`validate_extraction` returns them; `assert_valid` raises) |
| `serve.py` | `serve(graph_path)`, `serve_http(graph_path, *, host, port, ...)` | graph file path → MCP stdio server / HTTP server |
| `watch.py` | `watch(watch_path, debounce=3.0)`, `check_update(watch_path)` | directory → rebuild on change; `check_update` reports whether a re-extraction is pending |
| `benchmark.py` | `run_benchmark(graph_path)` | graph file → corpus vs subgraph token comparison |

### Calling `extract()` from your own code

`extract()` takes a **list** of paths, and `root` is keyword-only and optional:

```python
from pathlib import Path
from pilothify.extract import extract

paths = [Path("src/lib/content.ts"), Path("src/pages/index.astro")]
result = extract(paths, root=Path(".").resolve())   # pass root explicitly
```

Always pass `root`. Node ids and `source_file` values are derived relative to it; when it is omitted, `extract()` infers one from the paths you passed, which is the common parent of *that list* rather than your project root.

## Extraction output schema

Every extractor returns:

```json
{
  "nodes": [
    {"id": "unique_string", "label": "human name", "source_file": "path", "source_location": "L42"}
  ],
  "edges": [
    {"source": "id_a", "target": "id_b", "relation": "calls|imports|uses|...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
  ]
}
```

`validate.py` enforces this schema before `build()` consumes it.

## Confidence labels

| Label | Meaning |
|-------|---------|
| `EXTRACTED` | Stated in the source (an import statement, a direct call) |
| `INFERRED` | Resolved by a rule (declared type, same package, call-graph second pass), with a `confidence_score` |
| `AMBIGUOUS` | Uncertain; flagged for review in GRAPH_REPORT.md |

## Edge direction in graph.json

`graph.json` is written `"directed": false`, but every link is directed: arc order is the direction (`source` → `target`); older files carry it in `_src`/`_tgt` markers. Load through `paths.load_node_link_graph()` (or apply `paths.restore_arc_direction()` to the raw dict first) and read direction as `data.get("_src", u)` / `data.get("_tgt", v)`, never from `u, v`.

The undirected build keeps one edge per node pair. For two files that import each other, the dropped direction survives as a `reverse_import` stamp, and a type-only import (`import type`, `if TYPE_CHECKING:`) stays `type_only` so it never closes an import cycle.

## Querying

`serve.py` scores node labels against the question (exact, prefix and substring tiers, IDF-weighted), picks seed nodes and walks the graph (BFS or DFS) within a token budget. The same code backs the `query`, `path` and `explain` CLI commands and the MCP tools. Diacritics are folded for matching, except in a Vietnamese question: its accented words only match labels that hold the same word, so "trừ" cannot match `Truck`.

## Adding a new language extractor

1. Add an `extract_<lang>(path: Path) -> dict` function under `pilothify/extractors/` (tree-sitter parse → walk nodes → collect `nodes` and `edges` → call-graph second pass for INFERRED `calls` edges); `extract.py` re-exports it.
2. Register the file suffix in `extract()`'s dispatch table and in `collect_files()` (both in `extract.py`).
3. Add the suffix to `CODE_EXTENSIONS` in `detect.py` and `_WATCHED_EXTENSIONS` in `watch.py`.
4. Add the tree-sitter package to `pyproject.toml` dependencies.
5. Add a fixture file to `tests/fixtures/` and tests to `tests/test_languages.py`.

## Security

All external input passes through `pilothify/security.py` before use:

- URLs → `validate_url()` (http/https only) + `_NoFileRedirectHandler` (blocks file:// redirects)
- Fetched content → `safe_fetch()` / `safe_fetch_text()` (size cap, timeout)
- Graph file paths → `validate_graph_path()` (must resolve inside `pilothify-out/`)
- Node labels → `sanitize_label()` (strips control chars, caps 256 chars)

## Testing

One test file per module under `tests/`, isolated from the network and from the real filesystem through temporary directories:

```bash
.venv/bin/python -m pytest tests/ -q -n 8
```

The skill files under `pilothify/` are generated. After editing a fragment in `tools/skillgen/fragments/`, run `python -m tools.skillgen` then `python -m tools.skillgen --bless`; `python -m tools.skillgen --check` fails on drift.
