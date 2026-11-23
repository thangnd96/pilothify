"""The nearest tsconfig/jsconfig lookup is memoized per extract() run.

Every non-relative JS/TS import asked for the nearest config twice (aliases,
then baseUrl), and each ask walked every parent directory with two `exists()`
probes. On a 3,400-file front end that walk was the largest single cost of a
full rebuild after parsing. The answer cannot change within one run, so it is
remembered per start directory and dropped when the next run starts, like the
alias and baseUrl caches.
"""
from __future__ import annotations

from pathlib import Path

from pilothify.extract import extract
from pilothify.extractors import resolution
from pilothify.extractors.resolution import _find_js_config


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_lookup_probes_each_directory_once_per_run(tmp_path: Path, monkeypatch):
    _write(tmp_path / "tsconfig.json", "{}\n")
    deep = tmp_path / "src" / "a" / "b" / "c"
    deep.mkdir(parents=True)
    resolution._JS_CONFIG_LOOKUP_CACHE.clear()
    probes: list[str] = []
    real_exists = Path.exists

    def counting_exists(self, *args, **kwargs):
        if self.name in ("tsconfig.json", "jsconfig.json"):
            probes.append(str(self))
        return real_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", counting_exists)
    first = _find_js_config(deep)
    after_first = len(probes)
    assert first is not None and first[0] == (tmp_path / "tsconfig.json").resolve()
    assert after_first > 0
    assert _find_js_config(deep) == first
    assert len(probes) == after_first, "a repeated lookup must not walk the tree again"


def test_a_config_added_between_runs_is_found(tmp_path: Path):
    source = _write(tmp_path / "src" / "app.ts", "import { x } from '@/lib/x';\nexport const y = x;\n")
    _write(tmp_path / "src" / "lib" / "x.ts", "export const x = 1;\n")
    extract([source], cache_root=tmp_path, root=tmp_path)
    assert _find_js_config(source.parent) is None

    _write(
        tmp_path / "tsconfig.json",
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}\n',
    )
    result = extract([source], cache_root=tmp_path, root=tmp_path)
    assert _find_js_config(source.parent) is not None
    targets = {e.get("target") for e in result["edges"] if e.get("relation") == "imports_from"}
    assert "src_lib_x" in targets
