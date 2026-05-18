# LinkedIn Career Assistant

Personal RAG-powered career intelligence built on your LinkedIn data.
Runs fully locally on your personal machine. Uses AWS Bedrock for embeddings and LLM.

## Current Status (May 18, 2026)

**Phase 3 Productization: Chat UI Live** 🚀
- LinkedIn Snapshot API flow is stable end-to-end
- Parsing and ingestion are validated
- ChromaDB collections are healthy and query-ready
- Modular sync runner with smart skip logic is in place for repeatable updates
- Enriched markdowns for companies and connections normalized to strict field-only schemas
- Field-aware chunking for companies and network (identity/overview/finance/location boosts)
- **Retrieval**: Hybrid broad discovery (semantic + keyword-catalog) achieving 8.3/10 recall
- **Evaluation**: Strict automated gold truth generation (5 themes, 15 entities each) with rebuild from enriched data
- **Orchestration**: Sync pipeline now handles full workflow: fetch→enrich(→enriched_unstructured)→rebuild-new-only(→enriched)→ingest→rebuild-gold→[optional eval]
- **Chat UI**: Claude-style frontend with streaming, memory, web search, collapsible source sidebar, and markdown rendering
- **Chat API**: FastAPI backend with session memory (SQLite), model selector, Tavily web search, subprocess-isolated Bedrock calls
- **Retrieval routing fix**: Self-referential queries ("what do you know about me", "what certification should I pursue") now correctly route to `my_profile` collection instead of `my_network`

**Phase 3 remaining:** Freshness layer (changelog polling), authentication, deployment.

---

## Tech Stack

- **Vector DB**: ChromaDB (local, no server)
- **Embeddings**: AWS Bedrock — Amazon Titan Embed v2
- **LLM**: AWS Bedrock — Claude 4.5 Haiku
- **Data Sources**: LinkedIn Portability API + Tavily Search enrichment
- **Cost Control**: Content-hash deduplication + incremental enrichment + deterministic markdown normalization

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
- **Phase 2d**: Enriched markdown normalization + field-aware chunking for companies and network
- **Phase 2e**: Retrieval tuning + evaluation harness (`evaluation/eval_rag.py`) with scored regression runs

### Phase 3 - Productization (Current)

**Infrastructure & Retrieval (Complete)**
- ✅ Hybrid broad-intent retrieval (semantic + curated keyword catalogs) — 8.3/10 recall on gold sets
- ✅ Strict gold truth generation with automated rebuilds from enriched data
- ✅ Sync orchestrator (`sync_all_data.ps1`): fetch→enrich→rebuild-new-only→ingest→rebuild-gold→[optional eval]
  - Enrichment writes raw Tavily output to `data/enriched_unstructured/`
  - Incremental rebuild (`--new-only`) normalizes only newly enriched files into `data/enriched/`
  - Ingest reads from `data/enriched/` (normalized, field-only schemas)
  - Smart skip logic for each stage (only runs when changes detected)
  - All `ingest.py` steps stream output live (unbuffered `-u` flag)
  - Gold truth stays current after each ingest (automated rebuild)
  - Optional broad-recall smoke test with threshold failure mode (default: 7.5/10)
  - Full logging with step timings and exit codes
- ✅ Retrieval routing fix: memory-aware context no longer bleeds into collection selection; self-referential queries correctly target `my_profile`

**Frontend & Chat API (Complete)**
- ✅ FastAPI chat server (`api/chat_server.py`) with SSE-style NDJSON streaming
- ✅ Session memory persisted to SQLite (`data/chat_memory.db`) — survives page reloads
- ✅ Model selector (Claude Haiku 4.5 default, Sonnet 4, 3.7 Sonnet, custom model ID)
- ✅ Optional Tavily web search per turn (toggle in UI)
- ✅ Claude-style React frontend (`frontend/`) — dark theme, indigo accent
  - Streaming markdown rendering (react-markdown + remark-gfm)
  - Collapsible right sidebar: Knowledge base sources + Web sources with item counts
  - Independent sidebar scroll (window height driven by chat column)
  - Memory clear button
- ✅ Subprocess-isolated Bedrock calls (prevents Windows access-violation crashes in streaming path)

**Remaining**
- Freshness layer (changelog polling + targeted incremental ingest)
- Authentication and session management
- Deployment packaging (Docker, etc.)

