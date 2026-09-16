# JobHunter

A Python pipeline that pulls remote AI/ML/automation jobs from 8 sources
every morning, deduplicates them, scores them against a configurable
profile, and delivers a ranked digest to Telegram.

## Why

Manually scanning remote job boards takes an hour a day and still misses
postings. This runs on a schedule, filters out roles that don't fit
(senior-only, off-domain, geo-restricted), and surfaces only what's worth
applying to.

## Architecture

    ┌──────────────────┐
    │  8 job sources   │  Remotive, RemoteOK, Arbeitnow, Jobicy,
    │  (APIs + RSS)    │  WeWorkRemotely, HN Who's Hiring,
    └────────┬─────────┘  Himalayas, NoDesk
             │
             ▼
    ┌──────────────────┐
    │  Deduplication   │  SQLite, keyed on (source, id) + normalized URL
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  Scoring engine  │  YAML-configurable: title gates, keyword
    │                  │  weights, seniority filters, geo filters
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  Telegram digest │  Personal chat + optional public channel
    └──────────────────┘

Runs on GitHub Actions daily at 6am UTC. Zero cost, zero infrastructure.

## Features

- **8 sources** — 5 REST APIs, 2 RSS feeds, 1 Algolia-powered HN scraper
- **Deduplication** — catches re-posts even when the URL has a `-1`/`-2` suffix
- **Configurable scoring** — every rule lives in `config.yaml`; no code changes needed to tune
- **Title gating** — hard-rejects senior-only roles and off-domain titles before scoring
- **Geo filtering** — blocks US/UK/Canada-only postings for worldwide-remote roles
- **Freshness boost** — jobs posted in the last 3 days score higher
- **Two-tier output** — personal digest (loose threshold) + public channel (strict)
- **Scheduled** — GitHub Actions cron, no server required

## Stack

Python · SQLite · requests · feedparser · PyYAML · GitHub Actions

## Running locally

    pip install -r requirements.txt
    python run.py --notify

Environment variables (for Telegram):

    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
    TELEGRAM_PUBLIC_CHAT_ID=...   # optional

## Tuning

Edit `config.yaml` to adjust which roles pass. Use these to inspect:

    python run.py --show-reasons       # why each job scored what it did
    python run.py --min-score 0        # dump everything, including rejects

## License

MIT
