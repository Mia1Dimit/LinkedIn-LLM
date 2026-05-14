# LinkedIn Career Assistant — Phase 2 Architecture

## Overview

Phase 2 uses the **LinkedIn Portability API** exclusively for data ingestion. All CSV-based Phase 1 logic has been replaced with API snapshots and Tavily enrichment.

As of Phase 2d, enriched markdowns for companies and connections are normalized into strict field-only schemas before chunking and indexing.

---

## Ingestion Pipeline

### Immutable Workflow Contract

```
[1] FETCH all snapshot domains from LinkedIn Portability API
         ↓
[2] ENRICH companies & connections only (skip if already enriched)
         ↓
[3] NORMALIZE enriched markdowns for companies/connections
         ↓
[4] CHUNK all 14 domains
         ↓
[5] UPSERT to ChromaDB (skip if content unchanged)
```

**Why this sequence?**
- Prevents redundant Tavily API calls (quota management)
- Avoids re-embedding unchanged chunks (cost optimization)
- Eliminates base+enriched duplication for semantic search quality

---

## Data Flow by Domain

### Snapshot-Direct Domains (12)

These domains go directly from LinkedIn Portability API snapshot → chunks → ChromaDB.

| Domain | Collection | Notes |
|--------|-----------|-------|
| PROFILE | my_profile | Bio, headline, location |
| POSITIONS | my_profile | Job history |
| EDUCATION | my_profile | Schools, degrees, graduation dates |
| SKILLS | my_profile | List of skills |
| CERTIFICATIONS | my_profile | Certs, issuer, expiry |
| LANGUAGES | my_profile | List of languages |
| PUBLICATIONS | my_profile | Articles, URLs, dates |
| INBOX | communications | Message threads & conversations |
| JOB_APPLICATIONS | jobs | Applications with dates |
| SAVED_JOBS | jobs | Saved job listings |
| SAVED_JOB_ALERTS | jobs | Job alert subscriptions |
| JOB_APPLICANT_SAVED_ANSWERS | my_activity | Saved answers to application questions |

