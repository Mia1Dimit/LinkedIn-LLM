# Phase 2 Data Flow Logic & Phase 2c Readiness

## Overview: The Complete Data Pipeline

```
Phase 2a (FETCH)          Phase 2b (ENRICH)           Phase 2c (INGEST)
──────────────────        ───────────────────         ──────────────────

API Snapshots    ──→   Enrichment Pipeline  ──→   Parsing & Chunking  ──→  ChromaDB
(14 domains)          (Tavily + Legacy)         (DocumentChunks)
- PROFILE             • CONNECTIONS             • All 14 domains
- POSITIONS           • COMPANY_FOLLOWS         • Enriched markdown
- EDUCATION           • Reuse Phase 1           • Metadata tagging
- SKILLS              • Generate new
- etc.
```

---

## Current Implementation Status

### ✅ Phase 2a: Snapshot API (COMPLETE)
**File:** `ingestion/snapshot_api.py`

```
LinkedIn API (oauth2)
        ↓
Token validation (v202312)
        ↓
Fetch 14 domains with pagination
        ↓
Cache JSON locally at data/api_snapshots/{DOMAIN}/
        ↓
Resume capability (skip-cache flag)
```

**Key Functions:**
- `fetch_domain_paginated(domain)` — aggregates all pages via paging links
- `validate_token()` — tests API connectivity
- `fetch_domains(domains)` — batch fetcher with caching

**Status:** ✅ Tested, production-ready. All 14 domains fetch successfully.

---

### ✅ Phase 2b: Enrichment (MOSTLY COMPLETE)
**Files:** 
- `enrichment/enrich_connections_api.py`
- `enrichment/enrich_companies_api.py`
- `enrichment/common.py` (shared utilities)

```
Snapshot JSON (CONNECTIONS / COMPANY_FOLLOWS)
        ↓
Deduplicate by URL (connections) / org name (companies)
        ↓
Check if enriched MD already exists
        ↓
If missing: Query Tavily Search API
            Improved prompts (now extract: expertise, funding, founders, etc.)
        ↓
Save as markdown to data/enriched/{connections|companies}/
        ↓
OR reuse Phase 1 legacy enrichments (automated matching)
```

**Key Features:**
- **Legacy Reuse:** Automatic matching of Phase 1 enrichments by URL/organization
  - 601/627 connections already enriched from Phase 1 (96%)
  - 645/699 companies already enriched from Phase 1 (92%)
- **Improved Prompts (just completed):**
  - Connections: Now request expertise, specialties, education, career experience
  - Companies: Now request founding date, funding rounds, investors, employees, specialties
- **Rich Markdown Output:** Structured sections matching Phase 1 format
  - Connections: Professional Summary + Sources
  - Companies: Overview + Key Links + Company Details + Funding & Investors + Sources

**Pending Enrichment:**
- **26 connections** (52 Tavily credits at 2 each)
- **54 companies** (54 Tavily credits at 1 each)

**Status:** ✅ Ready to run. Scripts are validated. Just need Tavily API key.

---

### ✅ Phase 2c: Parsing & Ingestion (ALREADY IMPLEMENTED!)
**Files:**
- `ingest.py` — main orchestrator
- `db/vector_store.py` — ChromaDB wrapper
- `utils/chunker.py` — text chunking logic

```
Cached Snapshots (JSON) + Enriched Markdown
        ↓
Parse into DocumentChunks
        ↓
Apply domain-specific chunking:
  • Profile data: 400 tokens, 0 overlap
  • Network data: 400 tokens, 50 overlap
  • Tavily enrichments: 500 tokens, 50 overlap
  • Messages: 300 tokens, 100 overlap
        ↓
Tag metadata (type, source, entity_name)
        ↓
Upsert into ChromaDB collections:
  • my_profile (PROFILE, POSITIONS, EDUCATION, SKILLS, CERTS, LANGS, PUBS)
  • my_network (CONNECTIONS + enriched markdown)
  • companies (COMPANY_FOLLOWS + enriched markdown)
  • my_activity (JOB_APPLICANT_SAVED_ANSWERS)
  • jobs (JOB_APPLICATIONS, SAVED_JOBS, SAVED_JOB_ALERTS)
  • communications (INBOX)
```

