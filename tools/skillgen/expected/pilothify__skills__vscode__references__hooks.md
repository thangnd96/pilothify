# pilothify reference: commit hook and native CLAUDE.md integration

Load this when the user asked to install the post-commit hook or wire pilothify into a project's CLAUDE.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
pilothify hook install    # install
pilothify hook uninstall  # remove
pilothify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `/pilothify --update` manually for those.

If a post-commit hook already exists, pilothify appends to it rather than replacing it.

---

## For native CLAUDE.md integration

Run once per project to make pilothify always-on in Claude Code sessions:

```bash
pilothify claude install
```

This writes a `## pilothify` section to the local `CLAUDE.md` that instructs Claude to check the graph before answering codebase questions and rebuild it after code changes. No manual `/pilothify` needed in future sessions.

```bash
pilothify claude uninstall  # remove the section
```

## Source-read freshness

The source-read guard treats a file newer than `graph.json` as potentially stale,
but a checkout can refresh timestamps without changing content. For newer files,
the guard checks the exact project-relative path (or an exact legacy absolute
path) in the configured output directory's extraction manifest. Every populated
AST/semantic hash must match the current content; a matching tier cannot hide a
stale tier. Unchanged content retains the normal graph guidance and strict-mode
first-read deny.

Missing, unreadable, malformed or oversized manifests, unknown paths, and absent
or invalid hashes retain the conservative stale soft nudge. A `needs_update`
marker always softens the guard, even when content matches. Older-mtime files
are not hashed; this is a checkout-timestamp check, not a full freshness audit.
