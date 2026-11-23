"""A sandbox that denies POSIX semaphores falls back to sequential, and says why.

Claude Code's Bash sandbox on macOS refuses `sem_open`, so the process pool
fails to start with `[Errno 1] Operation not permitted`. Extraction already fell
back to sequential, but the bare errno read like a defect. The warning now names
the cause, and the graph is the same either way.
"""
from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

import pytest

from pilothify.extract import _PARALLEL_THRESHOLD, extract


def _corpus(root: Path) -> list[Path]:
    paths = []
    for i in range(_PARALLEL_THRESHOLD + 2):
        p = root / f"mod{i}.py"
        p.write_text(f"def f{i}():\n    return {i}\n", encoding="utf-8")
        paths.append(p)
    return paths


def _denied(*_a, **_k):
    raise PermissionError(1, "Operation not permitted")


def test_denied_pool_names_the_sandbox_and_matches_the_parallel_graph(tmp_path, monkeypatch, capsys):
    paths = _corpus(tmp_path)
    expected = extract(paths, cache_root=tmp_path / "a", root=tmp_path, parallel=False)
    monkeypatch.setenv("PILOTHIFY_MAX_WORKERS", "4")
    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", _denied)
    got = extract(paths, cache_root=tmp_path / "b", root=tmp_path, parallel=True)
    out = capsys.readouterr().out
    assert "parallel extraction unavailable" in out
    assert "POSIX semaphores" in out and "sandbox" in out
    key = lambda r: json.dumps(sorted(json.dumps(n, sort_keys=True) for n in r["nodes"]))
    assert key(got) == key(expected)


def test_other_pool_errors_keep_the_short_warning(tmp_path, monkeypatch, capsys):
    paths = _corpus(tmp_path)
    monkeypatch.setenv("PILOTHIFY_MAX_WORKERS", "4")

    def no_space(*_a, **_k):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", no_space)
    extract(paths, cache_root=tmp_path, root=tmp_path, parallel=True)
    out = capsys.readouterr().out
    assert "parallel extraction unavailable" in out
    assert "POSIX semaphores" not in out
