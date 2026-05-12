# Phase 2 Ingestion Pipeline — Audit Report
**Date:** May 12, 2026  
**Status:** ✅ VERIFIED WITH MINOR CLEANUP NEEDED

---

## Executive Summary

The Phase 2 ingestion pipeline is **correctly implemented** with proper skip logic, clean separation from Phase 1, and the correct workflow architecture. However, there are **3 minor cleanup items**:

1. Remove unused CSV references from `config.py` (Phase 1 bootstrap definitions)
2. Clean up Phase 1 migration functions that are now one-time-only (optional but recommended)
3. Document the immutable workflow contract for future maintainers

---

## 1. Skip Logic Verification ✅

### VectorStore.upsert() — Content Hash Deduplication

**File:** [db/vector_store.py](db/vector_store.py#L162-L193)

**Status:** ✅ **CORRECTLY IMPLEMENTED**

The `upsert()` method:
- Checks if `INGEST["skip_unchanged"]` is enabled in [config.py](config.py#L109)
- Groups chunks by collection for batch processing
- For each collection:
  - Queries existing chunk IDs using `_existing_ids()` (batched in groups of 500)
  - Retrieves content hashes for existing IDs using `_existing_hashes()`
  - Compares incoming `chunk.content_hash` with stored hash
  - Skips if chunk_id exists AND content_hash matches (avoids re-embedding cost)
  - Only embeds and upserts new/modified chunks

**Code Flow:**
```python
# From vector_store.py:162-180
if INGEST["skip_unchanged"]:
    existing_ids = self._existing_ids(collection, [c.chunk_id for c in coll_chunks])
    existing_hashes = self._existing_hashes(collection, list(existing_ids))
    
    for chunk in coll_chunks:
        if chunk.chunk_id in existing_ids:
            stored_hash = existing_hashes.get(chunk.chunk_id)
            if stored_hash == chunk.content_hash:
                stats["skipped"] += 1
                continue  # ← Skip unchanged chunks
        to_upsert.append(chunk)
```

**Config Setting:** [config.py](config.py#L109)
```python
INGEST = {
    "skip_unchanged": True,  # ← Enabled for Bedrock cost optimization
    ...
}
```

**Impact:** ✅ Prevents re-embedding identical chunks; saves Bedrock costs on incremental ingests

---

## 2. Phase 1 Leftovers — Code Audit ✅

### Summary
- **Phase 1 CSV references:** Exist in `config.py` but **NOT imported or used** in Phase 2 scripts
- **Phase 1 Python scripts:** Isolated in `/Phase 1/parsers/` and `/Phase 1/tavily_scripts/`
- **Phase 1 migration:** Handled via `sync_legacy_*()` functions in enrichment scripts (one-time-only)

### Detailed Findings

#### A. CSV References in config.py
**File:** [config.py](config.py#L13-L28)

**Status:** ⚠️ **UNUSED but KEPT for documentation**

```python
CSV = {
    "profile":              DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Profile.csv",
    "positions":            DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Positions.csv",
    # ... 13 more CSV paths
}
```

**Audit Result:**
- ❌ No references to `CSV` dictionary in Phase 2 scripts ([ingest.py](ingest.py), [enrichment/*.py](enrichment/), [query/ask.py](query/ask.py), [ingestion/*.py](ingestion/))
- ✅ CSV references only appear in Phase 1 isolated scripts:
  - Phase 1/parsers/parse_profile.py (4 refs)
  - Phase 1/parsers/parse_activity.py (5 refs)
  - Phase 1/parsers/parse_network.py (1 ref)
  - Phase 1/parsers/parse_companies.py (1 ref)
  - Phase 1/parsers/parse_messages.py (1 ref)

**Recommendation:** Keep for reference, but could be moved to Phase 1 config or marked as deprecated

---

#### B. Enrichment Scripts — Phase 1 Migration
**Files:** [enrichment/enrich_companies_api.py](enrichment/enrich_companies_api.py#L327), [enrichment/enrich_connections_api.py](enrichment/enrich_connections_api.py#L179)

**Status:** ✅ **CORRECTLY ISOLATED — One-Time Migration Only**

Both scripts call `sync_legacy_*()` functions:
```python
# From enrich_companies_api.py:327
reused_legacy = sync_legacy_companies(companies, OUTPUT_DIR)
```

**What it does:**
- Scans `Phase 1/tavily_scripts/Companies/` for legacy enrichment markdown
- Indexes files by organization name (with alias matching)
- Copies **only missing** enriched files to `data/enriched/companies/`
- Skips if target file already exists

**Behavior:**
- ✅ **First run:** Copies all Phase 1 legacy enrichments (~670 companies, ~60 connections)
- ✅ **Subsequent runs:** Does nothing (all files already exist)
- ✅ **No re-processing:** New enrichments only from Tavily API

**Code Pattern:**
```python
def sync_legacy_companies(...) -> int:
    # ... index legacy files ...
    for company in companies:
        target_path = output_dir / f"Company_{slugify_text(company['organization'])}.md"
        if file_has_content(target_path):
            continue  # ← Skip if already enriched
        legacy_path = legacy_index.get(normalize_lookup_key(...))
        if legacy_path and file_has_content(legacy_path):
            shutil.copy2(legacy_path, target_path)  # ← Copy only if missing
    return copied
```

---

#### C. Snapshot Parsing — No Phase 1 References
**File:** [ingest.py](ingest.py#L127-160)

**Status:** ✅ **CLEAN — Parses snapshots only, no CSV fallback**

All 14 domain parsers:
```python
PARSERS = {
    "PROFILE": parse_profile_snapshot,           # ← Snapshot only
    "POSITIONS": parse_positions_snapshot,       # ← Snapshot only
    "CONNECTIONS": parse_connections_snapshot,  # ← Markdown-only (Tavily)
    "COMPANY_FOLLOWS": parse_companies_snapshot, # ← Markdown-only (Tavily)
    # ... etc
}
```

No fallback to CSV parsing; Phase 1 CSVs completely bypassed in Phase 2 pipeline.

---

## 3. Workflow Validation ✅

**Requested Workflow:**
```
Fetch all snapshot domains 
    ↓
Enrich only companies & connections (with skip logic)
    ↓
Chunk them
    ↓
Upload to ChromaDB
```

**Actual Implementation in [ingest.py](ingest.py#L688-730):**

```python
# [1/4] Fetch
if args.fetch_all or args.fetch_only or ...:
    run_snapshot_fetcher(skip_cache=args.skip_cache)  # ← Fetch all domains

# [2/4] Enrich
if not args.ingest_only and not args.dry_run:
    run_enrichment_scripts()  # ← Calls enrich_companies_api.py + enrich_connections_api.py

# [3/4] Parse
all_chunks = parse_all_snapshots(verbose=args.verbose)  # ← Chunks all 14 domains

# [4/4] Ingest
ingest_chunks(all_chunks, dry_run=False)  # ← Upserts to ChromaDB with skip logic
```

**Status:** ✅ **MATCHES EXACTLY**

### Enrichment Skip Logic

**enrich_companies_api.py:**
```python
def split_pending(companies: list[dict]) -> tuple[list[dict], int]:
    pending = []
    for company in companies:
        if file_has_content(output_path(company)):  # ← Skip if file exists
            enriched += 1
        else:
            pending.append(company)  # ← Only enrich new ones
    return pending, enriched
```

**enrich_connections_api.py:**
- Identical `split_pending()` logic
- Reads from CONNECTIONS snapshot (unique by URL)
- Only calls Tavily API for missing enrichments

**Status:** ✅ **CORRECT — Prevents redundant API calls and quota waste**

---

## 4. Collections Mapping — Correct

| Domain(s) | Collection | Source | Chunking |
|-----------|-----------|--------|----------|
| PROFILE, POSITIONS, EDUCATION, SKILLS, CERTIFICATIONS, LANGUAGES, PUBLICATIONS | `my_profile` | Snapshot JSON | Direct from elements |
| JOB_APPLICATIONS, SAVED_JOBS, SAVED_JOB_ALERTS | `jobs` | Snapshot JSON | Per-row with entity_id hash |
| JOB_APPLICANT_SAVED_ANSWERS | `my_activity` | Snapshot JSON | Per-row |
| CONNECTIONS | `my_network` | **Markdown only** (CONNECTIONS_TAVILY) | From `data/enriched/connections/*.md` |
| COMPANY_FOLLOWS | `companies` | **Markdown only** (COMPANY_FOLLOWS_TAVILY) | From `data/enriched/companies/*.md` |
| INBOX | `communications` | Snapshot JSON | Per-conversation |

**Status:** ✅ **CORRECT — Avoids base+enriched duplication for companies/connections**

---

## 5. Incremental Ingest Pattern — Ready for Production

When new data arrives:

```bash
# Step 1: Fetch latest snapshots
python ingest.py --fetch-only

# Step 2: Enrich new companies/connections only (Tavily skip logic active)
python ingest.py --enrich-only

# Step 3: Ingest all (VectorStore skip_unchanged logic active)
python ingest.py --ingest-only

# Result:
# - ✅ No redundant Tavily API calls (enrichment script skips existing files)
# - ✅ No redundant embeddings (VectorStore skips unchanged content hashes)
# - ✅ All 6 collections updated with new + existing data
```

**Status:** ✅ **CORRECT — Cost-optimized, no duplicate processing**

---

## Issues Found & Recommendations

### ✅ VERIFIED — No Issues with Skip Logic
- `VectorStore.upsert()` correctly implements content hash deduplication
- Enrichment scripts correctly skip already-enriched files
- Config setting `skip_unchanged: True` is enabled

### ⚠️ MINOR CLEANUP — Phase 1 References
1. **CSV references in config.py** (not used, but harmless)
   - **Fix:** Remove or move to Phase 1 config file
   - **Impact:** Low — unused but kept for documentation
   
2. **sync_legacy_* functions** (one-time migration, could be removed)
   - **Current state:** Still in enrichment scripts; do nothing after first run
   - **Fix:** Could be removed after confirming all Phase 1 files copied
   - **Impact:** Low — already idempotent

3. **Phase 1 directory** (isolated, not imported)
   - **Current state:** Self-contained; no imports from Phase 2
   - **Fix:** Could be archived after confirming data migration complete
   - **Impact:** Low — currently harmless

---

## Recommendations for Maintainers

### 1. Document the Immutable Contract
Add this to [README.md](README.md) or a new [ARCHITECTURE.md](ARCHITECTURE.md):

```markdown
## Ingestion Workflow (Immutable Contract)

The Phase 2 pipeline MUST follow this sequence:

1. **Fetch snapshots** from LinkedIn Portability API
   - All 14 domains via `ingestion/snapshot_api.py`
   - Cached locally in `data/api_snapshots/{DOMAIN}/`

2. **Enrich** companies & connections only
   - Via Tavily Search API
   - Skip logic: if `data/enriched/{companies,connections}/*.md` exists, skip
   - Output: `data/enriched/{companies,connections}/*.md`

3. **Parse** all snapshots into DocumentChunks
   - Snapshots → JSON chunks for 12 domains (direct parse)
   - Enriched markdown → chunks for 2 domains (companies, connections)
   - No fallback to Phase 1 CSVs

4. **Chunk & Embed** all 14 domains
   - Bedrock embedding model (Titan or Cohere)
   - Content hash deduplication (skip if unchanged)

5. **Upsert** to ChromaDB
   - VectorStore.upsert() with skip_unchanged=True
   - Batch processing by collection
   - Skip chunks with identical content_hash

### Why This Matters
- Prevents redundant Tavily API calls (quota management)
- Avoids re-embedding unchanged chunks (cost optimization)
- Eliminates base+enriched duplication (semantic deduplicated search)
```

### 2. Optional: Clean Up Phase 1 References (Non-Urgent)

**If you decide to remove Phase 1 remnants:**

```python
# From config.py — Remove if Phase 1 fully archived
CSV = { ... }  # ← Could delete if Phase 1 directory archived

# From enrichment/common.py — Remove if Phase 1 migration confirmed complete
def sync_legacy_companies(...) -> int:  # ← Could delete after first run verification
def sync_legacy_connections(...) -> int: # ← Could delete after first run verification
```

**Verification before deletion:**
```bash
# Count enriched files from Phase 1 vs total
ls -la data/enriched/companies/ | wc -l
ls -la data/enriched/connections/ | wc -l

# Check if counts match Phase 1 legacy + Phase 2 Tavily enrichments
wc -l Phase\ 1/tavily_scripts/Companies/*.md
wc -l Phase\ 1/tavily_scripts/Connections/*.md
```

---

## Conclusion

✅ **The Phase 2 ingestion pipeline is correctly implemented.**

- **Skip logic:** ✅ Properly implemented at both enrichment and upsert stages
- **Phase 1 isolation:** ✅ Complete; no active dependencies on Phase 1 code
- **Workflow:** ✅ Matches the requested architecture exactly
- **Incremental ingest ready:** ✅ Cost-optimized for future data updates

**No blocking issues.** The 3 minor cleanup items are optional and non-critical.

---

## Appendix: Skip Logic Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ New Snapshot Data Arrives                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    [FETCH]
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
    [14 Snapshots]          [ENRICH: Companies & Connections]
          │                             │
          │                    ┌────────┴──────────┐
          │                    ▼                   ▼
          │          [split_pending()] ← ← ← ← ← ← SKIP if exists
          │                    │
          │          ┌─────────┴──────────┐
          │          ▼                    ▼
          │      [pending]            [enriched]
          │      (new rows)           (skip)
          │          │
          │      [Tavily API]
          │          │
          ▼          ▼
    [PARSE Snapshots + Enriched MD]
          │
    [All chunks with content_hash]
          │
    [UPSERT to ChromaDB]
          │
     ┌────┴────────────────────────────────┐
     ▼                                      ▼
[Existing chunk_id?]                   [New chunk_id]
     │                                      │
  YES│                                      │
     ▼                                      ▼
[Compare content_hash]             [Embed & Insert]
     │                                      
  SAME│ DIFF
     ▼  ▼
  [SKIP][Embed & Upsert]

────────────────────────────────────────────────────
✅ Result: Zero redundant API calls + zero redundant embeddings
```

---

**Generated:** 2026-05-12  
**Pipeline Status:** ✅ Production-Ready
