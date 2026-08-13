$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Root "tools\start-local-stack.ps1"
$TaskName = "TelegramNewsDashboardLocalStack"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$Script`""

$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Start the Telegram news dashboard API and worker after Windows logon." `
    -Force | Out-Null

Write-Host "Installed startup task: $TaskName"
Write-Host "It will start at Windows logon."
