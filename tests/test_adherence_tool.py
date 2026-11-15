"""tools/adherence.py counts graph lookups against grep/read in Claude Code transcripts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.adherence import classify, report, transcript_dir


def _call(i: int, name: str, tool_input: dict, result: str, stamp: str = "2026-11-15T10:00:00Z") -> list[dict]:
    return [
        {"type": "assistant", "timestamp": stamp,
         "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": tool_input}]}},
        {"type": "user", "timestamp": stamp,
         "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": result}]}},
    ]


def _write(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_classify():
    assert classify("Bash", {"command": 'pilothify query "spin wallet"'}) == "graph"
    assert classify("Bash", {"command": '$(cat pilothify-out/.pilothify_python) -m pilothify explain "X"'}) == "graph"
    assert classify("Bash", {"command": '$(cat pilothify-out/.pilothify_python) -P -m pilothify explain "X"'}) == "graph"
    assert classify("mcp__pilothify__query_graph", {}) == "graph"
    assert classify("Bash", {"command": "rg -n wallet src/"}) == "scout"
    assert classify("Bash", {"command": "cd api && grep -rn Spin ."}) == "scout"
    assert classify("Grep", {"pattern": "x"}) == "scout"
    assert classify("Read", {"file_path": "a.py"}) == "scout"
    assert classify("Bash", {"command": "pilothify update ."}) is None
    assert classify("Edit", {}) is None
    # the skill's own interpreter form is not a `cat`
    assert classify("Bash", {"command": "$(cat pilothify-out/.pilothify_python) -m pilothify update ."}) is None
    assert classify("Bash", {"command": "cd api\ngrep -rn Spin ."}) == "scout"
    assert classify("Bash", {"command": 'grep -rn "pilothify query" docs/'}) == "scout"


def test_report_counts_sessions_first_lookups_and_tokens(tmp_path):
    _write(tmp_path / "a.jsonl",
           _call(1, "Bash", {"command": 'pilothify query "wallet"'}, "x" * 400)
           + _call(2, "Read", {"file_path": "w.py"}, "y" * 4000))
    _write(tmp_path / "b.jsonl", _call(3, "Grep", {"pattern": "wallet"}, "z" * 800))
    _write(tmp_path / "c.jsonl", _call(4, "Edit", {}, "ok"))
    t = report(tmp_path)
    assert t == {"sessions": 2, "used_graph": 1, "graph_first": 1, "graph": 1, "scout": 2,
                 "graph_tokens": 100, "scout_tokens": 1200}


def test_since_drops_earlier_calls(tmp_path):
    _write(tmp_path / "a.jsonl",
           _call(1, "Grep", {"pattern": "x"}, "old", stamp="2026-11-10T10:00:00Z")
           + _call(2, "Bash", {"command": 'pilothify path "A" "B"'}, "new"))
    t = report(tmp_path, since=datetime(2026, 11, 14, tzinfo=timezone.utc))
    assert (t["sessions"], t["graph"], t["scout"]) == (1, 1, 0)


def test_transcript_dir_uses_claude_code_slug(tmp_path):
    assert transcript_dir(tmp_path).name == "".join(c if c.isalnum() else "-" for c in str(tmp_path.resolve()))
