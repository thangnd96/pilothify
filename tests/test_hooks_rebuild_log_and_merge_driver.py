"""Hook rebuild log location, and installing the hooks without the merge driver.

The four hooks set `PILOTHIFY_REBUILD_LOG` to `~/.cache/pilothify-rebuild.log`
unconditionally, so a value the caller exported never took effect. Inside a
sandbox that cannot write `~/.cache` (Claude Code's Bash sandbox) the launcher
then sent the rebuild's output to /dev/null. The hooks now keep a caller's
value, and the launcher falls back to `<out>/rebuild.log` when the log cannot be
opened.

`hook install` also registers the graph.json union merge driver, which writes a
`.gitattributes` line and git config. A repository that gitignores
`pilothify-out/` never merges graph.json, so `--no-merge-driver` installs only
the hooks; `hook uninstall --no-merge-driver` leaves the driver alone.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pilothify.hooks import (
    _CHECKOUT_SCRIPT, _HOOK_SCRIPT, _LAUNCHER_TEMPLATE, _MERGE_SCRIPT, _REWRITE_SCRIPT,
    install, status, uninstall,
)

PYTHON = sys.executable
_SCRIPTS = {
    "post-commit": _HOOK_SCRIPT,
    "post-checkout": _CHECKOUT_SCRIPT,
    "post-merge": _MERGE_SCRIPT,
    "post-rewrite": _REWRITE_SCRIPT,
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


@pytest.mark.parametrize("name", sorted(_SCRIPTS))
def test_hooks_keep_a_rebuild_log_the_caller_exported(name):
    script = _SCRIPTS[name]
    assert '_PILOTHIFY_LOG="${PILOTHIFY_REBUILD_LOG:-${HOME}/.cache/pilothify-rebuild.log}"' in script
    assert '_PILOTHIFY_LOG="${HOME}/.cache/pilothify-rebuild.log"' not in script


def _launch(cwd: Path, env: dict) -> None:
    body = "print('rebuild child ran', flush=True)"
    code = _LAUNCHER_TEMPLATE.replace("__REBUILD_BODY__", body)
    subprocess.run([PYTHON, "-c", code], cwd=cwd, env=env, check=True, timeout=30)


def _wait_for(path: Path, text: str) -> str:
    import time

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if path.exists() and text in path.read_text(encoding="utf-8", errors="replace"):
            return path.read_text(encoding="utf-8", errors="replace")
        time.sleep(0.05)
    raise AssertionError(f"{path} never received {text!r}")


def test_launcher_writes_to_the_exported_log(tmp_path):
    log = tmp_path / "custom" / "rebuild.log"
    _launch(tmp_path, {**os.environ, "PILOTHIFY_REBUILD_LOG": str(log)})
    _wait_for(log, "rebuild child ran")


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_launcher_falls_back_to_the_output_dir_when_the_log_is_not_writable(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        env = {**os.environ, "PILOTHIFY_REBUILD_LOG": str(locked / "sub" / "rebuild.log")}
        env.pop("PILOTHIFY_OUT", None)
        _launch(tmp_path, env)
        _wait_for(tmp_path / "pilothify-out" / "rebuild.log", "rebuild child ran")
    finally:
        locked.chmod(0o700)


def test_install_without_merge_driver_writes_only_the_hooks(tmp_path):
    repo = _repo(tmp_path)
    result = install(repo, merge_driver=False)
    assert "merge driver: skipped" in result
    assert not (repo / ".gitattributes").exists()
    assert _git(repo, "config", "--get", "merge.pilothify.driver").returncode != 0
    for name in _SCRIPTS:
        assert (repo / ".git" / "hooks" / name).exists()
    assert "post-commit: installed" in status(repo)


def test_uninstall_without_merge_driver_keeps_an_existing_registration(tmp_path):
    repo = _repo(tmp_path)
    install(repo)
    attrs = (repo / ".gitattributes").read_text(encoding="utf-8")
    result = uninstall(repo, merge_driver=False)
    assert "merge driver: left in place" in result
    assert (repo / ".gitattributes").read_text(encoding="utf-8") == attrs
    assert _git(repo, "config", "--get", "merge.pilothify.driver").returncode == 0
    for name in _SCRIPTS:
        assert not (repo / ".git" / "hooks" / name).exists()


def test_cli_accepts_no_merge_driver(tmp_path):
    repo = _repo(tmp_path)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(Path(__file__).resolve().parents[1]), os.environ.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)}
    res = subprocess.run(
        [PYTHON, "-m", "pilothify", "hook", "install", "--no-merge-driver"],
        cwd=repo, capture_output=True, text=True, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert "merge driver: skipped" in res.stdout
    assert not (repo / ".gitattributes").exists()
    res = subprocess.run(
        [PYTHON, "-m", "pilothify", "hook", "uninstall", "--no-merge-driver"],
        cwd=repo, capture_output=True, text=True, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert not (repo / ".git" / "hooks" / "post-commit").exists()
    bad = subprocess.run(
        [PYTHON, "-m", "pilothify", "hook", "install", "--bogus"],
        cwd=repo, capture_output=True, text=True, env=env,
    )
    assert bad.returncode != 0
