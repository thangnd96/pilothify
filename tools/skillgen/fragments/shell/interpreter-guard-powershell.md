```powershell
if (-not (Test-Path pilothify-out\.pilothify_python)) {
    $PILOTHIFY_PYTHON = $null
    $pilothifyCmd = Get-Command pilothify -ErrorAction SilentlyContinue
    if ($pilothifyCmd) {
        # The interpreter that owns the pilothify entry point sits next to it
        # (<env>\Scripts\python.exe for uv tool, pipx, and venv installs).
        $py = Join-Path (Split-Path $pilothifyCmd.Source) "python.exe"
        if (Test-Path $py) { $PILOTHIFY_PYTHON = $py }
    }
    if (-not $PILOTHIFY_PYTHON) { $PILOTHIFY_PYTHON = "python" }
    New-Item -ItemType Directory -Force -Path pilothify-out | Out-Null
    & $PILOTHIFY_PYTHON -c "import sys; open('pilothify-out/.pilothify_python', 'w', encoding='utf-8').write(sys.executable)"
}
```
