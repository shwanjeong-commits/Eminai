# Local Automation Setup

Use this while the project is still running from your Windows PC instead of a
cloud server.

## What Happens When the PC Is Off

When the PC is off:

- the dashboard/API server is stopped
- the Telegram live collector is stopped
- AI analysis is stopped
- browser/Telegram alerts are not sent

When the PC turns on again, the catch-up script collects recent Telegram
messages first, analyzes queued news, rebuilds dashboard views, and then starts
live listening.

## Manual Start

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start-local-stack.ps1
```

Open:

```text
http://127.0.0.1:4173
```

Logs:

```text
logs\api-server.out.log
logs\api-server.err.log
logs\worker.out.log
logs\worker.err.log
```

## Install Windows Startup Task

Run once:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install-windows-startup-task.ps1
```

After that, Windows will start the local stack whenever you log in.

## Remove Startup Task

```powershell
powershell -ExecutionPolicy Bypass -File tools\uninstall-windows-startup-task.ps1
```

## Catch-up Details

The worker startup flow is:

```text
1. collect latest Telegram messages, limit 500
2. reconcile known message ID gaps, limit 1000
3. analyze queued news, limit 50
4. rebuild dashboard views
5. start live Telegram collector
```

If the PC was off for a long time, run a bigger catch-up manually:

```powershell
.\tools\run-worker-with-catchup.ps1
```
