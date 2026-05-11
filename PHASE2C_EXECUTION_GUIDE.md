# Phase 2c Execution Plan — 25 Credit Budget

## Pre-Execution Checklist

### ✅ Skip Logic Verified

All skip mechanisms are in place to prevent re-processing:

1. **Enrichment Skip Logic** (enrich_connections_api.py, enrich_companies_api.py)
   - `file_has_content()` checks if markdown already exists with size > 0
   - `split_pending()` separates already-enriched from pending items
   - Only pending items are submitted to Tavily (saves credits!)
   - Each run only processes items missing enriched markdown

2. **Legacy Reuse** (common.py)
   - `sync_legacy_connections()` auto-matches and copies Phase 1 enrichments
   - `sync_legacy_companies()` auto-matches by normalized org name
   - Already matched: 601 connections, 645 companies (no API calls needed)

3. **Ingestion Skip Logic** (ingest.py)
   - `skip_unchanged: True` in config.py
   - ChromaDB upsert checks content_hash before re-embedding
   - Identical chunks skipped (no embedding cost)
   - Running ingest multiple times is safe

4. **API Call Limits**
   - `--max N` flag limits API calls per run
   - Tracks credits used via Tavily response
   - Progress indicator: `[{index}/{len(pending)}]`

---

## Credential Setup (25 Credit Budget)

### Load Tavily API Key from Creds

```bash
# Option 1: Load from tavily_key.json (already in creds folder)
$env:TAVILY_API_KEY = (Get-Content "data/creds/tavily_key.json" | ConvertFrom-Json).api_key

# Option 2: Verify key is loaded
python -c "import os; print('Tavily API key set' if os.getenv('TAVILY_API_KEY') else 'NOT SET')"

# Option 3: Check current usage before starting
python -c "
import os
import requests

api_key = os.getenv('TAVILY_API_KEY', '')
if api_key:
    response = requests.get(
        'https://api.tavily.com/usage',
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=30
    )
    data = response.json()
    print(f\"Account Usage: {data.get('account', {}).get('plan_usage')} / {data.get('account', {}).get('plan_limit')}\")
    print(f\"Key Usage: {data.get('key', {}).get('usage')} / {data.get('key', {}).get('limit')}\")
"
```

---

## Phase 2c Execution (3 Steps)

### Step 1: Show Enrichment Backlog (Stats Only, No API Calls)

```bash
# See how many items need enrichment — no Tavily calls
python enrichment/enrich_connections_api.py --stats
python enrichment/enrich_companies_api.py --stats
```

**Expected Output:**
```
Connections Backlog:
  Unique: 627
  Reused from Phase 1: 601
  Already enriched: 601
  Pending: 26
  Estimated credits: 52 (2 per connection)

Companies Backlog:
  Unique: 699
  Reused from Phase 1: 645
  Already enriched: 645
  Pending: 54
  Estimated credits: 54 (1 per company)

Total pending: 80 items
Total estimated: 106 credits
Available: 25 credits ← BUDGET CONSTRAINT
```

---

### Step 2: Strategic Enrichment with Credit Budget

**Problem:** 80 pending items need 106 credits, but we only have 25.

**Solution:** Enrich strategically to maximize value:

#### Option A: Enrich Only Connections (Lower Cost, More Recent)
```bash
# Connections: 26 pending × 2 credits = 52 credits needed
# We can only do ~12 connections with 25 credits

python enrichment/enrich_connections_api.py --max 12
# Stops after 12 calls (~24 credits)
```

**Why:** Connections are more recent (latest = May 6, 2026), so higher quality data.

#### Option B: Enrich Only Companies (Higher Volume, Cheaper)
```bash
# Companies: 54 pending × 1 credit = 54 credits needed  
# We can do ~25 companies with 25 credits

python enrichment/enrich_companies_api.py --max 25
# Stops after 25 calls (~25 credits)
```

**Why:** Companies are 1 credit each, so more volume with same budget.

#### Option C: Balanced Approach (Recommended)
```bash
# Enrich ~11 connections + ~13 companies = ~24 credits
python enrichment/enrich_connections_api.py --max 11
python enrichment/enrich_companies_api.py --max 13
```

**Why:** Balanced enrichment of both most important entity types.

---

### Step 3: Monitor Credit Usage During Run

```bash
# Watch the credits tick down
python enrichment/enrich_connections_api.py --max 11

# Each line shows: [1/11] Name
#                  Query: ...
#                  ✓ Saved → Connection_name.md
#                  (repeats 11 times, showing credit drain)

# Check final usage
python enrichment/enrich_connections_api.py --stats
# Shows: "Current Tavily key usage: X/100" (or your limit)
```

---

### Step 4: Ingest Enriched Data into ChromaDB

