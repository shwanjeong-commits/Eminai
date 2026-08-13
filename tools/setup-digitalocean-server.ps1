param(
    [Parameter(Mandatory = $true)]
    [string] $DropletIp
)

$ErrorActionPreference = "Stop"

Write-Host "Connecting to root@$DropletIp"
Write-Host "Enter the Droplet password when SSH asks."

ssh "root@$DropletIp" "curl -fsSL https://get.docker.com | sh && apt-get update && apt-get install -y docker-compose-plugin git"

Write-Host "Server setup complete."
