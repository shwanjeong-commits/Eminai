param(
    [Parameter(Mandatory = $true)]
    [string] $DropletIp
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$LocalDb = Join-Path $Root "data\news.db"
$TempDir = Join-Path $Root ".deploy-package"
$TempDb = Join-Path $TempDir "news.db"
$RemoteDb = "/root/news.db.upload"
$RemoteProject = "/root/telegram-news-dashboard"
$Compose = "docker compose -f docker-compose.yml -f docker-compose.ip.yml"
$VolumeName = "telegram-news-dashboard_news-data"

if (-not (Test-Path $LocalDb)) {
    throw "Local database not found: $LocalDb"
}

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
if (Test-Path $TempDb) {
    Remove-Item -LiteralPath $TempDb -Force
}

Write-Host "Creating safe SQLite copy..."
& $Python -c "import sqlite3, sys; src, dst = sys.argv[1], sys.argv[2]; source = sqlite3.connect(src); target = sqlite3.connect(dst); source.backup(target); target.close(); source.close()" $LocalDb $TempDb

Write-Host "Uploading database to root@$DropletIp..."
scp $TempDb "root@${DropletIp}:$RemoteDb"

$RemoteCommand = @"
set -eu
cd $RemoteProject
mkdir -p backups
echo 'Stopping containers...'
$Compose stop web worker
echo 'Backing up current server Docker volume...'
sh deploy/backup-docker.sh || true
echo 'Replacing /app/data/news.db in Docker volume...'
docker run --rm -v ${VolumeName}:/data -v ${RemoteDb}:/upload/news.db:ro alpine sh -c 'cp /upload/news.db /data/news.db && chmod 644 /data/news.db'
rm -f $RemoteDb
echo 'Restarting containers...'
$Compose up -d
echo 'Server DB restore complete.'
"@

Write-Host "Restoring database on server..."
ssh "root@$DropletIp" $RemoteCommand

Write-Host "Done. Open: http://$DropletIp:4173"
