"""JS/TS-family files use the AST cache, and a hit is only served when every
module resolution its extraction made still resolves the same way.

A JS/TS extraction depends on more than the file's bytes: tsconfig paths and
baseUrl, package.json imports and workspaces, and which candidate files exist
(`./util` is util.ts once util.ts appears beside util.js). These files used to
bypass the cache entirely, so a full rebuild of a front end re-parsed every
file every time (32/3,440 hits on a warm cache). Each entry now records the
resolutions its extraction made; a hit re-runs them, and any difference is a
miss. An entry without that record (written by hand, or by an older release)
is never served.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from pilothify.extract import extract


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _ts_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.suffix in (".ts", ".tsx", ".js", ".vue", ".ejs") and "pilothify-out" not in p.parts)


def _run(root: Path, capsys) -> tuple[dict, str]:
    result = extract(_ts_files(root), cache_root=root, root=root, parallel=False)
    return result, capsys.readouterr().out


def _shape(result: dict) -> tuple:
    nodes = sorted(json.dumps(n, sort_keys=True) for n in result["nodes"])
    edges = sorted(
        json.dumps({k: e.get(k) for k in ("source", "target", "relation")}, sort_keys=True)
        for e in result["edges"]
    )
    return nodes, edges


def _cold(root: Path, tmp_path: Path, capsys) -> dict:
    cold = tmp_path / "cold"
    shutil.rmtree(cold, ignore_errors=True)
    shutil.copytree(root, cold, ignore=shutil.ignore_patterns("pilothify-out"))
    result, _ = _run(cold, capsys)
    # Bring the cold run's absolute paths back to the warm root for comparison.
    text = json.dumps(result).replace(str(cold.resolve()), str(root.resolve())).replace(str(cold), str(root))
    return json.loads(text)


def _app(root: Path) -> None:
    _write(root / "tsconfig.json", '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}\n')
    _write(root / "src" / "lib" / "fmt.ts", "export function fmt(v: number) { return String(v); }\n")
    _write(root / "src" / "util.js", "export function pick() { return 1; }\n")
    _write(
        root / "src" / "main.ts",
        "import { fmt } from '@/lib/fmt';\n"
        "import { pick } from './util';\n"
        "import { later } from './later';\n"
        "export function main() { return fmt(pick()) + later(); }\n",
    )


def test_a_warm_cache_serves_unchanged_js_files_and_matches_a_cold_build(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    first, out1 = _run(root, capsys)
    assert "AST cache: 0/3 files served from cache" in out1
    second, out2 = _run(root, capsys)
    assert "AST cache: 3/3 files served from cache (100%)" in out2, out2
    assert _shape(second) == _shape(first)


def test_a_new_file_that_wins_resolution_makes_the_importer_a_miss(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _run(root, capsys)
    # `./util` resolved to util.js; util.ts takes precedence once it exists.
    _write(root / "src" / "util.ts", "export function pick() { return 2; }\n")
    warm, out = _run(root, capsys)
    # fmt.ts and util.js are hits; main.ts is a miss, util.ts is new.
    assert "AST cache: 2/4 files served from cache" in out, out
    assert _shape(warm) == _shape(_cold(root, tmp_path, capsys))
    util_ts = {n["id"] for n in warm["nodes"] if str(n.get("source_file", "")).endswith("util.ts")}
    main = {n["id"] for n in warm["nodes"] if str(n.get("source_file", "")).endswith("main.ts")}
    assert any(e["source"] in main and e["target"] in util_ts for e in warm["edges"]), "main.ts still imports util.js"


def test_an_import_that_starts_to_resolve_makes_the_importer_a_miss(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _run(root, capsys)
    _write(root / "src" / "later.ts", "export function later() { return 3; }\n")
    warm, out = _run(root, capsys)
    assert "AST cache: 2/4 files served from cache" in out, out
    assert _shape(warm) == _shape(_cold(root, tmp_path, capsys))


def test_a_tsconfig_paths_change_makes_the_alias_importer_a_miss(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _write(root / "app" / "lib" / "fmt.ts", "export function fmt(v: number) { return `${v}`; }\n")
    _run(root, capsys)
    _write(root / "tsconfig.json", '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["app/*"]}}}\n')
    warm, out = _run(root, capsys)
    assert "AST cache: 3/4 files served from cache" in out, out
    assert _shape(warm) == _shape(_cold(root, tmp_path, capsys))


def test_a_deleted_target_makes_the_importer_a_miss(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _run(root, capsys)
    (root / "src" / "util.js").unlink()
    warm, out = _run(root, capsys)
    assert "AST cache: 1/2 files served from cache" in out, out
    assert _shape(warm) == _shape(_cold(root, tmp_path, capsys))


def test_a_relocated_checkout_replays_its_js_entries(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _run(root, capsys)
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    warm, out = _run(moved, capsys)
    assert "AST cache: 3/3 files served from cache (100%)" in out, out
    cold = tmp_path / "cold-moved"
    shutil.copytree(moved, cold, ignore=shutil.ignore_patterns("pilothify-out"))
    fresh, _ = _run(cold, capsys)
    fresh = json.loads(json.dumps(fresh).replace(str(cold.resolve()), str(moved.resolve())).replace(str(cold), str(moved)))
    assert _shape(warm) == _shape(fresh)


def test_vue_and_ejs_entries_follow_the_same_rule(tmp_path, capsys):
    root = tmp_path / "app"
    _app(root)
    _write(
        root / "src" / "Panel.vue",
        "<template><div>{{ v }}</div></template>\n"
        "<script setup lang=\"ts\">\nimport { fmt } from '@/lib/fmt';\nconst v = fmt(1);\n</script>\n",
    )
    _write(root / "views" / "page.ejs", "<%- include('partial') %>\n")
    _run(root, capsys)
    _write(root / "views" / "partial.ejs", "<p>hi</p>\n")
    warm, out = _run(root, capsys)
    # page.ejs now resolves its include; Panel.vue and the rest are unchanged.
    assert "AST cache: 4/6 files served from cache" in out, out
    assert _shape(warm) == _shape(_cold(root, tmp_path, capsys))


def _run_files(root: Path, files: list[Path], capsys) -> tuple[dict, str]:
    result = extract(files, cache_root=root, root=root, parallel=False)
    return result, capsys.readouterr().out


def test_an_astro_entry_is_checked_against_its_resolutions_too(tmp_path, capsys):
    # Astro resolves its frontmatter imports through the same resolvers; its
    # entry was cached before, with nothing to notice a candidate that now wins.
    root = tmp_path / "site"
    _write(root / "src" / "lib" / "content.js", "export function getPosts() { return []; }\n")
    page = _write(
        root / "src" / "pages" / "index.astro",
        "---\nimport { getPosts } from '../lib/content';\nconst posts = getPosts();\n---\n<h1>{posts.length}</h1>\n",
    )
    files = [root / "src" / "lib" / "content.js", page]
    _run_files(root, files, capsys)
    _, out = _run_files(root, files, capsys)
    assert "AST cache: 2/2 files served from cache (100%)" in out, out

    _write(root / "src" / "lib" / "content.ts", "export function getPosts() { return [1]; }\n")
    files.append(root / "src" / "lib" / "content.ts")
    warm, out = _run_files(root, files, capsys)
    # content.js is a hit; index.astro must re-resolve `../lib/content`.
    assert "AST cache: 1/3 files served from cache" in out, out
    cold_root = tmp_path / "cold"
    shutil.copytree(root, cold_root, ignore=shutil.ignore_patterns("pilothify-out"))
    cold, _ = _run_files(cold_root, [cold_root / p.relative_to(root) for p in files], capsys)
    cold = json.loads(json.dumps(cold).replace(str(cold_root.resolve()), str(root.resolve())).replace(str(cold_root), str(root)))
    assert _shape(warm) == _shape(cold)


def test_an_extensionless_node_script_is_checked_against_its_resolutions(tmp_path, capsys):
    root = tmp_path / "tool"
    cli = _write(root / "bin" / "cli", "#!/usr/bin/env node\nconst { run } = require('./later');\nrun();\n")
    _run_files(root, [cli], capsys)
    _, out = _run_files(root, [cli], capsys)
    assert "AST cache: 1/1 files served from cache (100%)" in out, out

    later = _write(root / "bin" / "later.js", "exports.run = function run() { return 1; };\n")
    warm, out = _run_files(root, [cli, later], capsys)
    assert "AST cache: 0/2 files served from cache" in out, out
    cold_root = tmp_path / "cold"
    shutil.copytree(root, cold_root, ignore=shutil.ignore_patterns("pilothify-out"))
    cold, _ = _run_files(cold_root, [cold_root / "bin" / "cli", cold_root / "bin" / "later.js"], capsys)
    cold = json.loads(json.dumps(cold).replace(str(cold_root.resolve()), str(root.resolve())).replace(str(cold_root), str(root)))
    assert _shape(warm) == _shape(cold)
