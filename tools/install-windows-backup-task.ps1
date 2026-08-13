param(
    [string] $Time = "03:10",
    [switch] $IncludeEnv
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Root "tools\backup-local.ps1"
$TaskName = "TelegramNewsDashboardDailyBackup"
$Arguments = "-ExecutionPolicy Bypass -File `"$Script`""

if ($IncludeEnv) {
    $Arguments += " -IncludeEnv"
}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Back up Telegram news dashboard database and session files every day." `
    -Force | Out-Null

Write-Host "Installed daily backup task: $TaskName at $Time"
