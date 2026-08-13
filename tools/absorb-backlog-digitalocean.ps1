param(
    [Parameter(Mandatory = $true)]
    [string] $DropletIp
)

$ErrorActionPreference = "Stop"

$RemoteProject = "/root/telegram-news-dashboard"
$Compose = "docker compose -f docker-compose.yml -f docker-compose.ip.yml"

Write-Host "Absorbing queued backlog on root@$DropletIp..."
ssh "root@$DropletIp" "cd $RemoteProject && $Compose run --rm web python src/absorb_backlog_context.py && $Compose restart web worker"
Write-Host "Done. Open: http://$DropletIp:4173"
