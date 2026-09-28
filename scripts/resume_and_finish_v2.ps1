param([string]$EnvFile = 'C:\Users\Empty\Documents\Paper-secrets\api.env')
$ErrorActionPreference = 'Stop'
$paperRoot = Split-Path -Parent $PSScriptRoot
Push-Location $paperRoot
try {
    $paperPython = Join-Path $paperRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'External credential file is missing.' }
    $paperLock = Join-Path $paperRoot 'revision\generation\gem31lite\RUNNING.lock'
    if (Test-Path -LiteralPath $paperLock) { throw 'A generator lock exists. Inspect its owner; do not start a second writer.' }
    $paperStop = Join-Path $paperRoot 'revision\generation\gem31lite\STOP_AFTER_CURRENT'
    # Remove only the exact stop marker produced by this workflow, never a tree.
    if (Test-Path -LiteralPath $paperStop) { Remove-Item -LiteralPath $paperStop }
    & $paperPython -m research_v2.parallel_generation --model gem31lite --env-file $EnvFile --workers 1 --interval-seconds 10 --minutes 90
    $paperGenerationExit = $LASTEXITCODE
    # Always rebuild truthful available evidence. Partial work never becomes final.
    & $paperPython -m research_v2.reproduce --allow-partial
    $paperAnalysisExit = $LASTEXITCODE
    $paperArtifactPython = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $paperArtifactPython) {
        & $paperArtifactPython scripts/build_manuscript_docx.py revision/paper_assets/manuscript_REVIEW_DRAFT.md revision/paper_assets/manuscript_REVIEW_DRAFT.docx
        if ($LASTEXITCODE -ne 0) { throw 'Word reading-copy build failed.' }
        & (Join-Path $PSScriptRoot 'export_manuscript_pdf.ps1') -Docx revision/paper_assets/manuscript_REVIEW_DRAFT.docx -Pdf revision/paper_assets/manuscript_REVIEW_DRAFT.pdf
        Write-Output 'Reading copies rebuilt; new page images still require visual review. Prior visual QA does not certify this rebuild.'
    }
    # Refresh the artifact hashes after rebuilding reading copies.
    & $paperPython -m research_v2.paper_assets
    if ($LASTEXITCODE -ne 0) { throw 'Paper evidence binding failed.' }
    & $paperPython -m research_v2.archive --env-file $EnvFile
    if ($LASTEXITCODE -ne 0) { throw 'Review packaging failed; inspect diagnostics.' }
    if ($paperGenerationExit -ne 0 -or $paperAnalysisExit -ne 0) {
        Write-Output 'The checkpoint is preserved, but full computational completion is still blocked. See revision/readiness.json.'
        exit 2
    }
    Write-Output 'Computational evidence rebuilt. Genuine human reviews and investigator/archive decisions remain required.'
} finally {
    Pop-Location
}
