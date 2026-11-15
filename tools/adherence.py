"""Measure whether agents in a project ask the graph before they grep and read.

Usage: python -m tools.adherence <repo> [--since YYYY-MM-DD] [--transcripts DIR]

Reads the Claude Code transcripts of <repo> (~/.claude/projects/<slug>/, the
subagent files under it included) and counts, per session, graph lookups
(`pilothify query|explain|path`, or the MCP tools) against scouting (Grep,
Glob, Read, and shell grep/find/cat/head/tail/sed). Token figures are tool
result sizes at about 4 characters a token, enough to compare runs. Run it on
sessions from before pilothify for a baseline, then on later ones.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_GRAPH_CMD = re.compile(r"\bpilothify\s+(?:query|explain|path)\b")
_GRAPH_MCP = re.compile(r"^mcp__.*pilothify.*__(?:query_graph|get_node|shortest_path|get_neighbors)$")
_SCOUT_CMD = re.compile(r"(?:^|[|;&(]\s*|\s&&\s*)(?:grep|rg|ag|ack|find|cat|head|tail|sed\s+-n|less|bat)\b")
_SCOUT_TOOLS = {"Grep", "Glob", "Read"}


def transcript_dir(repo: Path) -> Path:
    """Where Claude Code keeps a project's transcripts: its path, non-alphanumerics as '-'."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))


def classify(name: str, tool_input: dict) -> str | None:
    """'graph', 'scout' or None for a tool call."""
    if _GRAPH_MCP.match(name):
        return "graph"
    if name == "Bash":
        command = str(tool_input.get("command") or "")
        if _GRAPH_CMD.search(command):
            return "graph"
        if _SCOUT_CMD.search(command):
            return "scout"
        return None
    return "scout" if name in _SCOUT_TOOLS else None


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def session_stats(path: Path, since: datetime | None = None) -> dict | None:
    """Counts for one transcript, or None when it holds no graph or scouting call."""
    calls: dict[str, str] = {}  # tool_use id -> kind, in call order
    sizes: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        if since is not None:
            try:
                stamp = datetime.fromisoformat(str(rec.get("timestamp", "")).replace("Z", "+00:00"))
            except ValueError:
                stamp = None
            if stamp is None or stamp < since:
                continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                kind = classify(str(block.get("name", "")), block.get("input") or {})
                if kind:
                    calls[str(block.get("id"))] = kind
            elif block.get("type") == "tool_result":
                sizes[str(block.get("tool_use_id"))] = len(_result_text(block.get("content")))
    if not calls:
        return None
    stats = {"graph": 0, "scout": 0, "graph_tokens": 0, "scout_tokens": 0,
             "first": next(iter(calls.values()))}
    for call_id, kind in calls.items():
        stats[kind] += 1
        stats[f"{kind}_tokens"] += sizes.get(call_id, 0) // 4
    return stats


def report(directory: Path, since: datetime | None = None) -> dict:
    sessions = [s for p in sorted(directory.rglob("*.jsonl")) if (s := session_stats(p, since))]
    total = {"sessions": len(sessions),
             "used_graph": sum(1 for s in sessions if s["graph"]),
             "graph_first": sum(1 for s in sessions if s["first"] == "graph")}
    for key in ("graph", "scout", "graph_tokens", "scout_tokens"):
        total[key] = sum(s[key] for s in sessions)
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.adherence")
    ap.add_argument("repo", type=Path)
    ap.add_argument("--since", help="only count calls on or after this date (YYYY-MM-DD)")
    ap.add_argument("--transcripts", type=Path, help="transcript directory, if not the default")
    args = ap.parse_args(argv)
    since = (datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
             if args.since else None)
    directory = args.transcripts or transcript_dir(args.repo)
    if not directory.is_dir():
        print(f"no transcripts at {directory}", file=sys.stderr)
        return 1
    t = report(directory, since)
    print(f"sessions with lookups:   {t['sessions']}")
    print(f"  asked the graph:       {t['used_graph']}")
    print(f"  asked the graph first: {t['graph_first']}")
    print(f"graph lookups:           {t['graph']} (~{t['graph_tokens']:,} result tokens)")
    print(f"grep/glob/read calls:    {t['scout']} (~{t['scout_tokens']:,} result tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
