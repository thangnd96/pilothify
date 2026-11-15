# pilothify reference: GitHub clone and cross-repo merge

Load this when the user passed one or more `https://github.com/...` URLs, or named several local subfolders to merge into one graph.

### Step 0 - Clone GitHub repo(s) (only if a GitHub URL was given)

**Single repo:**
```bash
LOCAL_PATH=$(pilothify clone <github-url> [--branch <branch>])
# Use LOCAL_PATH as the target for all subsequent steps
```

**Multiple repos (cross-repo graph):**
```bash
# Clone each repo, run the full pipeline on each, then merge
pilothify clone <url1>   # → ~/.pilothify/repos/<owner1>/<repo1>
pilothify clone <url2>   # → ~/.pilothify/repos/<owner2>/<repo2>
# Run /pilothify on each local path to produce their graph.json files
# Then merge:
pilothify merge-graphs \
  ~/.pilothify/repos/<owner1>/<repo1>/pilothify-out/graph.json \
  ~/.pilothify/repos/<owner2>/<repo2>/pilothify-out/graph.json \
  --out pilothify-out/cross-repo-graph.json
```

Pilothify clones into `~/.pilothify/repos/<owner>/<repo>` and reuses existing clones on repeat runs. Each node in the merged graph carries a `repo` attribute so you can filter by origin.

**Multiple local subfolders (monorepo or multi-service layout):**

The skill pipeline writes all intermediate and final outputs to `pilothify-out/` in the current working directory. Running the skill on each subfolder separately will clobber the same output dir. Instead, use the CLI directly for each subfolder — it places `pilothify-out/` *inside* the scanned path:

```bash
pilothify extract ./core/     # → ./core/pilothify-out/graph.json
pilothify extract ./service/  # → ./service/pilothify-out/graph.json
pilothify extract ./platform/ # → ./platform/pilothify-out/graph.json
# Add --backend gemini|kimi|openai|deepseek|claude-cli depending on which API key you have set

# Then merge at the project root:
pilothify merge-graphs \
  ./core/pilothify-out/graph.json \
  ./service/pilothify-out/graph.json \
  ./platform/pilothify-out/graph.json \
  --out pilothify-out/graph.json
```

Once `pilothify-out/graph.json` exists, the fast path above takes over: any codebase question runs `pilothify query` directly on the merged graph — no re-extraction, no size gate.