---

## Quick Start

### Chat UI (Frontend + API)

```bash
# Terminal 1 — start the chat API
python -m uvicorn api.chat_server:app --host 127.0.0.1 --port 8000

# Terminal 2 — start the frontend dev server
cd frontend
npm install        # first time only
npm run dev        # opens at http://localhost:5173
```

The UI connects to the API at `http://127.0.0.1:8000`. Keep both processes running while using the chat.

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

### Rebuild Normalized Enriched Markdown (Companies + Connections)

```bash
# Full (re)build — reads all files from data/enriched_unstructured/, normalises, writes to data/enriched/
# Use this once after initial setup or a bulk import.
python scripts/rebuild_enriched_markdowns.py --yes

# Incremental rebuild — only normalises files newly added to enriched_unstructured/ that are not yet in enriched/
# This runs automatically in sync_all_data.ps1 after each enrich step.
python scripts/rebuild_enriched_markdowns.py --new-only
```

### Incremental Updates (via orchestrator — recommended)

```bash
# Handles the full flow automatically with smart skip logic:
# fetch (if stale) → enrich new entities → rebuild new markdowns → ingest → rebuild gold truth
.\sync_all_data.ps1

# Skip fetch if snapshots are already fresh:
.\sync_all_data.ps1 -SkipFetch
```

### Manual Incremental Steps

```bash
# 1. Fetch latest snapshots
python ingest.py --fetch-only

# 2. Enrich new companies/connections (writes raw Tavily output to data/enriched_unstructured/)
python ingest.py --enrich-only

# 3. Normalise only new enriched files into data/enriched/
python scripts/rebuild_enriched_markdowns.py --new-only

# 4. Parse + embed + ingest (reads from data/enriched/)
python ingest.py --ingest-only
```

### Evaluation (RAG Quality)

```bash
# General RAG quality evaluation (mixed queries, LLM-as-judge)
python evaluation/eval_rag.py --verbose --output evaluation/results/eval_results.json

# Quick smoke run on first N cases
python evaluation/eval_rag.py --limit 3 --output evaluation/results/eval_smoke.json

# Broad-intent recall evaluation (themed discovery questions)
# Tests: "Who in my network works in [theme]?" with strict 15-entity gold truth per theme
python evaluation/eval_broad_recall.py --verbose
```

### Rebuild Gold Truth Sets

Gold truth sets are auto-generated from enriched markdown files with strict primary-theme classification:

```bash
# One-time rebuild after significant enrichment changes
python evaluation/rebuild_gold_truth_sets_strict.py --top 15
```

This scans `data/enriched/{companies,connections}`, reads full files, weights theme mentions by section (industry/overview/position/summary), and keeps only primary-theme entities (>8 score + dominance over second theme).

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
✅ **Two-Stage Enrichment Storage** — Raw Tavily output lands in `enriched_unstructured/`; normalised field-only markdowns live in `enriched/`  
✅ **Field-Aware Chunking** — Companies and network are chunked by semantic sections (identity/overview/finance/etc.)  
✅ **Hybrid Broad Retrieval** — Combines semantic retrieval with curated entity catalogs for better discovery recall  
✅ **Strict Gold Evaluation** — Automated generation of ground truth from enriched data with primary-theme validation  
✅ **Evaluation Harness** — Repeatable scored RAG tests with per-category reporting and JSON artifacts  
✅ **Orchestrated Pipeline** — Modular sync runner (PowerShell) handles fetch→enrich→rebuild→ingest→eval with smart skip logic  
✅ **Chat UI** — Claude-style dark-theme frontend with streaming markdown, session memory, model selector, and web search  
✅ **Smart Routing** — Query router extracts current intent from memory-enriched prompts; self-referential and advisory queries target `my_profile`

---

## Strengths & Weaknesses

### Strengths
- **Broad discovery now works well**: Themed "list as many" queries achieve ~83% recall on curated gold sets
- **Hybrid retrieval approach**: Combines semantic vectors with deterministic keyword-catalog fallback for better recall diversity
- **Automated truth sets**: No manual curation needed; gold truth rebuilds automatically from enriched data with strict primary-theme gating
- **Clean evaluation methodology**: Separated concerns (general RAG quality vs broad recall) with dedicated evaluation scripts
- **Reproducible**: All retrieval and truth-set generation is deterministic and version-tracked

