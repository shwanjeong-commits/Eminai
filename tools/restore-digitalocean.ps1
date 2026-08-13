param(
    [string] $DropletIp = "167.172.76.143"
)

$ErrorActionPreference = "Stop"

$RemoteDir = "/root/telegram-news-dashboard"
$Compose = "docker compose -f docker-compose.yml -f docker-compose.ip.yml"

Write-Host "Restoring public DigitalOcean dashboard on $DropletIp..."
Write-Host "You may be asked for the root password."

ssh "root@$DropletIp" "cd $RemoteDir && $Compose up -d"

Write-Host "Public dashboard containers are starting."
Write-Host "Dashboard: http://$DropletIp:4173"
