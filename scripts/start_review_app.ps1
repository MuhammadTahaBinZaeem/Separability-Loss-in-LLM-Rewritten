param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$ReviewProjectRoot = Split-Path -Parent $PSScriptRoot
$ReviewPython = Join-Path $ReviewProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ReviewPython)) {
    throw 'The research Python environment is missing. Follow revision/REPRODUCE.md first.'
}
Push-Location -LiteralPath $ReviewProjectRoot
try {
    & $ReviewPython -m research_v2.review_app serve --port $Port --open
} finally {
    Pop-Location
}
