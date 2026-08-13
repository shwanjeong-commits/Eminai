param(
    [Parameter(Mandatory = $true)]
    [string] $DropletIp,
    [int] $SshPort = 22,
    [string] $KeyPath = "$env:USERPROFILE\.ssh\eminai_codex",
    [switch] $UploadEnv,
    [switch] $Restart
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PackageDir = Join-Path $Root ".deploy-package"
$Archive = Join-Path $Root "telegram-news-dashboard.tar.gz"
$RemoteDir = "/root/telegram-news-dashboard"
$DeploymentId = Get-Date -Format "yyyyMMddHHmmssfff"
$RemoteArchive = "/root/telegram-news-dashboard-$DeploymentId.tar.gz"

function Assert-NativeCommandSucceeded([string] $Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

Set-Location $Root

if (Test-Path $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}

New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null

$Items = @(
    "app",
    "deploy",
    "src",
    "tools",
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "BACKUP.md",
    "DEPLOY.md",
    "DIGITALOCEAN_DROPLET_SETUP.md",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.ip.yml",
    "GITHUB_EDUCATION_DEPLOY.md",
    "LOCAL_AUTOMATION.md",
    "ORACLE_ALWAYS_FREE_DEPLOY.md",
    "Procfile",
    "PROJECT_MEMORY.md",
    "README.md",
    "requirements.txt",
    "runtime.txt"
)

foreach ($Item in $Items) {
    $Source = Join-Path $Root $Item
    if (Test-Path $Source) {
        Copy-Item -LiteralPath $Source -Destination $PackageDir -Recurse -Force
    }
}

if ($UploadEnv) {
    $EnvPath = Join-Path $Root ".env"
    if (Test-Path $EnvPath) {
        Copy-Item -LiteralPath $EnvPath -Destination (Join-Path $PackageDir ".env") -Force
    }
}

tar -czf $Archive -C $PackageDir .
Assert-NativeCommandSucceeded "Package creation"

Write-Host "Package created: $Archive"
Write-Host "Uploading to root@${DropletIp}:$RemoteArchive..."
$UploadSucceeded = $false
for ($UploadAttempt = 1; $UploadAttempt -le 3; $UploadAttempt++) {
    Write-Host "Upload attempt $UploadAttempt of 3..." -ForegroundColor Cyan
    scp -i $KeyPath -P $SshPort -o BatchMode=yes -o ConnectTimeout=20 -o ConnectionAttempts=2 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 $Archive "root@${DropletIp}:$RemoteArchive"
    if ($LASTEXITCODE -eq 0) {
        $UploadSucceeded = $true
        break
    }
    if ($UploadAttempt -lt 3) {
        Write-Host "Connection was interrupted. Retrying in 3 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
}
if (-not $UploadSucceeded) {
    throw "Upload failed after 3 attempts."
}

if ($Restart) {
    Write-Host "Extracting package, rebuilding, and restarting in one connection..."
    $RemoteCommand = "test -s $RemoteArchive && mkdir -p $RemoteDir && if [ -f $RemoteDir/.env ] && [ '$UploadEnv' != 'True' ]; then cp $RemoteDir/.env $RemoteDir/.env.deploy-backup; fi && tar xzf $RemoteArchive -C $RemoteDir && if [ -f $RemoteDir/.env.deploy-backup ] && [ '$UploadEnv' != 'True' ]; then mv $RemoteDir/.env.deploy-backup $RemoteDir/.env; chmod 600 $RemoteDir/.env; fi && cd $RemoteDir && docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build --remove-orphans && rm -f $RemoteArchive"
    ssh -i $KeyPath -p $SshPort -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "root@$DropletIp" $RemoteCommand
    Assert-NativeCommandSucceeded "Server extraction and Docker rebuild"
}
else {
    Write-Host "Preparing server directory..."
    $RemoteCommand = "test -s $RemoteArchive && mkdir -p $RemoteDir && if [ -f $RemoteDir/.env ] && [ '$UploadEnv' != 'True' ]; then cp $RemoteDir/.env $RemoteDir/.env.deploy-backup; fi && tar xzf $RemoteArchive -C $RemoteDir && if [ -f $RemoteDir/.env.deploy-backup ] && [ '$UploadEnv' != 'True' ]; then mv $RemoteDir/.env.deploy-backup $RemoteDir/.env; chmod 600 $RemoteDir/.env; fi && rm -f $RemoteArchive"
    ssh -i $KeyPath -p $SshPort -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "root@$DropletIp" $RemoteCommand
    Assert-NativeCommandSucceeded "Server extraction"
}

Write-Host "Done."
if (-not $Restart) {
    Write-Host "Next SSH command:"
    Write-Host "ssh -i $KeyPath -p $SshPort root@$DropletIp"
    Write-Host "Then run:"
    Write-Host "cd $RemoteDir"
    Write-Host "cp .env.example .env    # skip this if you used -UploadEnv"
    Write-Host "nano .env"
    Write-Host "docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build"
}
