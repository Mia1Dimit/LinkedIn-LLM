# LinkedIn Career Assistant

Personal RAG-powered career intelligence built on your LinkedIn data.
Runs fully locally on your personal machine. Uses AWS Bedrock for embeddings and LLM.

## Current Status (May 12, 2026)

**Phase 2b Complete** ✅
- LinkedIn Portability Snapshot API integration ready
- 699 companies in network; 21 new ones enriched (May 10)
- 627 connections in network; all 3 recent ones enriched (May 4)
- Ready for ChromaDB ingestion

**Next:** `python ingest.py` to index enriched data into vector store.

---

## Tech Stack

- **Vector DB**: ChromaDB (local, no server)
- **Embeddings**: AWS Bedrock — Amazon Titan Embed v2
- **LLM**: AWS Bedrock — Claude 3.5 Haiku
- **Data Sources**: LinkedIn Portability API + Tavily Search enrichment
- **Cost Control**: Content-hash deduplication + date-based incremental enrichment

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

## Query System (Future)

For now, data is indexed in ChromaDB. Query interface (`query/ask.py`) coming soon.

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
