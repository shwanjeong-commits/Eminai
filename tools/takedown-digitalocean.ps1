param(
    [string] $DropletIp = "167.172.76.143",
    [switch] $PowerOff
)

$ErrorActionPreference = "Stop"

$RemoteDir = "/root/telegram-news-dashboard"
$Compose = "docker compose -f docker-compose.yml -f docker-compose.ip.yml"

Write-Host "Taking down public DigitalOcean dashboard on $DropletIp..."
Write-Host "You may be asked for the root password."

ssh "root@$DropletIp" "cd $RemoteDir && $Compose down"

if ($PowerOff) {
    Write-Host "Powering off droplet. You will need the DigitalOcean panel to turn it back on."
    ssh "root@$DropletIp" "shutdown -h now"
}

Write-Host "Public dashboard containers are stopped."
Write-Host "Check from your PC: http://$DropletIp:4173 should no longer load."
