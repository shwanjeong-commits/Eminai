# Backup Guide

Backups are important for this project because the database and Telegram session
are local state.

## What To Back Up

Important:

- `data/news.db`
- `telegram_news_session.session`
- any `*.session-journal` file if present

Sensitive optional file:

- `.env`

`.env` contains API keys. Back it up only somewhere private.

## Local Windows Backup

Manual backup:

```powershell
powershell -ExecutionPolicy Bypass -File tools\backup-local.ps1
```

Manual backup including `.env`:

```powershell
powershell -ExecutionPolicy Bypass -File tools\backup-local.ps1 -IncludeEnv
```

Install daily backup task:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install-windows-backup-task.ps1
```

Install daily backup task including `.env`:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install-windows-backup-task.ps1 -IncludeEnv
```

Default backup location:

```text
backups/YYYYMMDD-HHMMSS/
```

Default retention:

```text
14 backups
```

Remove daily backup task:

```powershell
powershell -ExecutionPolicy Bypass -File tools\uninstall-windows-backup-task.ps1
```

## DigitalOcean / Docker Backup

On the server, from the project directory:

```bash
sh deploy/backup-docker.sh
```

This creates:

```text
backups/YYYYMMDD-HHMMSS/news-data.tgz
```

The archive includes the SQLite DB and Telegram session stored in the Docker
volume.

## DigitalOcean Automated Backup

Add a cron job on the Droplet:

```bash
crontab -e
```

Add:

```cron
10 3 * * * cd /root/telegram-news-dashboard && sh deploy/backup-docker.sh >> backups/backup.log 2>&1
```

Adjust the project path if you cloned it somewhere else.

## DigitalOcean Snapshot

DigitalOcean Droplet backups/snapshots can also help, but they may cost extra.
Use app-level backups first, then add platform snapshots later if needed.

## Restore Notes

Local restore:

1. Stop the API server and worker.
2. Replace `data/news.db` with the backed-up `news.db`.
3. Restore the `.session` file into the project root if needed.
4. Start the app again.

Docker restore:

1. Stop containers.
2. Extract `news-data.tgz` into the `news-data` volume.
3. Restart containers.

## Move Local DB To DigitalOcean

After the Droplet is running, copy the local historical database to the server:

```powershell
powershell -ExecutionPolicy Bypass -File tools\upload-db-to-digitalocean.ps1 -DropletIp YOUR_DROPLET_IP
```

This script:

1. creates a safe SQLite copy of `data/news.db`
2. uploads it to the Droplet
3. backs up the current server Docker volume
4. replaces only `/app/data/news.db`
5. restarts the containers

## Absorb Backlog Without AI API

If Gemini free quota is exhausted, absorb queued historical news into the
situation memory without individual AI calls:

```powershell
powershell -ExecutionPolicy Bypass -File tools\absorb-backlog-digitalocean.ps1 -DropletIp YOUR_DROPLET_IP
```

This keeps future new messages analyzable while preventing old backlog from
consuming the API quota.
