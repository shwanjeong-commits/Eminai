param(
    [switch] $IncludeEnv,
    [int] $Keep = 14
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackupRoot = Join-Path $Root "backups"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot $Stamp
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$DbPath = Join-Path $Root "data\news.db"
$DbBackupPath = Join-Path $BackupDir "news.db"

if (Test-Path $DbPath) {
    & $Python -c "import sqlite3, sys; src, dst = sys.argv[1], sys.argv[2]; source = sqlite3.connect(src); target = sqlite3.connect(dst); source.backup(target); target.close(); source.close()" $DbPath $DbBackupPath
}

$SessionFiles = Get-ChildItem -Path $Root -Filter "*.session*" -File -ErrorAction SilentlyContinue
foreach ($File in $SessionFiles) {
    Copy-Item -LiteralPath $File.FullName -Destination (Join-Path $BackupDir $File.Name) -Force
}

if ($IncludeEnv) {
    $EnvPath = Join-Path $Root ".env"
    if (Test-Path $EnvPath) {
        Copy-Item -LiteralPath $EnvPath -Destination (Join-Path $BackupDir ".env") -Force
    }
}

$Manifest = @{
    createdAt = (Get-Date).ToString("o")
    includeEnv = [bool] $IncludeEnv
    database = (Test-Path $DbBackupPath)
    sessionFiles = @($SessionFiles | ForEach-Object { $_.Name })
} | ConvertTo-Json -Depth 3

Set-Content -Path (Join-Path $BackupDir "manifest.json") -Value $Manifest -Encoding UTF8

$Existing = Get-ChildItem -Path $BackupRoot -Directory | Sort-Object Name -Descending
if ($Existing.Count -gt $Keep) {
    $ToDelete = $Existing | Select-Object -Skip $Keep
    foreach ($Dir in $ToDelete) {
        if ($Dir.FullName.StartsWith((Resolve-Path $BackupRoot).Path)) {
            Remove-Item -LiteralPath $Dir.FullName -Recurse -Force
        }
    }
}

Write-Host "Backup created: $BackupDir"
