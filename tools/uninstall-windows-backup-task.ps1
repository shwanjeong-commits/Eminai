$ErrorActionPreference = "Stop"

$TaskName = "TelegramNewsDashboardDailyBackup"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed backup task: $TaskName"
