# Automated Daily Data Synchronization

## Overview

The `sync_all_data.py` script provides a comprehensive daily update pipeline that:
- ✅ Fetches fresh LinkedIn snapshots (if data >24h old)
- ✅ Enriches new connections/companies with Tavily
- ✅ Ingests everything into ChromaDB
- ✅ Tracks state and progress
- ✅ Can be scheduled with cron/Task Scheduler

## Quick Start

### Manual Execution

```bash
# Set credentials
export LINKEDIN_PORTABILITY_TOKEN="your_token_here"
export TAVILY_API_KEY="your_key_here"

# Full sync (fetch + enrich + ingest)
python sync_all_data.py

# Or with budget limit
python sync_all_data.py --max-credits 25

# Check status without running
python sync_all_data.py --status

# Dry run first
python sync_all_data.py --dry-run
```

## Scheduling for Daily Execution

### Option 1: Windows Task Scheduler (Recommended for Windows)

#### Step 1: Create a batch wrapper script

Create `C:\Dev\Personal\GitHub\LinkedIn-LLM\run_daily_sync.bat`:

```batch
@echo off
REM Daily LinkedIn data sync
REM Set working directory
cd /d C:\Dev\Personal\GitHub\LinkedIn-LLM

REM Load environment
call .venv\Scripts\activate.bat

REM Set credentials from secure file or environment
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Content data/creds/linkedin_api_creds.json | ConvertFrom-Json | Select-Object -ExpandProperty access_token"') do set LINKEDIN_PORTABILITY_TOKEN=%%i
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Content data/creds/tavily_key.json | ConvertFrom-Json | Select-Object -ExpandProperty api_key"') do set TAVILY_API_KEY=%%i

REM Run sync with max 25 credits
python sync_all_data.py --max-credits 25

REM Log result
echo Sync completed at %date% %time% >> logs/sync_log.txt
```

#### Step 2: Schedule with Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)
2. Click "Create Basic Task"
3. Name: "LinkedIn Daily Data Sync"
4. Trigger: "Daily" at desired time (e.g., 2:00 AM)
5. Action: Start program
   - Program: `C:\Dev\Personal\GitHub\LinkedIn-LLM\run_daily_sync.bat`
   - Start in: `C:\Dev\Personal\GitHub\LinkedIn-LLM`
6. Conditions: Optional (uncheck "Stop if running on battery")
7. Click Create

---

### Option 2: Linux/Mac Cron

Create `crontab` entry:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 2:00 AM
0 2 * * * cd /path/to/LinkedIn-LLM && \
  LINKEDIN_PORTABILITY_TOKEN=$(jq -r '.access_token' data/creds/linkedin_api_creds.json) \
  TAVILY_API_KEY=$(jq -r '.api_key' data/creds/tavily_key.json) \
  /usr/bin/python3 sync_all_data.py --max-credits 25 >> logs/sync_log.txt 2>&1
```

---

### Option 3: GitHub Actions (Cloud-Based, Recommended for Always-On)

Create `.github/workflows/daily-sync.yml`:

```yaml
name: Daily Data Sync

