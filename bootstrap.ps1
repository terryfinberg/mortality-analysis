# Bootstrap for Windows / PowerShell
#
# If Windows refuses to run this script, the one-time fix is:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# Then re-run:  .\bootstrap.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== A Fragile Equilibrium: environment bootstrap ===" -ForegroundColor Cyan

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python not found on PATH. Install Python 3.10+ and re-run." }

$ver = & $py.Source -c "import sys; print('.'.join(map(str,sys.version_info[:2])))"
Write-Host "Python $ver at $($py.Source)"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $py.Source -m venv .venv
} else {
    Write-Host "Reusing existing .venv"
}

$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $vpy -m pip install --upgrade pip --quiet
& $vpy -m pip install -r requirements.txt --quiet

Write-Host "Registering Jupyter kernel..." -ForegroundColor Yellow
& $vpy -m ipykernel install --user --name fragile-equilibrium `
    --display-name "Python (fragile-equilibrium)" | Out-Null

Write-Host "Running tests..." -ForegroundColor Yellow
& $vpy -m pytest -q

Write-Host ""
Write-Host "=== Bootstrap complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "The data files in data\raw\ are empty by design." -ForegroundColor Yellow
Write-Host "Populate them from data\queries\cdc_wonder_queries.md, then run:"
Write-Host "    .venv\Scripts\python.exe -m src.report"
Write-Host ""
Write-Host "See UAT_CHECKLIST.md for the step-by-step path."