```bash
# Dry run first (safe, no embedding cost)
python ingest.py --dry-run

# Expected output:
# [3/4] Parsing Snapshots
#   [PROFILE] ✓ X chunks
#   [CONNECTIONS] ✓ Y chunks (includes enriched MDs)
#   [COMPANY_FOLLOWS] ✓ Z chunks (includes enriched MDs)
#   ...
# Total chunks: ~2500+

# Now ingest for real (embedding via Bedrock, not Tavily)
python ingest.py --ingest-only
# Upserts chunks to ChromaDB collections
```

---

### Step 5: Verify ChromaDB Population

```bash
# Check what's in ChromaDB
python ingest.py --stats

# Expected output:
# my_profile        : N chunks
# my_network        : M chunks (connections + enriched)
# companies         : K chunks (companies + enriched)
# communications    : L chunks
# jobs              : J chunks
# my_activity       : A chunks
# TOTAL             : ~2500+ chunks
```

---

## Credit Management Strategy

### Before Running Enrichment

1. **Get current usage:**
   ```bash
   python enrichment/enrich_connections_api.py --stats
   ```

2. **Calculate max safe calls:**
   - Budget: 25 credits
   - Connections: 2 credits each → max ~12 calls
   - Companies: 1 credit each → max ~25 calls
   - Mix strategically

3. **Decide enrichment strategy:**
   - Option A: All budget on connections (12 items)
   - Option B: All budget on companies (25 items)
   - Option C: Split balanced (11 connections + 13 companies)

### During Enrichment Run

1. **Watch for failures:**
   - `✓ Saved` = success, credit used
   - `✗ Failed` = error, NO credit used (safe to retry)

2. **Monitor progress:**
   - Script shows `[N/{total}]` to track position
   - Shows credits reported per call
   - Accumulates total at end

### After Enrichment Run

1. **Check usage again:**
   ```bash
   python enrichment/enrich_connections_api.py --stats
   # Shows: "Estimated key remaining: XX"
   ```

2. **Verify enriched files created:**
   ```bash
   ls -la data/enriched/connections/*.md
   ls -la data/enriched/companies/*.md
   ```

---

## Safety Features (Why We Won't Waste Credits)

### ✅ Enrichment Scripts

```python
# 1. Skip already-processed items
if file_has_content(output_path(connection)):
    enriched += 1
else:
    pending.append(connection)  # Only this is enriched

# 2. Legacy reuse (automatic, no cost)
reused = sync_legacy_connections(connections)
# Result: 601 connections auto-matched, 0 cost

# 3. Max call limit
for connection in pending:
    if max_calls > 0 and calls_made >= max_calls:
        break  # Stop when limit reached
    # API call...

# 4. Delay between calls
time.sleep(0.5)  # Rate limiting
```

### ✅ Ingest Script

```python
# 1. Skip unchanged chunks
if INGEST["skip_unchanged"]:  # True in config
    if chunk.content_hash in existing_hashes:
        continue  # No re-embedding cost

# 2. Batch processing (efficient embedding)
batch_size = 50
for batch in chunks_batched:
    embed_and_upsert(batch)  # Bedrock, not Tavily
```

---

## Quick Reference: Commands for 25-Credit Budget

```bash
# Set API key
$env:TAVILY_API_KEY = (Get-Content "data/creds/tavily_key.json" | ConvertFrom-Json).api_key

# Check backlog (no cost)
python enrichment/enrich_connections_api.py --stats
python enrichment/enrich_companies_api.py --stats

# Enrich strategically (CHOOSE ONE):

# Option A: 12 connections (~24 credits)
python enrichment/enrich_connections_api.py --max 12

# Option B: 25 companies (~25 credits)
python enrichment/enrich_companies_api.py --max 25

# Option C: Balanced (~24 credits)
python enrichment/enrich_connections_api.py --max 11
python enrichment/enrich_companies_api.py --max 13

# Then ingest (safe, uses Bedrock not Tavily)
python ingest.py --dry-run   # Verify first
python ingest.py --ingest-only

# Verify
python ingest.py --stats
```

---

## Timeline Estimate

- **Stats check:** 5 seconds
- **11 connection enrichments:** 2-3 minutes (Tavily API + markdown building)
- **13 company enrichments:** 2-3 minutes
- **Parsing all snapshots:** 10-15 seconds
- **Embedding and ingestion:** 5-10 minutes (depends on Bedrock quota)
- **Total:** ~15-20 minutes

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `TAVILY_API_KEY not set` | `$env:TAVILY_API_KEY = (Get-Content ...` |
| `Connection timeout` | Check internet, retry with shorter `--max` |
| `404 No data found` | Some snapshot domains are empty for this profile — OK |
| `Bedrock throttled` | Wait a minute, then re-run `python ingest.py --ingest-only` |
| `Credits exhausted mid-run` | Script stops gracefully; partially enriched items saved |

---

## Next Phase

After Phase 2c completes:
- Query/Ask Pipeline Ready: `python query/ask.py "your question"`
- ChromaDB populated with:
  - 627 connections (601 Phase 1 + ~12 new from budget)
  - 699 companies (645 Phase 1 + ~13-25 new from budget)
  - Full profile, education, certifications, skills, etc.
