# LinkedIn Career Assistant

Personal RAG-powered career intelligence built on your LinkedIn data.
Runs fully locally on your personal machine. Uses AWS Bedrock for embeddings and LLM.

## Current Status (May 13, 2026)

**Phase 2c Complete** ✅
- LinkedIn Snapshot API flow is stable end-to-end
- Parsing and ingestion are validated (10,276 chunks indexed)
- ChromaDB collections are healthy and query-ready
- Modular sync runner is in place for repeatable updates

**Current focus:** Phase 3 productization (chat UX, freshness, and automation).

---

## Tech Stack

- **Vector DB**: ChromaDB (local, no server)
- **Embeddings**: AWS Bedrock — Amazon Titan Embed v2
- **LLM**: AWS Bedrock — Claude 3.5 Haiku
- **Data Sources**: LinkedIn Portability API + Tavily Search enrichment
- **Cost Control**: Content-hash deduplication + date-based incremental enrichment

---

## Delivery Phases

### Phase 1 - Foundations

- CSV preparation from LinkedIn export
- ChromaDB initialization
- Tavily experimentation focused on enrichment quality

### Phase 2 - Snapshot API Pipeline

- **Phase 2a**: Snapshot API ingestion and local caching
- **Phase 2b**: Enrichment pipeline for companies/connections
- **Phase 2c**: Parsing + embedding + ChromaDB ingestion hardening

### Phase 3 - Productization (Now)

- Frontend chat UI with conversation history and internet-enabled answering
- Freshness layer using changelog polling + targeted incremental ingest
- CI/CD and scheduler automation so updates run without manual intervention

---

## Quick Start

### Setup

```bash
pip install -r requirements.txt
export LINKEDIN_PORTABILITY_TOKEN="YOUR_TOKEN"
export TAVILY_API_KEY="YOUR_KEY"
aws configure  # AWS Bedrock access
```

### Full Ingestion Pipeline

```bash
# Fetch snapshots → Enrich via Tavily → Parse → Index in ChromaDB
python ingest.py
```

### Incremental Updates

Subsequent runs automatically skip already-enriched companies and connections:

```bash
# Uses enrichment_config.json to only process new follows/connections
python ingest.py --ingest-only
```

---

## Development & Monitoring

### Check Pipeline Status
```bash
python ingest.py --stats          # ChromaDB statistics
python enrichment/enrich_companies_api.py --stats
python enrichment/enrich_connections_api.py --stats
```

### Dry Run (No Bedrock charges)
```bash
python ingest.py --dry-run
```

### Individual Pipeline Stages
```bash
python ingest.py --fetch-only     # Snapshots only
python ingest.py --enrich-only    # Tavily enrichment only
python ingest.py --ingest-only    # Parse + embed only
```

---

## Architecture & Implementation Details

For technical documentation, design decisions, and data flow diagrams, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Historical documentation, audit reports, and execution guides are archived in **[docs/](docs/)**.

---

## Key Features

✅ **Incremental Enrichment** — Only enrich new companies/connections, skip old ones  
✅ **Cost Optimized** — Skip chunks with identical content (Bedrock charges avoided)  
✅ **Privacy** — All data stays on your machine; no cloud storage  
✅ **Self-Updating** — Config tracks last enrichment date for next run  
✅ **Quality Gating** — Skip problematic companies (outdated, generic names)  

---

## Project Structure

```
├── ingest.py                      # Main ingestion orchestrator
├── config.py                      # Global configuration
├── enrichment/
│   ├── enrich_companies_api.py   # Company enrichment via Tavily
│   ├── enrich_connections_api.py # Connection enrichment via Tavily
│   ├── skip_list.py              # Companies to skip (quality issues)
│   └── enrichment_config.json    # Tracks enrichment progress
├── db/
│   └── vector_store.py           # ChromaDB interface + Bedrock
├── utils/
│   ├── chunker.py                # Text segmentation
│   └── schema.py                 # DocumentChunk definition
├── data/
│   ├── api_snapshots/            # Cached LinkedIn snapshots
│   └── enriched/                 # Tavily enrichment markdown
├── chroma_db/                    # ChromaDB vector store (local)
└── docs/                         # Historical documentation
```

