param(
    [Parameter(Mandatory = $true)]
    [string]$DropletIp
)

$ErrorActionPreference = "Stop"

$remoteCommand = @"
cd /root/telegram-news-dashboard
docker compose -f docker-compose.yml -f docker-compose.ip.yml run --rm web python src/cleanup_noise_queue.py
docker compose -f docker-compose.yml -f docker-compose.ip.yml restart web worker
"@

ssh "root@$DropletIp" $remoteCommand
