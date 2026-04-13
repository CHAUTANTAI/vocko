# Run from server/: .\run-dev.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Invoke-Step {
    param([string]$Message, [scriptblock]$Action)
    Write-Host $Message -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Invoke-Step '[run-dev] pip install -r requirements.txt' { python -m pip install -r requirements.txt }
Invoke-Step '[run-dev] python src/init_indexes.py' { python src/init_indexes.py }
Invoke-Step '[run-dev] uvicorn src.main:app --reload --host 127.0.0.1 --port 8000' {
    python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
}
