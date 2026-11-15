```bash
if [ ! -f pilothify-out/.pilothify_python ]; then
    PILOTHIFY_BIN=$(which pilothify 2>/dev/null)
    if [ -n "$PILOTHIFY_BIN" ]; then
        PYTHON=$(head -1 "$PILOTHIFY_BIN" | tr -d '#!')
        case "$PYTHON" in *[!a-zA-Z0-9/_.@-]*) PYTHON="python3" ;; esac
    else
        PYTHON="python3"
    fi
    mkdir -p pilothify-out
    "$PYTHON" -c "import sys; open('pilothify-out/.pilothify_python', 'w', encoding='utf-8').write(sys.executable)"
fi
```
