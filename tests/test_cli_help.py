"""`pilothify --help` must list user-facing commands that dispatch_command implements.

The top-level listing in pilothify/__main__.py is hand-maintained and
drifted from dispatch_command() — prs, provider, and 7 of 8 export formats
never appeared. Precedent: one usage line plus a stdout assert.
"""
from __future__ import annotations

import subprocess
import sys

PYTHON = sys.executable


def test_help_lists_prs_provider_and_export_formats():
    """`pilothify --help` must advertise prs, provider, and all export formats."""
    r = subprocess.run(
        [PYTHON, "-m", "pilothify", "--help"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"--help should exit 0: {r.stderr}"
    out = r.stdout
    assert "  prs" in out, "`pilothify --help` must list prs (#3140)"
    assert "provider" in out, "`pilothify --help` must list provider (#3140)"
    for fmt in (
        "html",
        "callflow-html",
        "obsidian",
        "wiki",
        "svg",
        "graphml",
        "neo4j",
        "falkordb",
    ):
        assert f"export {fmt}" in out, (
            f"`pilothify --help` must list export {fmt} (#3140)"
        )
    # Silent hook internals — deliberately excluded from user-facing help.
    assert "hook-check" not in out
    assert "hook-guard" not in out


def test_help_lists_every_install_platform():
    """The `install [--platform P]` line must advertise every accepted
    `--platform` value. It is derived from the same source as `pilothify install`
    usage (`[*_PLATFORM_CONFIG, "gemini", "cursor"]`), so this guards against the
    list silently drifting again (amp, copilot, kilo, kimi, antigravity-windows
    had all gone missing)."""
    import re

    from pilothify.install import _PLATFORM_CONFIG

    r = subprocess.run(
        [PYTHON, "-m", "pilothify", "--help"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"--help should exit 0: {r.stderr}"
    m = re.search(r"install \[--platform P\][^(]*\(([^)]*)\)", r.stdout)
    assert m, "could not find the install --platform list in `pilothify --help`"
    listed = set(m.group(1).split("|"))
    for platform_name in [*_PLATFORM_CONFIG, "gemini", "cursor"]:
        assert platform_name in listed, (
            f"`pilothify --help` must list the --platform value {platform_name!r} (#4655)"
        )


def test_help_lists_project_query_defaults_and_depth_range():
    result = subprocess.run([PYTHON, "-m", "pilothify", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--budget N, --budget=N" in result.stdout
    assert "--depth N, --depth=N" in result.stdout
    assert "1-6 (default 2)" in result.stdout
    assert "tokens (default 2000)" in result.stdout
    assert "query_budget" in result.stdout and "query_depth" in result.stdout
    assert "selected graph project's .pilothifyrc" in result.stdout
    assert "Explicit options override project values" in result.stdout
