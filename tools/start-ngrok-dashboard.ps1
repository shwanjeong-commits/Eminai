$ErrorActionPreference = "Stop"

param(
    [int] $Port = 4173
)

$Root = Split-Path -Parent $PSScriptRoot
$LocalUrl = "http://127.0.0.1:$Port"

Set-Location $Root

Write-Host "Starting local dashboard stack..."
& (Join-Path $Root "tools\start-local-stack.ps1")

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
    Write-Host ""
    Write-Host "ngrok is not installed or not in PATH."
    Write-Host "Install it from https://ngrok.com/download, then run:"
    Write-Host "  ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN"
    Write-Host "  ngrok http $Port"
    Write-Host ""
    Write-Host "Local dashboard is still available at $LocalUrl"
    exit 1
}

Write-Host ""
Write-Host "Opening ngrok tunnel for $LocalUrl"
Write-Host "Share the https://*.ngrok-free.app URL shown by ngrok."
Write-Host "Close this ngrok window to stop sharing."

Start-Process `
    -WindowStyle Normal `
    -FilePath $ngrok.Source `
    -WorkingDirectory $Root `
    -ArgumentList @("http", "$Port")

Write-Host "Local dashboard: $LocalUrl"
