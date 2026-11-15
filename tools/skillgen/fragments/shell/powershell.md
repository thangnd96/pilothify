```powershell
New-Item -ItemType Directory -Force -Path pilothify-out | Out-Null
$PILOTHIFY_PYTHON = $null

function Find-PilothifyPython {
    # 1. uv tool install ('uv tool dir' respects UV_TOOL_DIR)
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvDir = (uv tool dir 2>$null).Trim()
        if ($uvDir) {
            $py = Join-Path $uvDir "pilothify\Scripts\python.exe"
            if (Test-Path $py) {
                & $py -c "import pilothify" 2>$null
                if ($LASTEXITCODE -eq 0) { return $py }
            }
        }
    }
    # 2. pipx install (respects PIPX_HOME)
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        $venvs = (pipx environment --value PIPX_LOCAL_VENVS 2>$null).Trim()
        if ($venvs) {
            $py = Join-Path $venvs "pilothify\Scripts\python.exe"
            if (Test-Path $py) {
                & $py -c "import pilothify" 2>$null
                if ($LASTEXITCODE -eq 0) { return $py }
            }
        }
    }
    # 3. Active venv / conda / pip-into-current-env
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        & $pyCmd.Source -c "import pilothify" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return (& $pyCmd.Source -c "import sys; print(sys.executable)").Trim()
        }
    }
    return $null
}

$PILOTHIFY_PYTHON = Find-PilothifyPython

# Not found: install from the repo, not PyPI, then re-detect
if (-not $PILOTHIFY_PYTHON) {
    $src = "pilothify @ git+https://github.com/thangnd96/pilothify"
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv tool install --upgrade $src -q 2>&1 | Select-Object -Last 3
    } else {
        pip install $src -q 2>&1 | Select-Object -Last 3
    }
    $PILOTHIFY_PYTHON = Find-PilothifyPython
}

# Save interpreter path — all subsequent steps read this.
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $PWD 'pilothify-out\.pilothify_python'), [string]$PILOTHIFY_PYTHON, $Utf8NoBom)
# Save scan root so `pilothify update` (no args) knows where to look next time.
# INPUT_PATH goes through a literal here-string, so a path holding `;`, `|`
# or `$(...)` can never run as code.
$InputPathRaw = @'
INPUT_PATH
'@
[System.IO.File]::WriteAllText((Join-Path $PWD 'pilothify-out\.pilothify_root'), (Resolve-Path $InputPathRaw.Trim()).Path, $Utf8NoBom)
```

If the import succeeds, print nothing and move straight to Step 2.

**In every subsequent block, run Python through the saved interpreter — `& (Get-Content pilothify-out\.pilothify_python)` in place of a bare `python3` — so every step uses the interpreter that actually has pilothify.**
