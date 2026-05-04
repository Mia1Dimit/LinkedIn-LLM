# LinkedIn Career Assistant

Personal RAG-powered career intelligence built on your LinkedIn data.
Runs fully locally on your personal machine. Uses AWS Bedrock for embeddings and LLM.

## Stack
- **Vector DB**: ChromaDB (local, no server needed)
- **Embeddings**: AWS Bedrock — Amazon Titan Embed v2 or Cohere Embed Multilingual
- **LLM**: AWS Bedrock — Claude 3 Sonnet
- **Data**: Member Data Portability API + LinkedIn ZIP export + Tavily enrichment MDs

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AWS credentials
```bash
aws configure
# Enter your AWS Access Key, Secret, and region (e.g. eu-west-1)
```

Make sure your IAM user has `bedrock:InvokeModel` permission for:
- `amazon.titan-embed-text-v2:0`
- `anthropic.claude-3-sonnet-20240229-v1:0`

### 3. Set your name & LinkedIn API token
```bash
export LINKEDIN_OWNER_NAME="Dimitris"
export LINKEDIN_PORTABILITY_TOKEN="YOUR_PORTABILITY_TOKEN_HERE"
```

### 4. Verify cached API snapshots
Place any pre-fetched LinkedIn Portability Snapshot API responses in `data/api_snapshots/<DOMAIN>/` (optional).
The ingestion pipeline will fetch missing domains on first run.

---

## Usage

### Phase 1: Dry run (no Bedrock calls, just parsing)
```bash
python ingest.py --dry-run
```
Use this first to verify all CSVs parse correctly before spending Bedrock credits.

### Ingest everything
```bash
python ingest.py
```

### Ingest one section at a time
```bash
python ingest.py --only profile
python ingest.py --only network
python ingest.py --only companies
python ingest.py --only activity
python ingest.py --only messages
```

### Check what's in ChromaDB
```bash
python ingest.py --stats
```

### Ask a question
```bash
python query/ask.py "Who do I know at AWS?"
python query/ask.py "What roles have I applied for in the last year?"
python query/ask.py "Which companies in my network are in fintech?"
python query/ask.py "Summarise my career trajectory"
python query/ask.py "What skills do I have that match a senior PM role?"
```

### Interactive mode
```bash
python query/ask.py --interactive
```

### Debug: see what context was retrieved
```bash
python query/ask.py "Who do I know at Google?" --verbose
```

---

## Project Structure

```
linkedin_assistant/
├── config.py                   # All paths, model IDs, collection names
├── ingest.py                   # Main ingestion orchestrator
├── requirements.txt
├── data/
│   ├── csv/                    # LinkedIn ZIP CSVs
│   └── tavily/
│       ├── companies/          # Tavily extract MDs
│       └── connections/        # Tavily search MDs
├── chroma_db/                  # ChromaDB persistent storage (auto-created)
├── parsers/
│   ├── parse_profile.py        # Profile, positions, education, skills, certs, langs, pubs
│   ├── parse_network.py        # Connections CSV + Tavily connection MDs
│   ├── parse_companies.py      # Company follows CSV + Tavily company MDs
│   ├── parse_activity.py       # Job applications, saved jobs, likes, saved answers
│   └── parse_messages.py       # Full message threads
├── db/
│   └── vector_store.py         # ChromaDB + Bedrock embedder
├── query/
│   └── ask.py                  # RAG retriever + Bedrock Claude
└── utils/
    ├── schema.py               # Unified DocumentChunk schema
    └── chunker.py              # Text splitter
```

---

## 📋 Migration: Phase 1 → Phase 2

**Phase 1 (CSV-based)** is now archived in [Phase 1/](Phase 1/) for reference.

**Phase 2 (API-based)** is the current implementation:
- ✅ Eliminates CSV dependency — data source is LinkedIn Portability Snapshot API
- ✅ Enables automated periodic updates (future: changelog polling)
- ✅ Same parsing & ingestion logic, adapted for API JSON format
- ✅ New unified `ingest.py` orchestrates fetch → enrich → parse → embed → store

See [Phase 1/README.md](Phase 1/README.md) for legacy documentation.

---

## Phase 2 — LinkedIn Portability Snapshot API

Replace CSV imports with live API-sourced data. Three core workflows:

### Phase 2a: Snapshot API Fetcher

**Goal**: Fetch all configured domains from LinkedIn Portability Snapshot API as JSON, cache locally.

**Domains** (14 total):
- **Direct Ingestion** (9) → parsed directly to chunks & ChromaDB
  - `PROFILE`, `POSITIONS`, `EDUCATION`, `SKILLS`, `CERTIFICATIONS`, `LANGUAGES`, `PUBLICATIONS`, `JOB_APPLICANT_SAVED_ANSWERS`, `INBOX`

- **Tavily Enrichment** (2) → search public data, enrich, then ingest
  - `CONNECTIONS` — Tavily Search API with `"<Full Name>" <Company> <Position>` (exact match)
    - Extract: professional summary, experience, education, certifications
  - `COMPANY_FOLLOWS` — Tavily Search API with `<Company Name> industry founding funding` (structured query)
    - Extract: company info, industry, recent activity, founding date, size

- **Activity** (3) → direct ingestion
  - `JOB_APPLICATIONS`, `SAVED_JOBS`, `SAVED_JOB_ALERTS`

**Note**: INBOX is ingested directly without enrichment (conversation content is already self-contained).

**Script**: `ingestion/snapshot_api.py`
```bash
# Fetch all domains (requires LINKEDIN_PORTABILITY_TOKEN env var)
python ingestion/snapshot_api.py --fetch-all

# Fetch specific domains only
python ingestion/snapshot_api.py --domains PROFILE CONNECTIONS SAVED_JOBS

# Dry-run (validate token, show quota usage)
python ingestion/snapshot_api.py --validate

# Resume interrupted fetch (skips already-cached domains)
python ingestion/snapshot_api.py --resume
```

**Caching Strategy**:
- Cache folder: `data/api_snapshots/<domain>/<timestamp>.json`
- Resume logic: skip already-cached domains (respects API rate limits)
- Quota tracking: log API credits/requests per domain

### Phase 2b: Tavily Enrichment Scripts

**For Domains Requiring Enrichment** (CONNECTIONS, COMPANY_FOLLOWS only):

#### `enrichment/enrich_connections_api.py`
- **Input**: `data/api_snapshots/CONNECTIONS/<timestamp>.json`
- **Process**: For each connection (First Name, Last Name, URL, Company, Position):
  1. Query Tavily Search API with: `"<Full Name>" <Company> <Position>` (exact match)
  2. Extract professional summary, experience, education, certifications
- **Output**: Markdown file per connection → `data/enriched/connections/<slug>.md`
- **Resume**: Skip already-enriched connections (by checking file existence)

#### `enrichment/enrich_companies_api.py`
- **Input**: `data/api_snapshots/COMPANY_FOLLOWS/<timestamp>.json`
- **Process**: For each company (Organization name):
  1. Query Tavily Search API with: `<Company Name> industry founding funding careers` (structured search)
  2. Extract company page, industry, founding info, size, recent activity
- **Output**: Markdown file per company → `data/enriched/companies/<slug>.md`
- **Resume**: Skip already-enriched companies

**Note**: INBOX and other domains are ingested directly without enrichment.

### Phase 2c: Integrated Ingestion Pipeline

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
