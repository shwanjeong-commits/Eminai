# GitHub Education Deployment Path

Use this path when you want to use GitHub Student Developer Pack benefits
instead of Oracle Always Free.

Official Pack page: https://education.github.com/pack

## Best Fit For This Project

Recommended order:

1. `DigitalOcean` - best VPS-style fit for this project.
2. `Microsoft Azure` - good if you already activated Azure for Students.
3. `Heroku` - convenient, but less ideal for a 24/7 Telegram worker + SQLite setup.

This project needs two always-on processes:

```text
web    -> dashboard/API server
worker -> Telegram collector + AI analyzer + alerts
```

Because of that, a small VPS is simpler than a sleep-prone app platform.

## Option A: DigitalOcean Student Credit

GitHub Student Developer Pack currently lists DigitalOcean platform credit.
This is the recommended student-benefit route.

For the exact Droplet setup flow, follow:

```text
DIGITALOCEAN_DROPLET_SETUP.md
```

Use a small Droplet:

- Ubuntu 22.04 or 24.04
- Basic shared CPU
- 1 GB RAM can work, 2 GB RAM is more comfortable
- Region near Korea: Singapore or Tokyo-like nearby region if available

Open firewall ports:

- `22` SSH
- `4173` temporary IP test
- `80` and `443` when using a domain

Then follow the same Docker Compose flow:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo apt-get update
sudo apt-get install -y docker-compose-plugin git
```

Log out and back in.

Clone or upload the project:

```bash
git clone YOUR_REPOSITORY_URL telegram-news-dashboard
cd telegram-news-dashboard
```

Create `.env`:

```bash
cp .env.example .env
nano .env
```

Start IP-only test mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml up -d --build
```

Login to Telegram once:

```bash
docker compose -f docker-compose.yml -f docker-compose.ip.yml run --rm worker python src/login_telegram.py
docker compose -f docker-compose.yml -f docker-compose.ip.yml restart worker
```

Open:

```text
http://YOUR_DROPLET_IP:4173
```

## Option B: Azure for Students

Azure is also included in GitHub Student Developer Pack and can be used with
student credit. For this project, use:

- Ubuntu VM
- Docker Compose
- Persistent disk
- Ports `22`, `4173`, `80`, `443`

The deployment commands are almost identical to DigitalOcean.

## Option C: Heroku Student Credit

Heroku is useful for a quick hosted app, but it is not the first choice here
because:

- the Telegram collector should run continuously
- SQLite persistence is awkward on ephemeral dynos
- web and worker need to be managed separately

Use Heroku only if you later move the DB to Postgres and are comfortable with
platform-specific worker setup.

## Domain Option

The Student Developer Pack also includes domain offers. A domain is not required
for the first test, but it is strongly recommended later because browser push
alerts need HTTPS.

Once you have a domain:

1. Point an `A` record to the server IP.
2. Set `SITE_DOMAIN=your-domain.example` in `.env`.
3. Start normal HTTPS mode:

```bash
docker compose up -d --build
```

## Cost Control

Use the smallest VM that runs comfortably. This project is lightweight unless
AI calls become very frequent.

Recommended start:

- 1 vCPU
- 1-2 GB RAM
- 25 GB disk

Watch:

- VM monthly cost
- AI API usage
- disk growth under `data/`

## Practical Recommendation

If GitHub Education is approved, start with DigitalOcean credit. It is the
closest match to the architecture we already prepared:

```text
small VPS + Docker Compose + SQLite volume + Telegram session volume
```

That means fewer platform-specific changes and less deployment friction.
