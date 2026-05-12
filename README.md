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


New unified `ingest.py` supports Phase 2 workflows only (CSV import deprecated):

```bash
# Full pipeline (fetch → enrich → ingest)
python ingest.py --fetch-all

# Fetch API snapshots only (no ingestion)
python ingest.py --fetch-only

# Enrich only (no ingestion)
python ingest.py --enrich-only

# Ingest cached API snapshots + enriched data
python ingest.py --ingest-only

# Ingest one domain at a time
python ingest.py --only connections
python ingest.py --only companies
python ingest.py --only jobs
```

**Data Flow**:
```
API Snapshot (JSON) → Cached (data/api_snapshots/)
                        ↓
For enrichment domains:  Cache → Tavily Script → Enriched MDs (data/enriched/)
For direct domains:      Cache → Parser → Chunks → ChromaDB
                                ↓
                        All → ChromaDB Collections
```

**Legacy**: Phase 1 CSV workflows are archived in `Phase 1/` for reference.

### Phase 2d: Changelog & Scheduler (Future)

- `ingestion/changelog_api.py` — weekly incremental polls of LinkedIn changes
- `ingestion/cron.py` — background scheduler for periodic sync

---

## Implementation Roadmap

**Phase 2a** (this task): Implement snapshot API fetcher (`ingestion/snapshot_api.py`)

**Phase 2b** (next): Implement Tavily enrichment scripts for connections, companies, inbox

**Phase 2c** (then): Integrate into `ingest.py` orchestrator

**Phase 2d** (future): Add changelog polling + scheduler