### Weaknesses
- **Fintech theme lag**: Fintech recall is weakest at ~47% (vs 100% for sports_tech); lower quality enrichment for financial entities
- **Broad recall still narrow**: While 83% on gold, this is recall against only 15 curated entities per theme; absolute network coverage is smaller
- **Hybrid retrieval cost**: Catalog-backed retrieval adds file I/O and map caching overhead (mitigated with lru_cache but not free)
- **Limited to curated themes**: Only 5 theme clusters (sports, cloud, ai, security, fintech); ad-hoc queries outside these themes fall back to pure semantic retrieval
- **Lack of dynamic reranking**: No cross-encoder or semantic similarity reranking of final results; relies on distance + static scoring
- **Single-pass context**: Only 30 total hits retrieved for broad intents; deeper network mining would require pagination or iterative deepening  

---

## Normalized Enriched Markdown Contract

`data/enriched/companies/*.md` now contains only:
1. Company Name
2. Source URL
3. Extracted At
4. About Us/Overview
5. Locations
6. Website URL
7. Industry
8. Company Size
9. Founded
10. Investors
11. Funding
12. Specialties

`data/enriched/connections/*.md` now contains only:
1. Name and Surname
2. Current Company
3. Position
4. LinkedIn URL
5. Connected On
6. Professional Summary

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
├── scripts/
│   └── rebuild_enriched_markdowns.py  # Normalize company/connection markdowns
├── evaluation/
│   ├── eval_rag.py               # LLM-as-judge evaluation runner
│   └── results/                  # Saved evaluation outputs (.json)
├── db/
│   └── vector_store.py           # ChromaDB interface + Bedrock
├── utils/
│   ├── chunker.py                # Text segmentation
│   └── schema.py                 # DocumentChunk definition
├── data/
│   ├── api_snapshots/            # Cached LinkedIn snapshots
│   ├── enriched/                 # Normalized field-only markdowns
│   └── enriched_unstructured/    # Backup of original unstructured markdowns
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
1. Pre-checks (Python version, Tavily API diagnostics)
2. Ingest status check (parse vs stored chunk diff)
3. `python ingest.py --fetch-only` — fetch snapshots from LinkedIn API
4. `python enrichment/enrich_companies_api.py --stats` + connections stats (on fresh data)
5. `python ingest.py --enrich-only` — Tavily enrichment → `data/enriched_unstructured/`
6. `python scripts/rebuild_enriched_markdowns.py --new-only` — normalise new files → `data/enriched/`
7. `python ingest.py --ingest-only` — parse + embed + ChromaDB upsert
8. `python ingest.py --stats` — post-run collection stats
9. `python evaluation/rebuild_gold_truth_sets_strict.py` — keep gold truth current

Smart skip behavior is built in:
1. Skip fetch when snapshots are fresh (default threshold: 24h); passes `--skip-cache` to force refresh when stale
2. Skip enrich when pending companies and connections are both 0 (checked **after** fetch)
3. Skip rebuild when enrich did not run (no new files to normalise)
4. Skip ingest when fetch, enrich, and rebuild were all skipped and no chunk diff detected

Logs are written to `logs/sync/sync_YYYYMMDD_HHMMSS.log`. All `ingest.py` steps stream output live.

Each run also logs Tavily diagnostics:
1. key source (`env:TAVILY_API_KEY` or `data/creds/tavily_key.json`)
2. masked key fingerprint
3. live usage from Tavily usage API (project-scoped when `TAVILY_PROJECT_ID` is set)

Useful switches:

```powershell
./sync_all_data.ps1 -StatsOnly
./sync_all_data.ps1 -SkipFetch
./sync_all_data.ps1 -SkipEnrich
./sync_all_data.ps1 -SkipRebuildMarkdowns
./sync_all_data.ps1 -SkipIngest
./sync_all_data.ps1 -ContinueOnError
./sync_all_data.ps1 -ForceFetch
./sync_all_data.ps1 -ForceIngest
./sync_all_data.ps1 -RunBroadEval
./sync_all_data.ps1 -SnapshotFreshHours 12
./sync_all_data.ps1 -EvalThreshold 8.0
./sync_all_data.ps1 -TavilyApiKey "tvly-..."
./sync_all_data.ps1 -TavilyProjectId "proj_..."
```
