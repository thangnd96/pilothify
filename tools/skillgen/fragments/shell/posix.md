```bash
# Detect the correct Python interpreter (handles uv tool, pipx, venv, system installs)
PYTHON=""
PILOTHIFY_BIN=$(which pilothify 2>/dev/null)
# 1. uv tool install (read its dir; `uv tool run --from` would fetch from PyPI)
_UV_PY="$(uv tool dir 2>/dev/null)/pilothify/bin/python"
[ -x "$_UV_PY" ] && PYTHON="$_UV_PY"
# 2. Read shebang from pilothify binary (pipx and direct pip installs)
if [ -z "$PYTHON" ] && [ -n "$PILOTHIFY_BIN" ]; then
    _SHEBANG=$(head -1 "$PILOTHIFY_BIN" | tr -d '#!')
    case "$_SHEBANG" in
        *[!a-zA-Z0-9/_.@-]*) ;;
        *) "$_SHEBANG" -c "import pilothify" 2>/dev/null && PYTHON="$_SHEBANG" ;;
    esac
fi
# 3. Fall back to python3
if [ -z "$PYTHON" ]; then PYTHON="python3"; fi
if ! "$PYTHON" -c "import pilothify" 2>/dev/null; then
    # From the repo: the name is not ours on PyPI
    SRC="pilothify @ git+https://github.com/thangnd96/pilothify"
    if command -v uv >/dev/null 2>&1; then
        uv tool install --upgrade "$SRC" -q 2>&1 | tail -3
        PYTHON="$(uv tool dir)/pilothify/bin/python"
    else
        "$PYTHON" -m pip install "$SRC" -q 2>/dev/null \
          || "$PYTHON" -m pip install "$SRC" -q --break-system-packages 2>&1 | tail -3
    fi
fi
# Write interpreter path for all subsequent steps (persists across invocations)
mkdir -p pilothify-out
"$PYTHON" -c "import sys; open('pilothify-out/.pilothify_python', 'w', encoding='utf-8').write(sys.executable)"
# Save scan root so `pilothify update` (no args) knows where to look next time.
"$PYTHON" -c "import os, sys; out_path = os.path.abspath('pilothify-out/.pilothify_root'); os.chdir(sys.stdin.readline().rstrip('\n')); open(out_path, 'w', encoding='utf-8').write(os.getcwd())" <<'PILOTHIFY_ROOT_EOF'
INPUT_PATH
PILOTHIFY_ROOT_EOF
```

If the import succeeds, print nothing and move straight to Step 2.

**In every subsequent bash block, replace `python3` with `$(cat pilothify-out/.pilothify_python)` to use the correct interpreter.**