**Parsers Implemented:**
```python
PARSERS = {
    "PROFILE": parse_profile_snapshot,
    "POSITIONS": parse_positions_snapshot,
    "EDUCATION": parse_education_snapshot,
    "SKILLS": parse_skills_snapshot,
    "CERTIFICATIONS": parse_certifications_snapshot,
    "LANGUAGES": parse_languages_snapshot,
    "PUBLICATIONS": parse_publications_snapshot,
    "CONNECTIONS": parse_connections_snapshot,           ← Includes enriched MD!
    "COMPANY_FOLLOWS": parse_companies_snapshot,         ← Includes enriched MD!
    "JOB_APPLICATIONS": parse_jobs_snapshot,
    "SAVED_JOBS": parse_jobs_snapshot,
    "SAVED_JOB_ALERTS": parse_jobs_snapshot,
    "INBOX": parse_inbox_snapshot,
    "JOB_APPLICANT_SAVED_ANSWERS": parse_job_saved_answers_snapshot,
}
```

**Key Implementation Details:**
1. **Snapshot Parsing:** Extracts JSON snapshots into structured text
2. **Enrichment Integration:** For CONNECTIONS and COMPANY_FOLLOWS:
   ```python
   # First add basic snapshot data (name, company, position, etc.)
   # Then look for enriched Tavily MDs in data/enriched/{domain}/
   # Load and chunk them with proper metadata
   ```
3. **Chunking Strategy:** Different max_tokens and overlap per domain
4. **Metadata Tagging:** Each chunk gets:
   - `type`: entity type (connection_enriched, company, job, etc.)
   - `source`: origin (CONNECTIONS_TAVILY, COMPANY_FOLLOWS, etc.)
   - `entity_name`: person/company/job name for traceability

**Status:** ✅ FULLY IMPLEMENTED! Already in `ingest.py` lines 150-240 (connections & companies parsers).

---

## The "Correct Data" Logic

### How We Ensure Fetching the Correct Data

**1. Token-Based Authentication**
- LinkedIn Portability API uses OAuth2 bearer tokens
- `LINKEDIN_PORTABILITY_TOKEN` env var required
- Token validated at start via `validate_token()` call
- ✅ Implemented in `snapshot_api.py`

**2. Deterministic Snapshot Domains**
- Fixed list of 14 domains in `config.py`:
```python
PORTABILITY_API["snapshot_domains"] = [
    "PROFILE", "POSITIONS", "EDUCATION", "SKILLS", "CERTIFICATIONS",
    "LANGUAGES", "PUBLICATIONS", "CONNECTIONS", "COMPANY_FOLLOWS",
    "INBOX", "JOB_APPLICATIONS", "SAVED_JOBS", "SAVED_JOB_ALERTS",
    "JOB_APPLICANT_SAVED_ANSWERS"
]
```
- ✅ Implemented & tested (all 14 domains fetch successfully)

**3. Latest Data Caching & Resume**
- Snapshots cached at: `data/api_snapshots/{DOMAIN}/`
- Files sorted by timestamp, latest selected for parsing
- `--skip-cache` flag forces fresh fetch
- Resume-friendly: If fetch interrupted, re-running continues from last successful
- ✅ Implemented in `snapshot_api.py` with pagination handling

**4. Snapshot Pagination**
- LinkedIn API returns paginated results via `paging.links[].href`
- `fetch_domain_paginated()` aggregates ALL pages
- No data loss due to pagination limits
- ✅ Implemented in `snapshot_api.py` lines ~90-115

**5. Duplicate Deduplication**
- **Connections:** Keyed by LinkedIn URL (unique per person)
- **Companies:** Keyed by normalized organization name
- Legacy Phase 1 data auto-matched and reused
- ✅ Implemented in `enrich_connections_api.py` & `enrich_companies_api.py`

**6. Enrichment Validation**
- Check if enriched MD already exists before Tavily call
- Track credit usage to avoid overspending
- Fallback to basic snapshot data if enrichment fails
- ✅ Implemented in both enrichment scripts

**7. Parsing Robustness**
- `parse_all_snapshots()` iterates all 14 domains
- Skips if no cached data or parser missing
- Catches and reports parse errors
- Continues with partial results
- ✅ Implemented in `ingest.py` lines 576-602

---

## Phase 2c: What's Already Done vs. What's Needed

### ✅ ALREADY IMPLEMENTED IN `ingest.py`

1. **Snapshot Loading:** `load_snapshot_json(domain)` → loads latest cached JSON
2. **Connection Parsing:** `parse_connections_snapshot(elements)` 
   - Extracts basic data from snapshot
   - Looks for enriched MDs in `data/enriched/connections/`
   - Chunks both snapshot + enriched content
   - Tags metadata: `type: connection_enriched`, `source: CONNECTIONS_TAVILY`
