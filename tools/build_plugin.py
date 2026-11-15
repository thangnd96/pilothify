"""Copy the Claude Code skill into the plugin bundle, or check that it is current.

Usage: python -m tools.build_plugin [--check]

The plugin (.claude-plugin/) serves plugin/skills/pilothify/: SKILL.md is
pilothify/skill.md and references/ is pilothify/skills/claude/references/, so
installing the plugin gives the same skill `pilothify install` writes. Run after
`python -m tools.skillgen`; CI runs --check.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "plugin" / "skills" / "pilothify"
SOURCES = {
    "SKILL.md": ROOT / "pilothify" / "skill.md",
    **{
        f"references/{p.name}": p
        for p in sorted((ROOT / "pilothify" / "skills" / "claude" / "references").glob("*.md"))
    },
}


def stale() -> list[str]:
    """Bundle paths that differ from their source, are missing, or have no source."""
    out = [rel for rel, src in SOURCES.items()
           if not (BUNDLE / rel).is_file() or (BUNDLE / rel).read_bytes() != src.read_bytes()]
    extra = [p.relative_to(BUNDLE).as_posix() for p in BUNDLE.rglob("*")
             if p.is_file() and p.relative_to(BUNDLE).as_posix() not in SOURCES] if BUNDLE.exists() else []
    return out + extra


def build() -> None:
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    for rel, src in SOURCES.items():
        dst = BUNDLE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def main(argv: list[str]) -> int:
    if "--check" in argv:
        bad = stale()
        if bad:
            print("plugin bundle is stale, run `python -m tools.build_plugin`: " + ", ".join(bad))
            return 1
        print(f"plugin bundle OK: {len(SOURCES)} file(s) match their sources.")
        return 0
    build()
    print(f"wrote {len(SOURCES)} file(s) to {BUNDLE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
