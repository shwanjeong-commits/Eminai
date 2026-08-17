# PROJECT MEMORY: Eminai Watch

Last updated: 2026-08-01 KST

## Project Summary

Eminai Watch is a Telegram news automation dashboard for economic, market, and geopolitical intelligence.

The system collects public Telegram channel messages, filters news-worthy items, stores them in SQLite, analyzes them with AI, and displays daily news, issue flows, region risks, asset impacts, market views, economic calendar/chat, and AI automation status.

Primary Telegram channel:
- `insidertracking`

Primary deployed site:
- `http://167.172.76.143:4173`

The site is password protected. Do not write the password in project files or chat summaries unless the user explicitly asks during the same operational session. The password is stored on the DigitalOcean server in `/root/telegram-news-dashboard/.env` as `SITE_ACCESS_PASSWORD`.

## Current Hosting

Provider:
- DigitalOcean Droplet

Droplet:
- `Project2-jsh`
- Public IPv4: `167.172.76.143`

Main runtime:
- Docker Compose
- Remote project path: `/root/telegram-news-dashboard`

Important exposed ports:
- `4173`: public dashboard HTTP
- `4174`: SSH management port

SSH notes:
- SSH was moved away from port 22 because Bitdefender / local network behavior interfered with normal SSH.
- SSH socket activation is used on Ubuntu 24.04. The socket override is under:
  - `/etc/systemd/system/ssh.socket.d/listen.conf`
- Expected SSH socket listen addresses:
  - `0.0.0.0:4174`
  - `[::]:4174`
- Local key used by Codex/user tooling:
  - `%USERPROFILE%\.ssh\eminai_codex`

DigitalOcean Firewall should allow:
- TCP `4173` from All IPv4 / All IPv6
- TCP `4174` from All IPv4 / All IPv6 for now

Future security target:
- Restrict `4174` to trusted IPs if the user's IP is stable.
- Disable password SSH login after confirming key access is reliable.

## Containers

Compose files:
- `docker-compose.yml`
- `docker-compose.ip.yml`

Services:
- `web`: Python API/static dashboard server on port 4173
- `worker`: Telegram live collector
- `analyzer`: AI analysis worker
- `daily-reporter`: optional daily Telegram report scheduler
- `caddy`: domain/HTTPS path, currently not active for IP-only deployment

Normal status:
- `web`, `worker`, `analyzer` should all be `Up`
- `daily-reporter` should be `Up` after the daily report feature is deployed; it may report `disabled` until `DAILY_REPORT_ENABLED=1` and Telegram bot settings are configured.

Useful command:

```bash
cd /root/telegram-news-dashboard
docker compose -f docker-compose.yml -f docker-compose.ip.yml ps
```

## Automation Behavior

Live collector:
- `src/live_collector.py`
- Service name in DB: `telegram_live_collector`
- Expected status: `listening`

Analyzer:
- `src/analysis_worker.py`
- Service name in DB: `ai_analysis_worker`
- Expected status: `idle`, `checking`, `analyzed`, or `deferred` when API quota is hit
- Transient provider errors use exponential backoff: 90, 180, 360, 720, 1440, then 1800 seconds maximum. A successful analysis resets the failure streak.

Filter audit:
- Integrated with the live collector
- Checks recent Telegram messages for missing candidates and auto-repairs news-worthy missing items
- Expected recent status: `ok`, `scheduled`, or similar

Manual update:
- `/api/manual-update`
- Sets `manual_update` status and lets live collector handle collection

