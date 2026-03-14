# Clawbot — LinkedIn AI Automation Agent

Fully autonomous LinkedIn outreach pipeline built with Python + Selenium + GPT-4o.

**Zero-touch flow:** Filter → Connect → Message

---

## Features

- **Profile scraping** — Searches LinkedIn people results and extracts full profile data
- **Smart filtering** — Filters by role, seniority, location, and connection degree
- **Auto-connect** — Sends connection requests with human-like delays and behavior
- **GPT-4o messages** — Generates personalized outreach messages from each profile's data
- **Acceptance polling** — Detects accepted connections and queues them for messaging
- **Rate limiting** — Persisted hourly + daily token buckets (survives restarts)
- **Scheduling** — APScheduler cron runner, configurable intervals via YAML
- **Activity logs** — Append-only JSON Lines log + CSV export for reporting
- **Anti-detection** — Undetected ChromeDriver, human-like typing/scrolling/delays

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your LinkedIn credentials and OpenAI API key
```

### 3. Configure targeting

Edit [config/config.yaml](config/config.yaml) to set:
- Target roles, industries, seniority levels, and locations
- Rate limits and scheduling intervals
- GPT model, persona, and product context

### 4. Run immediately (one pass)

```bash
python scripts/run_pipeline.py
```

### 5. Run on a schedule

```bash
python scripts/run_scheduler.py
```

### 6. Export logs to CSV

```bash
python scripts/export_logs.py
```

---

## Project Structure

```
clawbot-linkedin-ai/
├── config/
│   └── config.yaml          # All tunable settings
├── clawbot/
│   ├── core/
│   │   ├── orchestrator.py  # Pipeline runner (the main entry point)
│   │   └── state_store.py   # SQLite state machine for profiles
│   ├── browser/
│   │   ├── driver.py        # Stealth Chrome factory
│   │   ├── session.py       # Login + cookie persistence
│   │   └── anti_detect.py   # Human-like interaction helpers
│   ├── scraper/
│   │   ├── search.py        # LinkedIn search + pagination
│   │   ├── profile_parser.py # Profile data extraction
│   │   └── filter_engine.py  # Targeting filter logic
│   ├── outreach/
│   │   ├── connector.py     # Sends connection requests
│   │   ├── messenger.py     # Sends DMs post-acceptance
│   │   └── acceptance_poller.py # Detects accepted connections
│   ├── ai/
│   │   ├── gpt_client.py    # OpenAI wrapper
│   │   ├── prompt_builder.py # Builds personalized prompts
│   │   └── message_templates.py # Message structure templates
│   ├── scheduler/
│   │   ├── job_runner.py    # APScheduler cron runner
│   │   └── rate_limiter.py  # Persistent token bucket rate limiter
│   └── logging/
│       └── activity_logger.py # JSONL + CSV activity logging
├── data/
│   ├── state.db             # Pipeline state (auto-created)
│   └── logs/
│       ├── activity.jsonl   # Append-only event log
│       └── activity.csv     # CSV export
├── scripts/
│   ├── run_pipeline.py      # One-shot pipeline run
│   ├── run_scheduler.py     # Scheduled cron mode
│   └── export_logs.py       # Log exporter
└── tests/                   # Unit tests (pytest)
```

---

## Pipeline States

Each profile moves through a SQLite-backed state machine:

```
DISCOVERED → FILTERED_IN → CONNECTION_SENT → CONNECTION_ACCEPTED → MESSAGE_SENT
           → FILTERED_OUT
           → CONNECTION_FAILED  (retried next run)
           → MESSAGE_FAILED     (retried next run)
```

The pipeline is **fully resumable** — crashes or restarts pick up exactly where they left off, and no profile is ever double-messaged.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Configuration Reference

Key settings in `config/config.yaml`:

| Setting | Default | Description |
|---|---|---|
| `targeting.roles` | `[...]` | Job title keywords to target |
| `targeting.seniority` | `[...]` | Seniority level keywords |
| `targeting.locations` | `[...]` | Location strings to match |
| `rate_limits.connection_requests_per_day` | `20` | Max connections/day |
| `rate_limits.connection_requests_per_hour` | `5` | Max connections/hour |
| `schedule.scrape_interval_hours` | `24` | How often the pipeline runs |
| `ai.model` | `gpt-4o` | OpenAI model for messages |
| `ai.persona` | `friendly SaaS founder` | GPT persona prompt |
| `browser.headless` | `false` | Run Chrome headless |

---

## Important Notes

- LinkedIn's Terms of Service prohibit automated scraping and messaging. Use this tool responsibly and at your own risk.
- Keep `connection_requests_per_day` at 20 or below to avoid account restrictions.
- The first run will open a Chrome window for login. Subsequent runs reuse the saved session.
- If LinkedIn triggers a security checkpoint, complete it manually in the browser and re-run.
