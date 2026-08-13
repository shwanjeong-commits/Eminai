param(
    [string] $DropletIp = "167.172.76.143",
    [int] $SshPort = 4174,
    [string] $KeyPath = "$env:USERPROFILE\.ssh\eminai_codex"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$ExportDir = Join-Path $Root ".deploy-package"
$ExportFile = Join-Path $ExportDir "calendar-events.json"
$LocalDb = Join-Path $Root "data\news.db"
$RemoteJson = "/root/calendar-events.json"
$RemoteTool = "/root/calendar_sync.py"
$RemoteProject = "/root/telegram-news-dashboard"
$Container = "telegram-news-dashboard-web-1"

if (-not (Test-Path $KeyPath)) { throw "SSH key not found: $KeyPath" }
if (-not (Test-Path $LocalDb)) { throw "Local database not found: $LocalDb" }

New-Item -ItemType Directory -Force -Path $ExportDir | Out-Null
& $Python "$PSScriptRoot\calendar_sync.py" export $LocalDb $ExportFile
if ($LASTEXITCODE -ne 0) { throw "Calendar export failed" }

$ScpOptions = @("-i", $KeyPath, "-P", "$SshPort", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=20")
$SshOptions = @("-i", $KeyPath, "-p", "$SshPort", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=20")
scp @ScpOptions $ExportFile "root@${DropletIp}:$RemoteJson"
if ($LASTEXITCODE -ne 0) { throw "Calendar upload failed" }
scp @ScpOptions "$PSScriptRoot\calendar_sync.py" "root@${DropletIp}:$RemoteTool"
if ($LASTEXITCODE -ne 0) { throw "Calendar tool upload failed" }

$RemoteCommand = @"
set -eu
cd $RemoteProject
mkdir -p backups
sh deploy/backup-docker.sh || true
docker cp $RemoteJson ${Container}:/tmp/calendar-events.json
docker cp $RemoteTool ${Container}:/tmp/calendar_sync.py
docker exec $Container python /tmp/calendar_sync.py import /app/data/news.db /tmp/calendar-events.json
rm -f $RemoteJson $RemoteTool
curl -fsS http://127.0.0.1:4173/api/auth/status >/dev/null
echo calendar-sync-ok
"@

ssh @SshOptions "root@$DropletIp" $RemoteCommand
if ($LASTEXITCODE -ne 0) { throw "Remote calendar import failed" }
Write-Host "Calendar sync complete: http://${DropletIp}:4173" -ForegroundColor Green
