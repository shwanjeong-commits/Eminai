param(
    [string] $DropletIp = "167.172.76.143",
    [string] $KeyPath = "$env:USERPROFILE\.ssh\eminai_codex",
    [int] $SshPort = 22
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $KeyPath)) {
    throw "SSH private key not found: $KeyPath"
}

Write-Host "Checking $DropletIp via SSH port $SshPort..."

$remote = @'
set -e
cd /root/telegram-news-dashboard

echo "== SERVER TIME =="
date -u

echo ""
echo "== CONTAINERS =="
docker compose -f docker-compose.yml -f docker-compose.ip.yml ps

echo ""
echo "== WEB HEALTH =="
curl -fsS http://127.0.0.1:4173/ >/dev/null && echo "web_local=ok" || echo "web_local=failed"
curl -fsS http://167.172.76.143:4173/ >/dev/null && echo "web_public_from_server=ok" || echo "web_public_from_server=failed"

echo ""
echo "== DB STATUS =="
docker compose -f docker-compose.yml -f docker-compose.ip.yml exec -T web python - <<'PY'
import sys
sys.path.insert(0, "/app/src")
from database import connect

c = connect()
print("latest_published_at=", c.execute("select max(published_at) from news_items").fetchone()[0])
print("total_news=", c.execute("select count(*) from news_items").fetchone()[0])
print("target_analyzed=", c.execute("select count(*) from news_items where analysis_scope='analysis_target' and analysis_status='analyzed'").fetchone()[0])
print("target_queued_or_review=", c.execute("select count(*) from news_items where analysis_scope='analysis_target' and analysis_status in ('queued','review')").fetchone()[0])
print("today_news_kst=", c.execute("select count(*) from news_items where news_date=date('now','+9 hours')").fetchone()[0])

print("")
print("latest_10=")
for row in c.execute("""
    select telegram_message_id, published_at, analysis_status, coalesce(title, substr(raw_text, 1, 80)) as title
    from news_items
    order by published_at desc
    limit 10
""").fetchall():
    print(tuple(row))

print("")
print("automation=")
for row in c.execute("""
    select service_name, status, detail, processed_count, error_count, updated_at
    from automation_status
    order by service_name
""").fetchall():
    print(tuple(row))
PY

echo ""
echo "== RECENT ERRORS =="
docker compose -f docker-compose.yml -f docker-compose.ip.yml logs --tail=80 web worker analyzer daily-reporter | grep -Ei "error|exception|failed|locked|quota|rate limit" || true
'@

$tmp = New-TemporaryFile
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmp, $remote, $utf8NoBom)
    $sshArgs = @(
        "-i", $KeyPath,
        "-p", "$SshPort",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "ConnectionAttempts=1",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=1",
        "root@$DropletIp",
        "bash -s"
    )

    $process = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -RedirectStandardInput $tmp -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "ssh exited with code $($process.ExitCode)"
    }
} catch {
    Write-Host ""
    Write-Host "Health check failed." -ForegroundColor Red
    Write-Host "If the dashboard opens in a browser but SSH times out, your local network or security software may be blocking SSH."
    Write-Host "Tried: root@$DropletIp port $SshPort"
    throw
} finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
