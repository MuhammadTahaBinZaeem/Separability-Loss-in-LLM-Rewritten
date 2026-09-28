param(
    [Parameter(Mandatory=$true)][string]$Docx,
    [Parameter(Mandatory=$true)][string]$Pdf
)
$ErrorActionPreference = 'Stop'
$paperDocxPath = (Resolve-Path -LiteralPath $Docx).Path
$paperPdfPath = [System.IO.Path]::GetFullPath($Pdf)
$paperWord = New-Object -ComObject Word.Application
$paperWord.Visible = $false
$paperWord.DisplayAlerts = 0
$paperWord.AutomationSecurity = 3
$paperDocument = $null
try {
    $paperDocument = $paperWord.Documents.Open($paperDocxPath, $false, $true)
    $paperDocument.ExportAsFixedFormat($paperPdfPath, 17)
    Write-Output 'Exported the supplied local manuscript through Microsoft Word.'
} finally {
    if ($null -ne $paperDocument) { $paperDocument.Close(0) }
    $paperWord.Quit()
    if ($null -ne $paperDocument) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($paperDocument) }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($paperWord)
}
