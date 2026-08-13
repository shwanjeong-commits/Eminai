# DigitalOcean Droplet Setup

This guide is the practical click-by-click path for deploying the dashboard on
DigitalOcean with GitHub Education credit.

## 1. Confirm Credit

In DigitalOcean:

1. Open `Billing`.
2. Check `Credits` or `Promo credits`.
3. Confirm the GitHub Education credit is visible before creating a Droplet.

If the credit is not visible, go back to GitHub Student Developer Pack and
redeem the DigitalOcean offer again.

## 2. Create Droplet

Go to:

```text
DigitalOcean > Droplets > Create Droplet
```

Recommended values:

```text
Region: Singapore, or the nearest available region
Image: Ubuntu 24.04 LTS
Plan: Basic
CPU: Regular / Shared CPU
Size: 1 GB RAM minimum, 2 GB RAM preferred
Disk: default is fine
Authentication: SSH key preferred
Hostname: telegram-news-dashboard
```

Do not create a separate VPC manually. The default VPC is fine.

## 3. Add SSH Key From Windows

On your Windows PC, open PowerShell:

```powershell
ssh-keygen -t ed25519 -C "digitalocean-telegram-news"
```

Press Enter for the default path.

Print the public key:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Copy the whole output and paste it into DigitalOcean's `Add SSH Key` box.

## 4. Create Firewall

DigitalOcean firewall inbound rules:

```text
SSH        TCP 22    your IP, or all IPv4/IPv6 while testing
Custom     TCP 4173  all IPv4/IPv6 for temporary dashboard test
HTTP       TCP 80    all IPv4/IPv6, later for domain
HTTPS      TCP 443   all IPv4/IPv6, later for domain
```

Outbound can stay open.

Attach the firewall to the Droplet.

## 5. SSH Into Server

After the Droplet is created, copy its public IP.

From Windows PowerShell:

```powershell
ssh root@YOUR_DROPLET_IP
```

If you created an `ubuntu` user image or changed the user, use:

```powershell
ssh ubuntu@YOUR_DROPLET_IP
```

## 6. Install Docker

On the server:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo apt-get update
sudo apt-get install -y docker-compose-plugin git
```

If you are not logged in as root:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in.

From this Windows workspace, you can run the same setup over SSH:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup-digitalocean-server.ps1 -DropletIp YOUR_DROPLET_IP
```

## 7. Put Project On Server

Recommended: push this project to a private GitHub repository, then clone:

```bash
git clone YOUR_PRIVATE_REPOSITORY_URL telegram-news-dashboard
cd telegram-news-dashboard
```

Alternative: upload the project folder with SFTP.

From this Windows workspace, you can also upload directly:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy-digitalocean.ps1 -DropletIp YOUR_DROPLET_IP
```

To upload your local `.env` to the server too:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy-digitalocean.ps1 -DropletIp YOUR_DROPLET_IP -UploadEnv
```

Never push these to a public repository:

```text
.env
*.session
data/
```

## 8. Configure `.env`

On the server:

```bash
cp .env.example .env
nano .env
```

Required values:

```text
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_CHANNELS=insidertracking
AI_PROVIDER=google
GEMINI_API_KEY=...
GOOGLE_AI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///data/news.db
```

Optional for now:

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALERT_CHAT_ID=
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:your-email@example.com
SITE_DOMAIN=example.com
```

## 9. First Run With IP Address

Use IP-only mode first:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build
```

Run Telegram login once:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml run --rm worker python src/login_telegram.py
docker compose -f docker-compose.yml -f docker-compose.ip.yml restart worker
```

Open:

```text
http://YOUR_DROPLET_IP:4173
```

## 10. Check Status

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml ps
docker compose -f docker-compose.yml -f docker-compose.ip.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.ip.yml logs -f worker
```

Dashboard health check:

```text
http://YOUR_DROPLET_IP:4173/api/bootstrap
```

## 11. Later: Domain + HTTPS

When you have a domain:

1. Create an `A` record pointing to `YOUR_DROPLET_IP`.
2. Set `SITE_DOMAIN=your-domain.example` in `.env`.
3. Start normal mode:

```bash
docker compose up -d --build
```

Open:

```text
https://your-domain.example
```

Browser push alerts require HTTPS, so use a domain before relying on push
notifications.

## 12. Stop Costs

If you are done testing and do not want charges:

```bash
docker compose down
```

To stop Droplet billing, destroy the Droplet in the DigitalOcean dashboard.
Back up `news-data` first if you need to keep the database/session.

For automated backups, follow:

```text
BACKUP.md
```