**Code:** [ingest.py](ingest.py#L127-160)

**Parsing Strategy:**
- Each domain has a dedicated parser function
- Snapshots are loaded from cache via `load_snapshot_json(domain)`
- Elements extracted from `snapshot["elements"]` list
- Per-row or aggregated chunks depending on domain semantics

---

### Enriched-Markdown Domains (2)

These domains use enriched markdown files ONLY (not snapshot base data).

| Domain | Collection | Source | Enrichment |
|--------|-----------|--------|-----------|
| CONNECTIONS | my_network | `data/enriched/connections/*.md` | Tavily Search (deep profile) |
| COMPANY_FOLLOWS | companies | `data/enriched/companies/*.md` | Tavily Search (company research) |

### Normalized Markdown Contract

Before chunking, enriched markdowns are reduced to only required fields.

Companies retain only:
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

Connections retain only:
1. Name and Surname
2. Current Company
3. Position
4. LinkedIn URL
5. Connected On
6. Professional Summary

Original unstructured markdowns are preserved under `data/enriched_unstructured/`.

**Why markdown-only?**
- Snapshots contain minimal data (URL + basic info)
- Tavily enrichment provides comprehensive profiles (news, funding, team, etc.)
- Combining base + enriched = duplicate chunks → poor semantic search
- Solution: Use enriched markdown exclusively, skip base snapshots

**Why normalize first?**
- Removes noisy page chrome and blended social activity
- Makes chunking deterministic and field-aware
- Prevents retrieval from being polluted by irrelevant sections

**Code:** [ingest.py](ingest.py#L196-225), [ingest.py](ingest.py#L228-257)

Chunking is now field-aware for these two domains rather than raw full-markdown chunking.

---

## Skip Logic — Cost Optimization

### Stage 1: Enrichment Skip (enrich_*.py)

**File:** [enrichment/enrich_companies_api.py](enrichment/enrich_companies_api.py)  
**File:** [enrichment/enrich_connections_api.py](enrichment/enrich_connections_api.py)

Both enrichment scripts check if a company/connection is already enriched before calling Tavily API:

```python
def split_pending(companies: list[dict]) -> tuple[list[dict], int]:
    pending = []
    enriched = 0
    for company in companies:
        if file_has_content(output_path(company)):  # ← Check if .md exists
            enriched += 1
        else:
            pending.append(company)  # ← Only enrich new ones
    return pending, enriched

# Usage in main()
pending, enriched = split_pending(companies)
print_stats(companies, pending, enriched, ...)

if not pending:
    return  # ← Early exit: no new enrichments needed
```

**Impact:**
- ✅ First run: Enriches all pending (and reuses Phase 1 legacy files)
- ✅ Subsequent runs: Skips already-enriched files
- ✅ Cost savings: Zero Tavily API calls for unchanged companies/connections

### Stage 2: Upsert Skip (VectorStore)

**File:** [db/vector_store.py](db/vector_store.py#L162-193)

The `upsert()` method implements content-hash deduplication:

```python
def upsert(self, chunks: list[DocumentChunk], verbose: bool = True) -> dict:
    stats = {"inserted": 0, "skipped": 0, "errors": 0}
    
    for coll_name, coll_chunks in by_collection.items():
        collection = self._get_collection(coll_name)
        
        to_upsert = []
        if INGEST["skip_unchanged"]:  # ← Enabled in config.py
            existing_ids = self._existing_ids(collection, [c.chunk_id for c in coll_chunks])
            existing_hashes = self._existing_hashes(collection, list(existing_ids))
            
            for chunk in coll_chunks:
                if chunk.chunk_id in existing_ids:
                    stored_hash = existing_hashes.get(chunk.chunk_id)
                    if stored_hash == chunk.content_hash:
                        stats["skipped"] += 1
                        continue  # ← Skip unchanged chunks
                to_upsert.append(chunk)
        else:
            to_upsert = coll_chunks
        
        # ... embed and upsert to_upsert only ...
        
    return stats
```

**Config Setting:** [config.py](config.py#L109)
```python
INGEST = {
    "skip_unchanged": True,  # ← Always True for Phase 2
    "embedding_rpm": 100,    # Bedrock rate limit
    "owner_name": "...",
}
```

**Impact:**
- ✅ Prevents re-embedding identical chunks
- ✅ Saves Bedrock costs on incremental ingests
- ✅ Batching: 50 chunks per Bedrock call

---

## Chunking Strategy

### By Domain Type

**Profile Domains** (PROFILE, POSITIONS, EDUCATION, SKILLS, etc.)
- Max tokens: 400
- Overlap: 0 (self-contained sections)
- Example: "# POSITIONS" section chunks separately from "# SKILLS"

**Normalized Company Markdown** (`COMPANY_FOLLOWS_TAVILY`)
- `company_identity`: Company Name, Source URL, Extracted At, Website, Industry, Company Size, Founded
- `company_overview`: About Us/Overview
- `company_locations`: All locations
- `company_finance`: Investors + Funding
- `company_specialties`: Specialties
- Typical chunk size: 220-320 tokens
- Overlap: 0 for structured sections, 30 for overview

**Normalized Connection Markdown** (`CONNECTIONS_TAVILY`)
- `connection_identity`: Name, company, position, LinkedIn URL, connected date
- `connection_summary`: Professional Summary
- Typical chunk size: 220-320 tokens
- Overlap: 0 for identity, 30 for summary

**Message Domains** (INBOX)
- Max tokens: 300
- Overlap: 100 (preserve conversation context)
- Example: Multi-turn conversations keep context across turns

**Default/Jobs** (JOB_APPLICATIONS, SAVED_JOBS, etc.)
- Max tokens: 400
- Overlap: 50

**Code:** [config.py](config.py#L73-82)

---

## Collections — Final Architecture

| Collection | Domains | Sources | Chunk Count (Baseline) |
|-----------|---------|---------|------|
| `my_profile` | PROFILE, POSITIONS, EDUCATION, SKILLS, CERTS, LANGS, PUBS | Snapshots | ~7 chunks |
| `my_activity` | JOB_APPLICANT_SAVED_ANSWERS | Snapshot | ~1 chunk |
| `my_network` | CONNECTIONS | Normalized enriched MD only (CONNECTIONS_TAVILY) | varies by chunking pass |
| `companies` | COMPANY_FOLLOWS | Normalized enriched MD only (COMPANY_FOLLOWS_TAVILY) | varies by chunking pass |
| `communications` | INBOX | Snapshot | ~1 chunk |
| `jobs` | JOB_APPLICATIONS, SAVED_JOBS, SAVED_JOB_ALERTS | Snapshots | ~212 chunks |

---

## Running the Pipeline

### Full Pipeline (Fetch + Enrich + Ingest)
```bash
python ingest.py --fetch-all
```

### Normalize Enriched Markdown (One-Time / On Demand)
```bash
python scripts/rebuild_enriched_markdowns.py --yes
```

### Fetch Only
```bash
python ingest.py --fetch-only
```

### Enrich Only
```bash
python ingest.py --enrich-only
```

### Ingest Only (Use cached snapshots + enriched)
```bash
python ingest.py --ingest-only
```

### Dry Run (Parse without embedding)
```bash
python ingest.py --dry-run
```

### Show Stats
```bash
python ingest.py --stats
```

### With Verbose Output
```bash
python ingest.py --fetch-all --verbose
```

---

## Incremental Updates

When new LinkedIn data arrives:

```bash
# 1. Fetch latest snapshots (pulls new data from API)
python ingest.py --fetch-only

# 2. Enrich (skip logic prevents redundant Tavily calls)
python ingest.py --enrich-only

# 3. Ingest (skip_unchanged prevents redundant embeddings)
python ingest.py --ingest-only
```

**Result:**
- ✅ Only new/changed chunks embedded
- ✅ Zero redundant API calls
- ✅ Zero wasted Bedrock credits

---

## Environment Variables

Required:
```bash
export LINKEDIN_PORTABILITY_TOKEN="your_token_here"
export TAVILY_API_KEY="your_tavily_key"
export AWS_REGION="eu-west-1"  # or your AWS region
```

Optional:
```bash
export LINKEDIN_API_VERSION="202312"  # API version (defaults to 202312)
export LINKEDIN_OWNER_NAME="Your Name"  # Used in system prompt
```

---

## Troubleshooting

### Q: Why are some enrichments not running?
**A:** Check if the .md file already exists in `data/enriched/{companies,connections}/`. The enrichment script skips existing files.

**Solution:**
```bash
# Delete the file to re-enrich
rm data/enriched/companies/Company_acme.md

# Re-run enrichment
python ingest.py --enrich-only
```

### Q: Why is ingest not embedding new chunks?
**A:** If `INGEST["skip_unchanged"]` is True, identical content is skipped.

**Solution:**
```bash
# Check if content changed by inspecting the file
# If content actually changed, the chunk_id changes → will be embedded

# If you need to force re-embedding despite unchanged content:
# (Not recommended, wastes Bedrock credits)
# Set INGEST["skip_unchanged"] = False in config.py temporarily
```

### Q: How do I reset everything and start fresh?
```bash
# Delete cached snapshots
rm -rf data/api_snapshots

# Delete normalized enriched files (⚠️ caution!)
rm -rf data/enriched

# Delete backup of original unstructured enriched files if desired (⚠️ caution!)
rm -rf data/enriched_unstructured

# Delete ChromaDB
rm -rf chroma_db

# Re-run full pipeline
python ingest.py --fetch-all
```

---

## Phase 1 References

Phase 1 CSV files are preserved in `data/Basic_LinkedInDataExport_04-18-2026/` for archival purposes only. They are **not used** in Phase 2.

**Phase 1 scripts** (in `/Phase 1/parsers/` and `/Phase 1/tavily_scripts/`) are legacy and isolated; not imported by Phase 2.

**Phase 1 enrichment files** (in `/Phase 1/tavily_scripts/{Companies,Connections}/`) were migrated during initial Phase 2 setup. The current active normalized dataset is stored in `data/enriched/`, while original unstructured markdowns are preserved in `data/enriched_unstructured/`.

---

## Future Considerations

1. **Incremental enrichment:** Only new connections/companies are enriched; existing ones are skipped
2. **Archive old data:** As Phase 1 is fully migrated, the `/Phase 1` directory could be archived
3. **Content versioning:** If enrichments are updated, files will be re-chunked (chunk_id changes if content changes)
4. **Semantic drift:** Monitor query quality over time; older snapshot data may have lower semantic relevance

---

**Last Updated:** May 12, 2026  
**Status:** ✅ Production-Ready
