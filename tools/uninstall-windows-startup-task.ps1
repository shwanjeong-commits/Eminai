$ErrorActionPreference = "Stop"

$TaskName = "TelegramNewsDashboardLocalStack"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed startup task: $TaskName"
