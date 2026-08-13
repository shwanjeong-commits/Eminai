param(
    [int]$Limit = 500,
    [switch]$Requeue,
    [int]$MaxRequeue = 20
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = "python"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $BundledPython) {
    $Python = $BundledPython
}

$argsList = @("src\analysis_quality_audit.py", "--limit", "$Limit", "--max-requeue", "$MaxRequeue")
if ($Requeue) {
    $argsList += "--requeue"
}

& $Python @argsList
