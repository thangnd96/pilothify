## pilothify

This repository is pilothify itself.

- Run the tests with `.venv/bin/python -m pytest tests/ -q -n 8`.
- The skill files under `pilothify/` are generated: edit `tools/skillgen/fragments/`, then run `python -m tools.skillgen` and `python -m tools.skillgen --bless`.
- When the task is about the graph's own correctness, do not use a graph built by pilothify as evidence.
