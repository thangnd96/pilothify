"""The bash that git runs hooks with, for tests that execute emitted shell."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def git_bash() -> str:
    """Path to bash, or "bash" when none is found.

    On Windows a bare "bash" in subprocess resolves through System32 before
    PATH, which is the WSL launcher and exits 1 without a distro. Git for
    Windows runs hooks with its own MSYS bash, next to git.exe.
    """
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            root = Path(git).resolve().parent.parent
            for candidate in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
                if candidate.is_file():
                    return str(candidate)
    return shutil.which("bash") or "bash"


BASH = git_bash()
