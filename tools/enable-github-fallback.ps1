param(
    [string] $DropletIp = "167.172.76.143",
    [int] $SshPort = 4174,
    [string] $KeyPath = "$env:USERPROFILE\.ssh\eminai_codex",
    [string] $Model = "meta/llama-3.3-70b-instruct"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root ".env"

function Set-EnvValue {
    param([string[]] $Lines, [string] $Name, [string] $Value)

    $replacement = "$Name=$Value"
    $found = $false
    $updated = foreach ($line in $Lines) {
        if ($line -match "^$([regex]::Escape($Name))=") {
            $found = $true
            $replacement
        }
        else {
            $line
        }
    }
    if (-not $found) {
        $updated += $replacement
    }
    return [string[]] $updated
}

Write-Host "GitHub Models fallback setup" -ForegroundColor Cyan
Write-Host "A fine-grained GitHub token with Models: Read permission is required."
$secureToken = Read-Host "Paste the token here (input is hidden)" -AsSecureString
$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)

try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr).Trim()
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "No token was entered."
    }

    Write-Host "Checking GitHub token validity..." -ForegroundColor Cyan
    $headers = @{
        Accept = "application/vnd.github+json"
        Authorization = "Bearer $token"
        "X-GitHub-Api-Version" = "2026-03-10"
    }
    $identity = Invoke-RestMethod -Method Get `
        -Uri "https://api.github.com/user" `
        -Headers $headers `
        -TimeoutSec 30
    Write-Host "GitHub token: OK ($($identity.login))" -ForegroundColor Green

    Write-Host "Testing GitHub Models access..." -ForegroundColor Cyan
    $body = @{
        model = $Model
        messages = @(@{ role = "user"; content = "Reply with OK only." })
        max_tokens = 8
    } | ConvertTo-Json -Depth 5
    $null = Invoke-RestMethod -Method Post `
        -Uri "https://models.github.ai/inference/chat/completions" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 30
    Write-Host "GitHub Models connection: OK" -ForegroundColor Green

    $lines = if (Test-Path -LiteralPath $EnvPath) { @(Get-Content -LiteralPath $EnvPath) } else { @() }
    $lines = Set-EnvValue $lines "AI_FALLBACK_PROVIDERS" "github"
    $lines = Set-EnvValue $lines "GITHUB_MODELS_MODEL" $Model
    $lines = Set-EnvValue $lines "GITHUB_MODELS_TOKEN" $token
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllLines($EnvPath, $lines, $utf8NoBom)
    Write-Host "Local fallback settings saved." -ForegroundColor Green

    Write-Host "Merging fallback settings and restarting analyzer..." -ForegroundColor Cyan
    $patchPath = New-TemporaryFile
    try {
        [IO.File]::WriteAllLines(
            $patchPath,
            @(
                "AI_FALLBACK_PROVIDERS=github",
                "GITHUB_MODELS_MODEL=$Model",
                "GITHUB_MODELS_TOKEN=$token"
            ),
            $utf8NoBom
        )
        scp -i $KeyPath -P $SshPort -o BatchMode=yes -o ConnectTimeout=20 `
            $patchPath "root@${DropletIp}:/root/eminai-fallback.env.patch"
        if ($LASTEXITCODE -ne 0) {
            throw "Fallback settings upload failed with exit code $LASTEXITCODE."
        }

        $remoteCommand = @'
set -e
cd /root/telegram-news-dashboard
cp .env /root/telegram-news-dashboard.env.before-fallback
grep -vE '^(AI_FALLBACK_PROVIDERS|GITHUB_MODELS_MODEL|GITHUB_MODELS_TOKEN)=' .env > .env.next
cat /root/eminai-fallback.env.patch >> .env.next
mv .env.next .env
chmod 600 .env
rm -f /root/eminai-fallback.env.patch
docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --no-deps --force-recreate analyzer
'@
        ssh -i $KeyPath -p $SshPort -o BatchMode=yes -o ConnectTimeout=20 `
            "root@$DropletIp" $remoteCommand
        if ($LASTEXITCODE -ne 0) {
            throw "Targeted fallback deployment failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Remove-Item -LiteralPath $patchPath -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Fallback AI deployment completed." -ForegroundColor Green
}
finally {
    if ($tokenPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr)
    }
    $token = $null
}