on:
  schedule:
    # Run daily at 2:00 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run daily sync
        env:
          LINKEDIN_PORTABILITY_TOKEN: ${{ secrets.LINKEDIN_PORTABILITY_TOKEN }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
        run: python sync_all_data.py --max-credits 25
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: sync-logs
          path: logs/
```

---

## State Tracking

The script maintains a `.sync_state.json` file that tracks:

```json
{
  "last_fetch": "2026-05-12T02:00:00",
  "last_enrichment": "2026-05-12T02:03:00",
  "last_ingest": "2026-05-12T02:08:00",
  "last_full_sync": "2026-05-12T02:08:00",
  "connections_enriched_total": 26,
  "companies_enriched_total": 54,
  "credits_used_total": 106,
  "runs": [
    {
      "timestamp": "2026-05-12T02:08:00",
      "status": "success"
    }
  ]
}
```

## Usage Examples

### Daily Sync with Budget Constraint
```bash
python sync_all_data.py --max-credits 25
```

### Force Refresh (Ignore 24h Cache)
```bash
python sync_all_data.py --force-refresh
```

### Skip Enrichment (Only Fetch + Ingest)
```bash
python sync_all_data.py --skip-enrich
```

### Dry Run (No Changes)
```bash
python sync_all_data.py --dry-run
```

### Check Status
```bash
python sync_all_data.py --status
```

Output:
```
======================================================================
  Data Synchronization Status
======================================================================

Last Fetch:                    2026-05-12T02:00:00
Data Status:                   🟢 FRESH
Last Enrichment:               2026-05-12T02:03:00
Last Ingestion:                2026-05-12T02:08:00
Last Full Sync:                2026-05-12T02:08:00

Pending Enrichments:
  Connections:                 14 pending
  Companies:                   28 pending
  Estimated Tavily credits:    ~56

Lifetime Stats:
  Total connections enriched:  26
  Total companies enriched:    54
  Total Tavily credits used:   106
  Total sync runs:             1

Tavily Account Status:
  Key usage:                   106 / 100
  Account plan:                800 / 1000

======================================================================
```

## Automation Flow

```
Daily Trigger (2:00 AM)
    ↓
Is data >24h old?
├─ Yes → Fetch fresh snapshots
└─ No  → Skip fetch, use cache
    ↓
Count pending enrichments
    ├─ Connections: N pending
    └─ Companies: M pending
    ↓
Respect credit budget
├─ Prioritize connections (2 credits each)
└─ Fill remaining budget with companies (1 credit each)
    ↓
Enrich new entities
    ↓
Parse all snapshots + enriched markdown
    ↓
Chunk with domain-specific settings
    ↓
Upsert to ChromaDB (skip_unchanged = smart reuse)
    ↓
Update .sync_state.json with progress
    ↓
Log results and completion time
```

## Logging

Create a `logs/` directory for output:

```bash
mkdir logs
```

Logs are appended to `logs/sync_log.txt` with timestamps.

## Troubleshooting

### "LINKEDIN_PORTABILITY_TOKEN not set"
- Ensure credentials are in `data/creds/` and script loads them
- Or set environment variables before running

### "Data Status: STALE"
- Data hasn't been fetched in >24h
- Script will automatically fetch fresh data on next run
- Use `--force-refresh` to force immediate fetch

### "Pending enrichments high"
- New connections/companies added since last sync
- Adjust `--max-credits` to control enrichment scope
- Or remove `--max-credits` to enrich everything (may use many credits)

### "Tavily credits exhausted"
- Track usage in `.sync_state.json`
- Reduce `--max-credits` limit
- Wait for monthly budget reset

## Advanced: Custom Scheduling

### Run every 12 hours
**Linux/Mac:**
```bash
0 */12 * * * python sync_all_data.py
```

**Windows Task Scheduler:**
- Repeat task every 12 hours

### Run multiple times daily with different budgets
**Morning sync** (generous budget):
```bash
0 2 * * * python sync_all_data.py --max-credits 50
```

**Evening sync** (conservative):
```bash
0 18 * * * python sync_all_data.py --max-credits 10
```

### Skip enrichment on weekends
**Linux/Mac:**
```bash
# Weekday: full sync
0 2 * * 1-5 python sync_all_data.py --max-credits 25

# Weekend: fetch + ingest only (no enrichment cost)
0 2 * * 0,6 python sync_all_data.py --skip-enrich
```

## Summary

| Feature | Benefit |
|---------|---------|
| **Automated Fetch** | New data available within 24 hours |
| **Smart Cache** | Avoid redundant API calls |
| **Incremental Enrichment** | Only process new connections/companies |
| **Budget Control** | `--max-credits` limits Tavily spend |
| **State Tracking** | Know exactly what's been processed |
| **Scheduling** | Windows Task Scheduler, cron, or GitHub Actions |
| **Error Resilient** | Partial progress saved even if failures occur |

With `sync_all_data.py`, your LinkedIn data stays fresh automatically! 🚀
