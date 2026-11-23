"""An incremental update resolves imports through unchanged barrels like a full build.

A changed file that imports a symbol through an `index.ts` barrel needs the
barrel's export facts to reach the declaring module. The barrel is not
re-extracted when only the importer changed, so the import used to stay on the
barrel's own id: build minted an `external` stub such as
`src_components_ui_index_button`, the `calls` edges from the importer to the
real component disappeared, and `affected`/blast radius missed the caller.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pilothify.watch import _rebuild_code

pytest.importorskip("tree_sitter_typescript")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _corpus(root: Path) -> None:
    _write(root / "package.json", '{"name": "barrels", "version": "1.0.0"}\n')
    _write(
        root / "tsconfig.json",
        '{"compilerOptions": {"jsx": "react-jsx", "baseUrl": ".", "paths": {"@/*": ["src/*"]}}}\n',
    )
    _write(
        root / "src/components/ui/button.tsx",
        "export function Button(props: { label: string }) { return <button>{props.label}</button>; }\n",
    )
    _write(root / "src/components/ui/card.tsx", "export function Card() { return <div />; }\n")
    _write(
        root / "src/components/ui/badge.tsx",
        "export function Badge() { return <span />; }\n",
    )
    # Named re-export, star re-export, and an import-then-export bridge.
    _write(
        root / "src/components/ui/index.ts",
        "import { Badge } from './badge';\n"
        "export { Button } from './button';\n"
        "export * from './card';\n"
        "export { Badge };\n",
    )
    # A second hop: a barrel that re-exports the first one.
    _write(root / "src/components/index.ts", "export * from './ui';\n")
    _write(
        root / "src/features/panel.tsx",
        "import { Button, Card, Badge } from '@/components/ui';\n"
        "export function Panel() { return <Card><Badge /><Button label=\"x\" /></Card>; }\n",
    )
    _write(
        root / "src/features/deep.tsx",
        "import { Button } from '../components';\n"
        "export function Deep() { return <Button label=\"d\" />; }\n",
    )
    _write(
        root / "src/features/other.tsx",
        "import { Button } from '../components/ui';\n"
        "export function Other() { return <Button label=\"y\" />; }\n",
    )


def _graph(root: Path) -> dict:
    return json.loads((root / "pilothify-out" / "graph.json").read_text(encoding="utf-8"))


def _edges(graph: dict) -> set[tuple[str, str, str]]:
    return {
        (e["source"], e["target"], e["relation"])
        for e in graph.get("links", graph.get("edges", []))
    }


def _stubs(graph: dict) -> set[str]:
    return {
        n["id"] for n in graph["nodes"]
        if n.get("type") == "external" or n.get("external")
    }


def _edit_consumers(root: Path) -> None:
    panel = root / "src/features/panel.tsx"
    panel.write_text(
        panel.read_text(encoding="utf-8").replace('label="x" />', 'label="x" /><Button label="z" />'),
        encoding="utf-8",
    )
    deep = root / "src/features/deep.tsx"
    deep.write_text(deep.read_text(encoding="utf-8") + "// touched\n", encoding="utf-8")


@pytest.mark.parametrize("no_cluster", [True, False])
def test_incremental_update_through_unchanged_barrels_matches_a_full_build(tmp_path: Path, no_cluster: bool):
    warm = tmp_path / "warm"
    _corpus(warm)
    assert _rebuild_code(warm, no_cluster=no_cluster, acquire_lock=False)
    _edit_consumers(warm)
    assert _rebuild_code(warm, incremental=True, no_cluster=no_cluster, acquire_lock=False)

    cold = tmp_path / "cold"
    shutil.copytree(warm, cold, ignore=shutil.ignore_patterns("pilothify-out"))
    assert _rebuild_code(cold, no_cluster=no_cluster, acquire_lock=False)

    warm_graph, cold_graph = _graph(warm), _graph(cold)
    barrel_stubs = {s for s in _stubs(warm_graph) if "_index_" in s}
    assert not barrel_stubs, f"imports left on a barrel: {sorted(barrel_stubs)}"
    assert {n["id"] for n in warm_graph["nodes"]} == {n["id"] for n in cold_graph["nodes"]}
    assert _edges(warm_graph) == _edges(cold_graph)

    calls = {(s, t) for s, t, r in _edges(warm_graph) if r == "calls"}
    assert ("src_features_panel_panel", "src_components_ui_button_button") in calls
    assert ("src_features_panel_panel", "src_components_ui_card_card") in calls
    assert ("src_features_panel_panel", "src_components_ui_badge_badge") in calls
    assert ("src_features_deep_deep", "src_components_ui_button_button") in calls


def test_incremental_update_mints_no_node_for_an_unchanged_barrel(tmp_path: Path):
    """Barrel facts only steer resolution: the barrel keeps its persisted nodes."""
    _corpus(tmp_path)
    assert _rebuild_code(tmp_path, no_cluster=True, acquire_lock=False)
    before = {
        n["id"]: n for n in _graph(tmp_path)["nodes"]
        if n.get("source_file", "").startswith("src/components/")
    }
    _edit_consumers(tmp_path)
    assert _rebuild_code(tmp_path, incremental=True, no_cluster=True, acquire_lock=False)
    after = {
        n["id"]: n for n in _graph(tmp_path)["nodes"]
        if n.get("source_file", "").startswith("src/components/")
    }
    assert after.keys() == before.keys()
