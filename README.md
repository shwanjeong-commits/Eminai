# Telegram News Intelligence

> Codex startup note: read `AGENTS.md` and `PROJECT_MEMORY.md` before working on this project. `PROJECT_MEMORY.md` is the shared project memory for deployment, security, automation, and current operational state.

Public Telegram channel news monitoring, Korean summarization, and geopolitical/economic analysis dashboard.

## MVP Goal

Watch selected public Telegram news channels, extract each news item, summarize it in Korean, classify its economic/geopolitical impact, and review the results in a small web app.

## Product Shape

- Source: public Telegram channels
- Domain: economy, markets, macro policy, global affairs, geopolitical risk
- Output: web/app dashboard
- First useful version: daily intelligence board with impact score, region, topic, sentiment, summary, and analysis notes

## Suggested Pipeline

1. Collect new Telegram channel messages.
2. Normalize message text, links, timestamps, source channel, and media metadata.
3. Extract article body when a linked article is present.
4. Deduplicate repeated stories across channels.
5. Run AI analysis:
   - three-line Korean summary
   - key facts
   - economic impact
   - geopolitical context
   - risk level
   - affected regions, sectors, assets, or currencies
6. Save structured results.
7. Display filtered results in the dashboard.

## Recommended Stack

- Collector: Python + Telethon
- Analysis: OpenAI API or local model-compatible provider
- Storage: SQLite for MVP, PostgreSQL later
- Web app: static dashboard for prototype, then React/Next.js when live APIs are added
- Scheduler: Windows Task Scheduler, cron, or a long-running worker

## Data Model Draft

```text
news_items
- individual Telegram/news article records

daily_briefings
- one generated briefing per date

issues
- continuing stories such as Fed policy, Middle East shipping risk, China stimulus

issue_events
- timeline entries inside each issue

news_issue_links
- connection between individual news and continuing issues

asset_impacts
- asset, sector, currency, commodity, or stock-specific situation

region_risks
- regional risk summaries by date
```

## Environment Variables

Create `.env` from `.env.example`:

```text
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_CHANNELS=
OPENAI_API_KEY=
DATABASE_URL=sqlite:///data/news.db
```

The current app also supports Telegram bot alerts and browser Web Push alerts.
See `.env.example` for the full list of variables.

`TELEGRAM_CHANNELS` should be a comma-separated list:

```text
TELEGRAM_CHANNELS=channel_one,channel_two,https://t.me/channel_three
```

## Next Implementation Steps

1. Confirm target Telegram channel usernames.
2. Install Python dependencies and create `.env`.
3. Run SQLite initialization.
4. Collect recent public channel posts.
5. Add AI analysis that fills news, issue, asset, and region tables.
6. Replace the sample dashboard data with live `/api/*` output.

## Product Roadmap

Current priority order:

1. Strengthen the current situation board.
2. Make the news-flow menu connect related events over time.
3. Improve asset and instrument-level situation views.
4. Stabilize live automation with retry queues for failed AI analysis.

## Analysis Pipeline

Prepare DB columns for classification:

```powershell
python src/migrate.py
```

Run first-pass message classification:

```powershell
python src/classifier.py
```

This separates messages into:

```text
queued      - analysis candidates
ignored     - link-only, very short, or non-news comments
review      - ambiguous messages
```

Run AI analysis for queued July-and-later news:

```powershell
python src/ai_analyzer.py --limit 10
```

Or use the helper:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-ai-analyzer.ps1
```

The analyzer reads historical context packets from `ai_context_batches`, analyzes only
`analysis_target` rows, and fills `summary_ko`, `analysis_ko`, `impact_score`,
`sentiment`, `risk_level`, and `category`. Add `OPENAI_API_KEY` to `.env` before
running it with direct OpenAI billing.

### Azure OpenAI / Azure AI Foundry

If you want to use Azure credits instead of direct OpenAI billing, set the provider
to Azure and add your Azure OpenAI resource details:

```text
AI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=2024-10-21
```

`AZURE_OPENAI_DEPLOYMENT` is the deployment name you create in Azure AI Foundry,
not just the model name. After this, run the same analyzer command:

```powershell
python src/ai_analyzer.py --limit 10
```

### Google AI Studio / Gemini API

If you want to use a Google AI Studio API key, set the provider to Google:

```text
AI_PROVIDER=google
GEMINI_API_KEY=
GOOGLE_AI_MODEL=gemini-2.5-flash
```

Then run the same analyzer command:

```powershell
python src/ai_analyzer.py --limit 10
```

## Local Prototype

Open [app/index.html](app/index.html) directly in a browser for sample data, or run the local API-backed app:

```powershell
python src/api_server.py
```

Then visit:

```text
http://127.0.0.1:4173
```

The app uses sample data when opened directly, and uses `data/news.db` when served through `src/api_server.py`.

## Deployment

See [DEPLOY.md](DEPLOY.md) for Render/Railway/VPS deployment notes.

The deployed service has two processes:

```text
web: python src/api_server.py
worker: python src/live_collector.py
```

Browser Web Push alerts require HTTPS and VAPID keys:

```powershell
python src/generate_vapid_keys.py
```

## Database Setup

Initialize the local SQLite database:

```powershell
python src/database.py
```

This creates:

```text
data/news.db
```

Check whether Telegram settings are ready:

```powershell
python src/config.py
```

## Collector Skeleton

After installing dependencies and filling `.env`, the first collector entry point will be:

```powershell
powershell -ExecutionPolicy Bypass -File tools/login-telegram.ps1
```

This creates the local Telegram session file. It will ask for your phone number and the login code sent to your Telegram app.

```powershell
python src/collector.py
```

Backfill more history:

```powershell
python src/collector.py --limit 1000
```

Backfill all available history:

```powershell
python src/collector.py --all
```

Run continuous collection for new messages:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-live-collector.ps1
```

The live collector saves each new Telegram text message, classifies it, and immediately
analyzes it when it is a July-and-later `queued` or `review` news item. If the AI
provider hits a temporary quota or demand limit, the message stays in the queue and
can be analyzed later with `python src/ai_analyzer.py --limit 10`.

The first login run asks Telegram login/session confirmation through Telethon. After that, the saved session can poll public channels automatically.

If dependencies are installed into the project-local `vendor/` folder, scripts automatically load them through `src/bootstrap.py`.

GitHub practice update.