---

## Query System

The local query system is running and uses indexed LinkedIn data from ChromaDB.

Next step is to wrap it with a frontend chat application that supports:
1. Persistent conversation history
2. Better user controls (filters, source citations, controls per collection)
3. Optional internet retrieval for up-to-date context

---

## Next Steps Roadmap

### 1) Frontend Chat Application

- Build a lightweight web app (FastAPI + React or Streamlit)
- Add chat history persistence (SQLite/Postgres)
- Show retrieved chunks and citations per answer
- Add source toggles (LinkedIn-only vs LinkedIn + web)

### 2) Changelog API for Data Freshness

- Poll `memberChangeLogs` daily or weekly
- Ingest only new events (messages, invitations, social actions)
- Keep checkpoint state (last `capturedAt`) for incremental runs
- Continue using snapshot exports as source-of-truth for areas where changelog is sparse (for example, company follows)

### 3) Automation Without Manual Runs

- **Local option:** scheduled PowerShell task runs `sync_all_data.ps1`
- **Cloud option:** GitHub Actions on cron for fetch/ingest jobs
- Add notifications (email/Slack) on failures
- Add lightweight health checks and run summaries

### 4) Make the Product More Intriguing

- Daily brief generated from new events (new conversations, notable interactions)
- Personal CRM lens (follow-ups, relationship momentum, opportunity signals)
- Career intelligence dashboard (skills growth, inbound trends, company movement)
- Weekly "what changed" digest from changelog deltas

---

## Troubleshooting

**Issue**: "Cannot find cached snapshots"  
→ Run `python ingest.py --fetch-only` first to get snapshots from API

**Issue**: "Tavily API quota exceeded"  
→ Check `enrichment_config.json` for progress; resume with `python ingest.py --ingest-only`

**Issue**: "AWS Bedrock permission denied"  
→ Verify IAM user has `bedrock:InvokeModel` for `amazon.titan-embed-text-v2:0`

For more details, see **[ARCHITECTURE.md](ARCHITECTURE.md)** or check archived docs in **[docs/](docs/)**.

---

## Windows Modular Sync Runner

Use [sync_all_data.ps1](sync_all_data.ps1) when you want modular execution and timestamped logs per run.

Default sequence:

```powershell
./sync_all_data.ps1
```

This runs, in order:
1. `python ingest.py --fetch-only`
2. `python enrichment/enrich_companies_api.py --stats`
3. `python enrichment/enrich_connections_api.py --stats`
4. `python ingest.py --enrich-only`
5. `python ingest.py --ingest-only`
6. `python ingest.py --stats`

Smart skip behavior is built in:
1. Skip fetch when snapshots are fresh (default threshold: 24h)
2. Skip enrich when pending companies and connections are both 0
3. Skip ingest when both fetch and enrich were skipped (no upstream changes)

Logs are written to `logs/sync/sync_YYYYMMDD_HHMMSS.log`.

Each run also logs Tavily diagnostics:
1. key source (`env:TAVILY_API_KEY` or `data/creds/tavily_key.json`)
2. masked key fingerprint
3. live usage from Tavily usage API (project-scoped when `TAVILY_PROJECT_ID` is set)

Useful switches:

```powershell
./sync_all_data.ps1 -StatsOnly
./sync_all_data.ps1 -SkipFetch
./sync_all_data.ps1 -SkipEnrich
./sync_all_data.ps1 -SkipIngest
./sync_all_data.ps1 -ContinueOnError
./sync_all_data.ps1 -ForceFetch
./sync_all_data.ps1 -ForceIngest
./sync_all_data.ps1 -SnapshotFreshHours 12
./sync_all_data.ps1 -TavilyApiKey "tvly-..."
./sync_all_data.ps1 -TavilyProjectId "proj_..."
```

`sync_all_data.py` is now a compatibility wrapper that forwards to this PowerShell runner.
