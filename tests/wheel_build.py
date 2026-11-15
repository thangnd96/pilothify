"""Build the pilothify wheel from a copy of the checkout, never in it."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_IGNORE = shutil.ignore_patterns(".git", ".venv", "build", "dist", "*.egg-info", "pilothify-out",
                                 "__pycache__", ".pytest_cache", "node_modules")


def _copy_checkout(dest: Path) -> None:
    """Copy the tracked files, or without git the tree minus build output."""
    try:
        listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"],
                                capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        shutil.copytree(REPO, dest, ignore=_IGNORE, dirs_exist_ok=True)
        return
    for rel in filter(None, listed.decode("utf-8").split("\0")):
        src = REPO / rel
        if src.is_file():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)


def build_wheel_names() -> set[str]:
    """Arcnames of a wheel built from a temporary copy of the checkout.

    Building in the checkout rewrote its pilothify.egg-info, which sits ahead of
    site-packages on sys.path, so processes started later in the same test run
    read a different pilothify version than the ones already running. It also
    shared one build/ dir between concurrent runs, which then needed a lock.
    """
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "src", Path(tmp) / "out"
        _copy_checkout(src)
        proc = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(out), str(src)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"wheel build failed:\nstdout:\n{proc.stdout[-1000:]}\nstderr:\n{proc.stderr[-1000:]}"
            )
        wheels = list(out.glob("pilothify-*.whl"))
        assert wheels, "no wheel was produced"
        with zipfile.ZipFile(wheels[0]) as zf:
            return set(zf.namelist())
