$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -c "import numpy, scipy, fastapi, uvicorn"
if ($LASTEXITCODE -ne 0) { throw 'Install dependencies first: python -m pip install -e ".[dev]"' }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'counterform\web\index.html'))) {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Workbench build failed' }
}
Write-Host 'COUNTERFORM: http://127.0.0.1:8768'
python -m counterform serve --port 8768
