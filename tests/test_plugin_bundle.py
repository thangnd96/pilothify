"""The Claude Code plugin ships the same skill `pilothify install` writes, at one version."""
import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from tools import build_plugin

ROOT = Path(__file__).resolve().parent.parent


def test_plugin_bundle_matches_the_generated_skill():
    assert build_plugin.stale() == [], "run `python -m tools.build_plugin` after tools.skillgen"


def test_plugin_marketplace_and_package_versions_agree():
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    listed = [p for p in market["plugins"] if p["name"] == "pilothify"]
    assert plugin["version"] == package
    assert [p["version"] for p in listed] == [package]


def test_plugin_points_at_a_skill_named_pilothify():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    skill = ROOT / plugin["skills"] / "pilothify" / "SKILL.md"
    assert skill.read_text(encoding="utf-8").startswith("---\nname: pilothify\n")
