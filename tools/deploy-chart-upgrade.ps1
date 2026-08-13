$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "EMINAI CHART UPGRADE DEPLOY"

try {
    & "$PSScriptRoot\deploy-digitalocean.ps1" -DropletIp "167.172.76.143" -Restart
    Write-Host ""
    Write-Host "배포 성공 - 이 창을 닫아도 됩니다." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host $_ -ForegroundColor Red
    Write-Host "배포 실패 - 창을 닫지 말고 오류를 알려주세요." -ForegroundColor Yellow
}