Daily report:
- `src/daily_report.py` builds and sends an investor-style daily report using already-analyzed database content.
- `src/daily_report_worker.py` schedules reports at configured KST times.
- Report delivery uses the existing Telegram bot integration and is recorded in `daily_report_deliveries`.
- Daily report support and two report times (`08:00,18:00`) were deployed on 2026-07-28.
- Daily report card-news support renders a multi-card PNG album with `src/daily_report_cards.py` and sends it through Telegram `sendMediaGroup` before the fallback text report when `DAILY_REPORT_SEND_CARDS=1`.
- The dashboard can show a "Get Daily News on Telegram" home button when `TELEGRAM_DAILY_CHANNEL_URL` is set in the server `.env`. The value should be a Telegram `https://t.me/...` invite/channel URL and should not be written into project memory.
- Required server `.env` values:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_ALERT_CHAT_ID`
  - Optional dashboard subscribe button: `TELEGRAM_DAILY_CHANNEL_URL`
  - `DAILY_REPORT_ENABLED=1`
  - `DAILY_REPORT_TIME_KST`, default `08:00,18:00`; comma-separated KST times are supported
  - `DAILY_REPORT_DATE_MODE`, default `today`
  - `DAILY_REPORT_SEND_CARDS`, default `1`
- Do not store the Telegram bot token or chat ID in project memory.

## AI Provider State

Primary provider:
- Google Gemini via `GEMINI_API_KEY`
- Model: `gemini-2.5-flash`

GitHub Models fallback:
- Intentionally re-enabled by the user on 2026-07-28.
- Active model: `meta/llama-3.3-70b-instruct`.
- The fine-grained GitHub token requires `Models: Read-only` and is stored only in local `.env` and the server `.env`; never copy its value into project memory or chat.
- `openai/gpt-4.1-mini` was rejected because GitHub/Azure content filtering blocked routine economic and geopolitical news. Llama 3.3 successfully analyzed the same queued items.
- When every configured provider content-filters an item, the analyzer preserves it with `analysis_status='filtered'` and continues processing the queue instead of deferring the whole worker.

Known current bottleneck:
- Google free-tier quota may produce `429 RESOURCE_EXHAUSTED`.
- When this happens, news collection can remain healthy while analysis queue grows.
- The analyzer automatically retries later.

Recent settings applied:
- `AI_FALLBACK_PROVIDERS=github`
- `GITHUB_MODELS_MODEL=meta/llama-3.3-70b-instruct`
- `ANALYZER_BATCH_LIMIT=5`
- `ANALYZER_INTERVAL_SECONDS=25`
- `ANALYZER_IDLE_INTERVAL_SECONDS=45`

## Security Work Completed

Completed on 2026-07-28:
- Added site password protection.
- API routes under `/api/*` now require auth except:
  - `/api/auth/status`
  - `/api/auth/login`
- Frontend shows a password gate before loading protected data.
- Server `.env` contains `SITE_ACCESS_PASSWORD`.
- Server `.env` permission set to `600`.
- Verified:
  - `/api/bootstrap` without auth returns `401`
  - login with configured password returns a token
  - `/api/bootstrap` with token works

Important:
- Static files are still served so the browser can load the login UI.
- Sensitive dashboard data is protected at API level.

Additional hardening completed on 2026-07-30:
- Login POST now also requires same-origin validation before password handling.
- API POST routes continue to require same-origin validation, authentication, and rate limits before LLM-backed handlers run.
- Security response headers now include `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` in addition to CSP, frame denial, no-sniff, referrer, and permissions policies.
- Static file serving rejects hidden dotfiles under the app directory.
- Verification after deploy:
  - unauthenticated `/api/bootstrap`, `/api/news/deep-analysis`, and `/api/news/translations` returned `401`
  - cross-origin `/api/auth/login` returned `403`
  - public site returned HTTP `200` with CSP, `X-Frame-Options: DENY`, COOP, and CORP headers
  - all four containers were running, collector was `listening`, analyzer was `idle`, and queued/review analysis count was `0`

## Local Operations Tools

Health check:
- `tools/check-digitalocean-health.ps1`
- Supports custom SSH port:

```powershell
cd "C:\Users\drego\OneDrive\문서\대시보드 제작"
powershell -ExecutionPolicy Bypass -File ".\tools\check-digitalocean-health.ps1" -SshPort 4174
```

Deploy:
- `tools/deploy-digitalocean.ps1`
- Supports `-SshPort` and `-KeyPath`

```powershell
cd "C:\Users\drego\OneDrive\문서\대시보드 제작"
powershell -ExecutionPolicy Bypass -File ".\tools\deploy-digitalocean.ps1" -DropletIp 167.172.76.143 -SshPort 4174 -Restart
```

## Economic Calendar Deployment Coordination

- The local `data/news.db` currently contains 71 validated `economic_calendar_events` rows from the 2026-07-27 weekly update.
- Calendar deployment must merge only `economic_calendar_events`; never upload or replace the full server database because the server DB also contains live news and analysis data.
- The calendar-only tool is `tools/sync-calendar-to-digitalocean.ps1`, but its SSH settings must match the current shared server settings before it is run:
  - SSH port `4174`
  - key `%USERPROFILE%\.ssh\eminai_codex`
- A successful calendar deployment requires both:
  - sync output containing `calendar-sync-ok`
  - authenticated external `/api/bootstrap` verification showing `calendarEvents`
- The 2026-07-28 calendar deployment completed successfully: 71 rows exported/imported, the server DB was backed up, `calendar-sync-ok` was emitted, and the authenticated external Calendar view rendered 12 events for the week of 2026-07-27 through 2026-08-02.
- Continue to avoid running calendar sync concurrently with another task deploying the same Docker Compose project.
- Latest cross-task deployment state as of 2026-07-29:
  - `daily-reporter` and the `08:00,18:00` twice-daily schedule are deployed
  - daily report card-news is deployed with a tested 7-card PNG album flow
  - the home Telegram daily-news subscription button is deployed, but it remains hidden until the server `.env` contains a valid `TELEGRAM_DAILY_CHANNEL_URL`
  - the white/forest-green UI, calendar modes, asset/search/evidence hub, and watchlist work are deployed
  - there is no standing deployment lock; every task must still re-check other active tasks immediately before a server deployment

## Current Health Snapshot

Recent known good state after 2026-08-01 health check:
- `web`, `worker`, `analyzer`, and `daily-reporter` were recreated and running
- `web_local=ok`
- `web_public_from_server=ok`
- External root returned HTTP `200`
- Unauthenticated `/api/bootstrap` and `/api/news/deep-analysis` returned `401`
- Security headers were present: CSP, `X-Frame-Options: DENY`, `nosniff`, COOP, and CORP
- Latest Telegram collection was active at `2026-08-01T06:29:56Z` with 48 KST-today news items
- Analysis had 1,356 analyzed targets and 60 queued/review targets after restart; the analyzer was `checking`
- Daily report for `2026-08-01` was sent at the 08:00 KST schedule, and the worker remained scheduled for `08:00,18:00`
- A malformed/bot HTTP request logging traceback was fixed by making `Handler.log_request()` tolerate requests without `self.path`; post-deployment web logs showed normal request logs only
- `SITE_DOMAIN` warnings are expected for the current IP-only HTTP deployment
- On 2026-08-01 the analyzer was tuned from `3/45s/90s` to `5/25s/45s` to reduce backlog when API capacity is available. Post-change health: all containers up, 1,375 analyzed targets, 41 queued/review targets, latest collection active, and analyzer deferred briefly because GitHub Models returned a scheduled `github_models_retirement_brownout` error. This is provider availability, not a collector failure.

## Recent Product Work

Deployed to DigitalOcean on 2026-07-28:
- Dashboard visual direction changed to a white and forest-green theme.
- Home was reorganized around a market brief, upcoming events, assets, news, and AI priorities.
- Economic calendar supports weekly and monthly views.
- Asset hub search now combines the market catalog with analyzed asset themes, supports symbols and aliases, and displays generated lettermark icons.
- A device-local watchlist view stores selected asset keys in browser local storage and links saved assets to related news, charts, and upcoming earnings.
- Asset evidence combines analyzed Telegram news with curated official/source documents from `data/insidertracking_catchup.sqlite3`; the bootstrap payload exposes these as `sourceDocuments` when the file exists.
- The daily/news view is now a unified news-and-evidence hub with live text search, collected-news vs official-document filters, and an 8+ high-impact filter.
- The news-and-evidence hub also supports US/Korea region facets, macro/policy/market/earnings topic facets, and latest/impact sorting.
- Navigation labels and view descriptions were rewritten around the finished product flows; stale collected-news data now triggers a visible freshness warning with a manual-update action.
- The news hub shows collection/evidence/source coverage totals and offers one-click filter reset. Mid-size and keyboard navigation behavior were improved.
- `database.init_db()` now explicitly closes its SQLite connection after committing; this fixed the Windows single-writer test cleanup failure. All 15 unit tests pass locally.
- Fixed a global navigation-label selector that was replacing every content button carrying `data-view` (including home news rows) with the text `뉴스·근거`; navigation updates are now scoped to `#nav` only.
- News/evidence items are merged chronologically, grouped under date headings, and can be filtered with a date dropdown. Narrow-width navigation and refresh controls are forced to stay horizontal.
- The full white/forest-green UI, home/news fixes, watchlist, asset hub, calendar modes, evidence hub, date grouping/filtering, and freshness warning are now deployed.
- Deployment preserved the live `news.db` and server `.env`; pre-deployment code and DB backups were created under `/root`.
- `data/insidertracking_catchup.sqlite3` was installed separately into the shared `news-data` Docker volume so the deployed API exposes 17 source documents without replacing the live news database.
- Post-deployment verification: 500 news items, 17 source documents, 71 calendar events, latest news `2026-07-28T07:41:49Z`; `web`, `worker`, `analyzer`, and `daily-reporter` all running.
- Collection is healthy (`telegram_live_collector=listening`). Analysis is quota-deferred with 58 queued analysis targets due to Gemini 429 limits; this does not stop new message collection.
- Queue ETA support was deployed on 2026-07-28. `analysisStats.queueEstimate` derives throughput from recent 1h/6h/24h analyzed-item counts and exposes an ETA range plus worker/paused state. Home and System Status show the estimate; quota-deferred estimates are explicitly labeled `재개 후`.
- Post-deployment ETA snapshot: 59 queued, 3.5 items/hour using the 6-hour window, conditional range 809-1314 minutes (about 13h29m-21h54m after API processing resumes), worker status `deferred` because of Gemini 429.
- During this deployment, the server `.env` was found malformed at one non-key line. The malformed file was preserved under `/root`, and the valid `.env` was restored from the pre-UI backup archive before rebuilding. Password protection and all four services were re-verified afterward.
- Continue to check for another active deployment task before future deployments.
- GitHub fallback was restored with a targeted server `.env` merge and analyzer-only recreation, preserving the site password and unrelated server settings. Future fallback changes must use `tools/enable-github-fallback.ps1`; do not use full `-UploadEnv` deployment because the local `.env` does not contain every server-only setting.
- 2026-07-29: Fixed the blank main-screen regression caused by `renderHomeV2()` referencing an undeclared `queueEta`. Added the local queue estimate binding, verified the local home content renders, then deployed only `app/main.js` and rebuilt the `web` service. The public web endpoint returned HTTP 200; `/api/bootstrap` returned the expected HTTP 401 without the site password.
- 2026-07-29: Fixed two home overview display bugs and deployed `app/main.js`: upcoming events now read the API's `scheduledAt` field (with legacy fallbacks), and the home “최종 갱신” value now prefers `meta.lastUpdatedAt` over the older latest-news timestamp. Local UI verification showed the 2026-07-29 SK hynix event plus subsequent FOMC/Meta/Microsoft events and a 2026-07-28 final-update timestamp.
- 2026-07-29: Deployed analyzer rate-limit backoff. GitHub `Too many requests`, quota, 429, timeout, and temporary service errors are recorded as `deferred` with the next retry delay instead of `failed`. Consecutive retries now back off from 90 seconds to a 30-minute maximum, preventing repeated rapid attempts on the same queued item.
- Post-backoff snapshot: all four containers up, public/local web healthy, collector `listening`, 1,156 analyzed targets and 23 queued/review targets. GitHub Models was temporarily rate-limited and correctly reported `deferred ... retry in 90s`; collection remained active.
- 2026-07-29: Added a manual ChatGPT backlog round-trip workflow. `src/export_chatgpt_backlog.py` exports queued/review/filtered analysis targets with stable news/message IDs, `CHATGPT_BACKLOG_PROMPT.md` defines the required JSON contract, and `src/import_chatgpt_backlog.py` validates IDs, allowed values, score ranges, and skips rows already analyzed before applying results.
- Exported `eminai_chatgpt_backlog_20260729.json`: 24 items, no duplicate IDs or empty raw text, covering `2026-07-28T20:18:31Z` through `2026-07-28T21:58:11Z`. These are recent July 29 KST items; the older downtime backlog was already largely processed.
- 2026-07-29: Imported the returned `eminai_chatgpt_results.json`. Local schema validation and server dry-run both passed for all 24 items with exact news/message ID matches. A Docker data-volume backup was created at `backups/20260728-222933`, then all 24 queued items were imported and daily briefings, issue flows, asset views, news events, and region risks were rebuilt.
- Post-import verification: all 24 returned items are `analyzed`; 1,180 total analysis targets are analyzed and only 2 newer items remain queued. Public/local web are healthy, collector is `listening`, analyzer is `checking`, and the July 29 daily report was sent with the scheduler active for 08:00 and 18:00 KST.
- 2026-07-29: Deployed daily report card-news automation. The Docker image now installs `Pillow` and `fonts-noto-cjk`; `src/daily_report_cards.py` renders a 5-card PNG set, and `src/telegram_alerts.py` sends it as a Telegram media group before the text fallback. `DAILY_REPORT_SEND_CARDS=1` enables this behavior. Forced server test generated 5 cards and sent the 2026-07-29 daily report successfully.
- Post-card deployment verification: `web`, `worker`, `analyzer`, and `daily-reporter` all running; public/local web healthy; latest Telegram collection active; `daily_report=sent` for 2026-07-29; `filter_audit_worker=ok`. Analysis had 12 queued/review items due to temporary provider rate limiting, not a collection failure.
- 2026-07-29: Upgraded daily report card-news from 5 cards to a 7-card layout to support richer detail while staying under Telegram's 10-media album limit. The renderer now uses fit-to-box font sizing, sentence/paragraph boundary cleanup, and separate cards for cover, two key events, market reaction, daily timeline, cause-effect flow, and next-watch points. Server render test produced 7 PNG cards for 2026-07-29.
- 2026-07-29: Added and deployed the queue retry countdown. The API parses the analyzer's `retry in Ns` status, subtracts elapsed time from the worker status timestamp, and exposes `retryRemainingMinutes` plus retry metadata. Home and System Status now show `재개 시도까지` separately from the existing `재개 후` processing-time estimate. Only `src/api_server.py` and `app/main.js` were deployed and only `web` was recreated; collector/analyzer remained running. Browser verification showed 10 queued items, retry attempt in about 15 minutes, and 20-32 minutes of processing after resume.
- 2026-07-29: Replaced the non-expiring deterministic site token with a signed token that has an absolute six-hour expiry. The browser schedules automatic logout at the signed expiry, the server rejects expired/tampered/legacy tokens, unauthorized responses clear the cookie, and the auth cookie is `HttpOnly` with `Max-Age=21600`. Deploying the change invalidated prior sessions once by design. Only `src/api_server.py` and `app/main.js` were deployed and only `web` was recreated; worker, analyzer, and daily reporter remained running. External verification returned `sessionHours=6`, rejected a legacy token with HTTP 401, cleared its cookie, and all 17 local tests passed.

- 2026-07-29: Reworded the queue retry display from “재개 시도까지” to “재개 가능 시간” because a scheduled retry does not guarantee successful processing. When `retryAt` is available the UI shows the absolute KST time followed by “이후”; otherwise it shows “가능 시간 확인 중”, “현재 재개 가능”, or a relative availability estimate. Only `app/main.js` was deployed and only `web` was recreated.
- 2026-07-29: Exported a second manual ChatGPT backlog batch from the live server as `eminai_chatgpt_backlog_20260729_batch2.json`. It contains exactly 35 queued/review/filtered analysis targets, 35 unique news IDs, 35 unique Telegram message IDs, no empty raw text, and covers `2026-07-28T22:03:39Z` through `2026-07-29T06:14:06Z`. The export is read-only; later import will skip any rows the analyzer completes in the meantime.
- 2026-07-29: Validated and imported the returned second-batch file `eminai_chatgpt_results(1).json`. All 35 result rows matched the exported news/message ID pairs, passed schema and allowed-value checks, and were still importable on the server dry-run. An online SQLite backup with `integrity=ok` was created at `/app/data/backups/chatgpt-import-20260729-154104/news.db`, then all 35 rows were applied and all derived views were rebuilt. Post-import dry-run reported all 35 as already analyzed, the remaining manual-export queue was 0, all four services were up, and the public site returned HTTP 200.
- 2026-07-29: Added and deployed a home-screen Telegram daily-news subscription button. The API exposes `meta.telegramDailyChannelUrl` only when the server `.env` contains a valid `https://t.me/...` or `https://telegram.me/...` value, and the frontend hides the button when the value is missing. Deployment preserved the live DB and server `.env`; post-deployment health showed all four containers up, public HTTP 200, `telegram_live_collector=listening`, `ai_analysis_worker=idle`, and 0 queued/review analysis targets. The channel URL was not yet set on the server at verification time.
- 2026-07-29: Integrated and deployed the user-provided EMINAI branding. `app/assets/eminai_square_icon.png` is used for the sidebar brand, favicon, Apple touch icon, and push icon, while `app/assets/eminai_primary_logo.png` is used on the login gate with the WATCH descriptor.
- 2026-07-29: Deployed the wide primary EMINAI logo as a persistent top-header brand across every dashboard menu, with the current menu title and description retained beside it. Only the six logo-related static files were uploaded, a server-side backup was created at `/root/eminai-logo-backup-20260729-1637`, and only the `web` service was rebuilt. Post-deployment verification: public page and logo asset HTTP 200, unauthenticated protected API HTTP 401, and `web`, `worker`, `analyzer`, and `daily-reporter` all running. External browser verification confirmed both the top-header and login-gate logos render.
- 2026-07-29: Fixed and deployed the economic evaluation pollution from old `hi` connection-test records. Exact greeting/test probes now return a system guidance message without calling an AI provider or creating an analysis/score record. Existing probe rows are preserved in the DB but excluded from evaluation counts, averages, weaknesses, improvement items, feedback statistics, and recent analyses. Local browser verification showed 3 genuine analyses instead of 5, no visible `hi` rows, and a new `hi` submission created no evaluation entry. All 20 existing tests plus 4 targeted probe/evaluation tests passed. Deployment uploaded only `src/api_server.py` and `src/economic_chat.py`, backed up their previous server versions under `/root/evaluation-probe-backup-20260729-1652`, and rebuilt only `web`; the other services stayed running. Post-deployment checks confirmed the new filter code on the server, public HTTP 200, unauthenticated API HTTP 401, and all four services running.
- 2026-07-29: Completed a local-only security hardening pass; it is not deployed yet. Authentication now uses random opaque, server-side six-hour sessions in an `HttpOnly`, `SameSite=Strict` cookie; tokens are no longer returned to or stored by JavaScript, individual logout revokes the session immediately, and protected browser state is erased on logout. Added fail-closed startup when `SITE_ACCESS_PASSWORD` is missing, login failure lockout, login/API/market/LLM rate limits, a 256 KiB JSON request limit, same-origin checks for authenticated writes, generic client errors with privacy-preserving server logs, CSP and other security headers, safer static path containment, HTTP(S)-only external links, and explicit blocking/removal of the obsolete public preview page. Caddy is prepared with HTTPS security headers and a request-body limit; `SITE_COOKIE_SECURE=1` must be enabled only when the public site is actually served exclusively through HTTPS. Local verification passed 24 unit tests and browser/integration checks for 401 unauthenticated access, 404 preview, no token in login JSON, cookie-only login, forged-header rejection, cross-origin 403, LLM 429, login lockout 429, 413 oversized body, immediate logout invalidation, and cleared/hidden protected UI state. External DigitalOcean remains on the previous deployed version until a coordinated deployment.
- 2026-07-29: Deployed the full security hardening pass to DigitalOcean. A server-side code backup was created under `/root`, the server `.env` was preserved with mode `600`, the obsolete preview file was removed, and only `web` was rebuilt; `worker`, `analyzer`, and `daily-reporter` remained running throughout. External verification: root HTTP 200 with CSP and `nosniff`, unauthenticated `/api/bootstrap` 401, preview path 404, deployed `main.js` contains neither `sessionStorage` auth nor `X-Eminai-Auth`, production login JSON does not expose a token, the cookie is `HttpOnly` and `SameSite=Strict`, authenticated bootstrap succeeds, and logout immediately revokes the session. Post-deployment health: all four services running, public/local web healthy, collector `listening`, analyzer `idle`, 1,229 analysis targets analyzed, 0 queued/review, 85 KST-today news items, and latest collection at `2026-07-29T10:41:38Z`. The site still uses IP-based HTTP, so `Secure` cookies/HSTS remain intentionally disabled until a domain and HTTPS are activated.

When checking health, distinguish:
- Collection health: latest Telegram messages entering DB
- Analysis health: queued items being converted to analyzed items
- Display health: dashboard API and static files responding

## Do Not Forget

- Do not expose `.env` contents.
- Do not paste API keys or passwords into files.
- The user often asks for operational confirmation. Prefer running `check-digitalocean-health.ps1` when possible.
- If SSH fails, first ask whether Bitdefender Firewall is on. It previously blocked SSH until disabled.
- The dashboard password is intentionally simple for friend-sharing; stronger auth can be added later.
- Domain/HTTPS is not fully configured yet; current access is IP + port.

## Shared Memory Policy

This file is the source of truth for Codex tasks in this project.

At the start of any new task:
- Read `AGENTS.md`.
- Read this file.
- Prefer the latest facts here over stale chat memory.

After meaningful changes:
- Update this file with deployment, security, automation, architecture, or operational-state changes.
- Keep secrets out of this file. Record only the secret location and purpose.


## n8n / Appsmith Integration

- 2026-08-18: Added a separate `feature/eminai-ops-api` branch for machine-to-machine operations integration.
- `/api/ops/status` reuses existing automation status, analysis statistics, AI status, filter audit, and queue estimate builders.
- `/api/ops/news` exposes a bounded, filterable operations queue view without direct database access from n8n or Appsmith.
- `/api/ops/manual-update` reuses `start_manual_update()`; `/api/ops/reanalyze` reuses the shared requeue logic and leaves AI execution to `analysis_worker`.
- Ops routes use `X-Eminai-Ops-Key` backed by runtime-only `EMINAI_OPS_API_KEY`; no key value is stored in the repository or project memory.
- Integration instructions are in `docs/N8N_APPSMITH_INTEGRATION.md`. No n8n server or Appsmith instance was configured in this repository task.
