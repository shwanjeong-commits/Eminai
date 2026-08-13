$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "EMINAI RESUME DEPLOY"

$dropletIp = "167.172.76.143"
$remoteDir = "/root/telegram-news-dashboard"
$remoteArchive = "/root/telegram-news-dashboard.tar.gz"
$remoteCommand = "mkdir -p $remoteDir && tar xzf $remoteArchive -C $remoteDir && cd $remoteDir && docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build && rm -f $remoteArchive"
$completed = $false

for ($attempt = 1; $attempt -le 3; $attempt++) {
    Write-Host "Resume deployment attempt $attempt of 3..." -ForegroundColor Cyan
    ssh -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "root@$dropletIp" $remoteCommand
    if ($LASTEXITCODE -eq 0) {
        $completed = $true
        break
    }
    if ($attempt -lt 3) {
        Write-Host "Connection was interrupted. Retrying in 2 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $completed) {
    throw "Resume deployment failed after 3 attempts."
}

Write-Host ""
Write-Host "DEPLOY SUCCESS - you can close this window." -ForegroundColor Green
