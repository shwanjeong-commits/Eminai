# Oracle Always Free Deployment

This is the recommended low-cost path for this project when you want the
dashboard, Telegram collector, AI analyzer, database, and alerts to keep running
after your PC is turned off.

Oracle Cloud Free Tier includes Always Free services for an unlimited time, but
free compute capacity can be unavailable in some regions. If VM creation fails
because of capacity, try another region or try again later.

Official reference: https://www.oracle.com/cloud/free/

## Target Architecture

```text
Oracle Always Free VM
|-- web dashboard/API server
|-- Telegram live collector
|-- AI analyzer
|-- SQLite DB on persistent disk
`-- alert sender
```

## 1. Create the Oracle VM

In Oracle Cloud Console:

1. Create an Always Free account.
2. Go to `Compute > Instances > Create instance`.
3. Recommended shape:
   - `VM.Standard.A1.Flex` if available
   - 1 OCPU / 6 GB RAM is enough to start
   - Ubuntu 22.04 or 24.04
4. Add your SSH public key.
5. Open these ingress ports in the VCN security list:
   - `22` for SSH
   - `4173` for temporary IP testing
   - `80` and `443` later when you connect a domain

For HTTPS browser push alerts, you eventually need a real domain connected to
the VM. Temporary IP access works for the dashboard, but browser push requires
HTTPS in normal browsers.

## 2. Install Docker on the VM

SSH into the VM:

```bash
ssh ubuntu@YOUR_ORACLE_VM_IP
```

Install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo apt-get update
sudo apt-get install -y docker-compose-plugin git
```

Log out and back in so the Docker group permission applies.

## 3. Upload or Clone the Project

If you use GitHub:

```bash
git clone YOUR_REPOSITORY_URL telegram-news-dashboard
cd telegram-news-dashboard
```

If the project is not on GitHub yet, upload the folder by SFTP or `scp`, then
enter the project directory.

Never upload your local `.env` or `.session` files to a public repository.

## 4. Configure Environment

Create `.env` on the VM:

```bash
cp .env.example .env
nano .env
```

Fill these values:

```text
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_CHANNELS=insidertracking
AI_PROVIDER=google
GEMINI_API_KEY=...
GOOGLE_AI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///data/news.db
VAPID_SUBJECT=mailto:your-email@example.com
```

Optional alert values:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALERT_CHAT_ID=...
ALERT_MIN_IMPACT=8
ALERT_KEYWORDS=oil,rates,semiconductor,china,war
```

Generate Web Push keys on the server if you have not already:

```bash
docker compose run --rm web python src/generate_vapid_keys.py
```

Then paste the generated public/private VAPID keys into `.env`.

## 5. First Run Without a Domain

Use this mode first. It exposes the dashboard at:

```text
http://YOUR_ORACLE_VM_IP:4173
```

Start the app:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build
```

Run Telegram login once on the server:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml run --rm worker python src/login_telegram.py
docker compose -f docker-compose.yml -f docker-compose.ip.yml restart worker
```

Check logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.ip.yml logs -f worker
```

## 6. Switch to Domain + HTTPS Later

When you have a domain:

1. Add an `A` record pointing the domain/subdomain to the VM public IP.
2. Set this in `.env`:

```text
SITE_DOMAIN=your-domain.example
```

3. Start the normal HTTPS stack:

```bash
docker compose up -d --build
```

Caddy will request and renew HTTPS certificates automatically.

## 7. Daily Operation Commands

Status:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs -f web
docker compose logs -f worker
```

Restart:

```bash
docker compose restart
```

Update after code changes:

```bash
git pull
docker compose up -d --build
```

Backup local data volume:

```bash
docker run --rm -v telegram-news-dashboard_news-data:/data -v "$PWD":/backup alpine tar czf /backup/news-data-backup.tgz -C /data .
```

## 8. Important Notes

- Keep `.env` private.
- Keep the Telegram session file private.
- Oracle Always Free accounts can be suspended if left idle for a long time.
- If `VM.Standard.A1.Flex` is unavailable, try another region or retry later.
- Browser push alerts need HTTPS, so use a domain before relying on them.
