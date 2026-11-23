"""`pilothify update --full`, and the commit stamp of a --no-cluster graph.

`update --force` was the only way to make `update` re-extract the whole corpus,
and it also switches the shrink guard off. A caller that only wants the graph a
full build would produce (to drop what incremental updates left behind) had to
accept an unguarded write, or use `extract`, which is a different pipeline.
`--full` re-extracts everything through the update pipeline and keeps the guard,
and is a no-op when the last build was already a full one of the same inputs.

The raw --no-cluster writes (`update --no-cluster`, `extract --no-cluster`)
left `built_at_commit` out of graph.json, so a consumer comparing it with HEAD
could not tell a fresh graph from a stale one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable
_LLM_ENV_KEYS = {
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "MOONSHOT_API_KEY", "DEEPSEEK_API_KEY",
}


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _LLM_ENV_KEYS}
    env["PILOTHIFY_BACKEND"] = "none"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(__file__).resolve().parents[1]), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    return subprocess.run(
        [PYTHON, "-m", "pilothify", *args], cwd=cwd, capture_output=True, text=True, env=env,
    )


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text("from util import helper\n\n\ndef run():\n    return helper()\n", encoding="utf-8")
    (root / "util.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _graph(root: Path) -> dict:
    return json.loads((root / "pilothify-out" / "graph.json").read_text(encoding="utf-8"))


def test_full_flag_rebuilds_through_the_update_pipeline_with_the_guard_on(monkeypatch, tmp_path):
    import pilothify.watch as watch
    from pilothify.__main__ import main

    calls: list[dict] = []

    def record(path, **kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(watch, "_rebuild_code", record)
    monkeypatch.chdir(tmp_path)
    for argv, incremental, full, force in (
        (["update", "."], True, False, False),
        (["update", ".", "--full"], False, True, False),
        (["update", ".", "--full", "--force"], False, True, True),
    ):
        monkeypatch.setattr(sys, "argv", ["pilothify", *argv])
        main()
        assert calls[-1]["incremental"] is incremental, argv
        assert calls[-1].get("full", False) is full, argv
        assert calls[-1]["force"] is force, argv


def test_a_queued_incremental_record_does_not_narrow_an_explicit_full_request(tmp_path, monkeypatch):
    """A default pass that drains an incremental record runs incrementally
    (test_update_lock_contention I3); an explicit full request stays full,
    which serves that record too."""
    import pilothify.extract as extract_mod
    from pilothify.watch import _queue_pending_incremental, _rebuild_code

    repo = _repo(tmp_path / "repo")
    assert _rebuild_code(repo, acquire_lock=False)
    app = repo / "app.py"
    app.write_text(app.read_text(encoding="utf-8") + "\n\ndef more():\n    return 3\n", encoding="utf-8")
    _queue_pending_incremental(repo / "pilothify-out")
    batches: list[list[str]] = []
    real = extract_mod.extract

    def spy(targets, **kwargs):
        batches.append(sorted(Path(p).name for p in targets))
        return real(targets, **kwargs)

    monkeypatch.setattr(extract_mod, "extract", spy)
    assert _rebuild_code(repo, full=True, block_on_lock=True)
    assert batches and batches[0] == ["app.py", "util.py"], batches
    assert not (repo / "pilothify-out" / ".pending_incremental").exists()


def test_full_after_an_incremental_update_re_extracts_every_file(tmp_path):
    repo = _repo(tmp_path / "repo")
    assert _run(["update", "."], repo).returncode == 0
    (repo / "app.py").write_text(
        (repo / "app.py").read_text(encoding="utf-8") + "\n\ndef again():\n    return run()\n",
        encoding="utf-8",
    )
    incremental = _run(["update", "."], repo)
    assert incremental.returncode == 0, incremental.stderr
    assert "Incremental: re-extracting 1 of" in incremental.stdout

    full = _run(["update", ".", "--full"], repo)
    assert full.returncode == 0, full.stderr
    assert "Incremental" not in full.stdout
    assert "No relevant changes" not in full.stdout
    # Both files reach extract(), not only the one that changed.
    assert "/2 files served from cache" in full.stdout, full.stdout

    # The last build is now a full one of these inputs: --full has nothing to do.
    again = _run(["update", ".", "--full"], repo)
    assert again.returncode == 0, again.stderr
    assert "No relevant changes" in again.stdout


@pytest.mark.parametrize("args", [["update", ".", "--no-cluster"], ["extract", ".", "--code-only", "--no-cluster"]])
def test_no_cluster_graph_carries_the_commit_it_was_built_at(tmp_path, args):
    repo = _repo(tmp_path / "repo")
    res = _run(args, repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert _graph(repo).get("built_at_commit") == _git(repo, "rev-parse", "HEAD")


def test_no_cluster_update_stamps_the_new_commit_when_the_graph_changes(tmp_path):
    repo = _repo(tmp_path / "repo")
    assert _run(["update", ".", "--no-cluster"], repo).returncode == 0
    (repo / "extra.py").write_text("def extra():\n    return 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "extra")
    assert _run(["update", ".", "--no-cluster"], repo).returncode == 0
    assert _graph(repo).get("built_at_commit") == _git(repo, "rev-parse", "HEAD")
