# Deployment Guide

This project has two long-running processes:

- `web`: serves the dashboard and JSON APIs.
- `worker`: listens to Telegram, analyzes new messages, rebuilds views, and sends alerts.

The recommended cloud layout is:

```text
Cloud server
|-- web dashboard/API server
|-- Telegram live collector + AI analyzer worker
|-- SQLite DB on a persistent volume
|-- alert sender
`-- Caddy HTTPS reverse proxy
```

## 1. Required Environment Variables

Copy `.env.example` to `.env` and fill the values.

Important groups:

- Telegram collector: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_CHANNELS`
- AI provider: `AI_PROVIDER`, `GEMINI_API_KEY` or OpenAI/Azure settings
- Telegram bot alerts: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALERT_CHAT_ID`
- Browser push alerts: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`

Generate Web Push VAPID keys:

```powershell
python src/generate_vapid_keys.py
```

## 2. Local Production-Style Run

```powershell
python -m pip install -r requirements.txt
python src/migrate.py
python src/api_server.py
```

In another terminal:

```powershell
python src/live_collector.py
```

Open:

```text
http://127.0.0.1:4173
```

For Windows auto-start and catch-up after the PC was off, follow:

```text
LOCAL_AUTOMATION.md
```

## 3. Oracle Always Free / VPS Deployment

For the free VM path, follow:

```text
ORACLE_ALWAYS_FREE_DEPLOY.md
```

For GitHub Student Developer Pack credits, follow:

```text
GITHUB_EDUCATION_DEPLOY.md
```

For DigitalOcean Droplet click-by-click setup, follow:

```text
DIGITALOCEAN_DROPLET_SETUP.md
```

Quick IP-only test mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build
```

Open:

```text
http://YOUR_SERVER_IP:4173
```

Full domain + HTTPS mode:

```bash
docker compose up -d --build
```

Caddy will serve HTTPS automatically for `SITE_DOMAIN`.

## 4. Render / Railway Style Deployment

The repository includes a `Procfile`:

```text
web: python src/api_server.py
worker: python src/live_collector.py
```

Create two services from the same repository:

- Web service: `web`
- Worker service: `worker`

Set all environment variables in the platform dashboard.

For Web Push, the deployed site must use HTTPS.

## 5. systemd Deployment

Suggested path:

```bash
sudo mkdir -p /opt/telegram-news-intelligence
cd /opt/telegram-news-intelligence
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python src/migrate.py
```

Copy example service files:

```bash
sudo cp deploy/news-api.service.example /etc/systemd/system/news-api.service
sudo cp deploy/news-worker.service.example /etc/systemd/system/news-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now news-api news-worker
```

Check logs:

```bash
journalctl -u news-api -f
journalctl -u news-worker -f
```

Put Nginx/Caddy in front of the API server and enable HTTPS.

## 6. Telegram Session Warning

The worker uses the local Telegram session file. On a new server, run Telegram
login once:

```bash
python src/login_telegram.py
```

For Docker Compose:

```bash
docker compose run --rm worker python src/login_telegram.py
docker compose restart worker
```

After login, keep the generated session file with the deployment.

Do not commit `.env` or `.session` files.

## 7. Browser Push Alerts

Browser push needs:

- HTTPS deployment URL
- `VAPID_PUBLIC_KEY`
- `VAPID_PRIVATE_KEY`
- `VAPID_SUBJECT`
- user clicks `Alert Center > Enable browser alerts`

Local `127.0.0.1` can be used for testing, but real users need HTTPS.

## 8. Operating Checklist

After deployment:

1. Open `/api/bootstrap` and confirm JSON loads.
2. Open the dashboard and check the operations center.
3. Confirm `telegram_live_collector` is listening.
4. Send a new Telegram channel message or wait for one.
5. Confirm the item appears in daily news analysis.
6. Confirm alert status in the operations center.

## 9. Backups

Follow:

```text
BACKUP.md
```