3. **Company Parsing:** `parse_companies_snapshot(elements)`
   - Same pattern as connections
   - Enriched MDs loaded from `data/enriched/companies/`
   - Tags metadata: `type: company_enriched`, `source: COMPANY_FOLLOWS_TAVILY`
4. **Full Ingestion Pipeline:** `ingest_chunks(all_chunks)` → upserts to ChromaDB collections
5. **Dry-Run Mode:** `--dry-run` flag shows chunk counts without embedding

### ⏳ WHAT'S STILL NEEDED FOR PHASE 2c

1. **Run enrichment scripts** (once per entity backlog)
   ```bash
   python enrichment/enrich_connections_api.py --max 26
   python enrichment/enrich_companies_api.py --max 54
   ```
   - Generates enriched markdown in `data/enriched/{connections|companies}/`
   - Estimated cost: 106 Tavily credits

2. **Execute full pipeline** to ingest into ChromaDB
   ```bash
   python ingest.py --ingest-only   # Skip fetch/enrich, just parse+ingest
   # OR
   python ingest.py                 # Full pipeline: fetch + enrich + ingest
   ```

3. **Verify ChromaDB** population
   ```bash
   python ingest.py --stats         # Show collection counts
   ```

---

## Are We Ready for Phase 2c?

### 📋 Checklist

| Item | Status | Details |
|------|--------|---------|
| Snapshot API working | ✅ | All 14 domains fetch, v202312 validated |
| Snapshots cached locally | ✅ | 2576 total records in `data/api_snapshots/` |
| Legacy enrichments reused | ✅ | 601 connections + 645 companies auto-matched |
| Improved enrichment prompts | ✅ | Just completed. Targeting expertise, funding, team info |
| Enrichment scripts validated | ✅ | Both scripts pass `--stats` with no errors |
| Pending enrichment backlog | ✅ | 26 connections + 54 companies (106 credits) |
| Parsing logic implemented | ✅ | All 14 domain parsers in `ingest.py` |
| Enriched MD integration | ✅ | Connections & companies parsers load enriched MDs |
| Chunking strategy defined | ✅ | Domain-specific max_tokens and overlap |
| ChromaDB collections ready | ✅ | 6 collections defined in `config.py` |
| Metadata tagging | ✅ | Type, source, entity_name on all chunks |
| Dry-run mode | ✅ | `--dry-run` shows what would be ingested |

### 🚀 **YES, WE'RE READY FOR PHASE 2c!**

**Here's what Phase 2c execution looks like:**

```
Step 1: Enrich remaining entities (one-time, ~5 mins with Tavily API)
$ python enrichment/enrich_connections_api.py --max 26
$ python enrichment/enrich_companies_api.py --max 54
→ Generates: 80 markdown files in data/enriched/{connections,companies}/

Step 2: Parse all snapshots + enriched MDs into DocumentChunks
$ python ingest.py --ingest-only
→ Reads: data/api_snapshots/ + data/enriched/
→ Parses: 14 domains
→ Chunks: ~2500+ total chunks

Step 3: Ingest chunks into ChromaDB collections
$ ingest.py (continued from step 2)
→ Upserts chunks with metadata to 6 collections
→ my_profile, my_network, companies, jobs, communications, my_activity

Step 4: Verify
$ python ingest.py --stats
→ Shows collection counts and readiness for query.ask.py
```

---

## Data Integrity Guarantees

1. **No Data Loss:** Pagination aggregates all records
2. **No Duplicates:** Deduplication by URL (connections) and org name (companies)
3. **Freshness:** Latest snapshot selected per domain
4. **Traceability:** Metadata on every chunk (source, type, entity)
5. **Enrichment Safety:** Graceful fallback if Tavily fails
6. **Resume Capability:** Can restart fetch/enrich at any point

---

## Next Steps (Phase 2c Execution)

1. **Set TAVILY_API_KEY** if not already set
2. **Run enrichment** for 26 connections + 54 companies
3. **Run full ingest pipeline** to load ChromaDB
4. **Run `query/ask.py`** to test end-to-end query functionality

**Estimated Time:** 10-15 minutes (Tavily API calls + parsing + embedding)

---

See `ingest.py` for implementation details. All parsing logic is already in place!
