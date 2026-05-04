# Phase 1 — CSV-Based Ingestion (Archived)

This folder contains all Phase 1 scripts and workflows, archived after migration to Phase 2 (LinkedIn Portability Snapshot API).

## Contents

### `ingest_phase1.py`
Original ingestion orchestrator that:
- Parsed LinkedIn CSV exports (Profile.csv, Connections.csv, etc.)
- Supported dry-run, selective ingestion, and stats display
- Routed data to appropriate ChromaDB collections

Usage:
```bash
python Phase 1/ingest_phase1.py --dry-run
python Phase 1/ingest_phase1.py --only profile
python Phase 1/ingest_phase1.py --stats
```

### `parsers/`
Module containing domain-specific CSV parsers:
- `parse_profile.py` — Profile, positions, education, skills, certifications, languages, publications
- `parse_network.py` — Connections CSV + Tavily connection enrichment MDs
- `parse_companies.py` — Company follows CSV + Tavily company enrichment MDs
- `parse_activity.py` — Job applications, saved jobs, likes, saved answers
- `parse_messages.py` — Full message threads from CSV

Each parser took raw CSV data and produced `DocumentChunk` objects for ChromaDB ingestion.

### `tavily_scripts/`
Tavily enrichment scripts for Phase 1:
- `search_connections.py` — Enriched connection profiles via Tavily Search API (reads from Connections.csv)
- `extract_companies.py` — Enriched company profiles via Tavily Extract API (reads from Company Follows.csv)
- Subdirectories: `Companies/`, `Connections/` — cached enrichment markdown files

**Note**: Phase 2 replaces these with API-sourced equivalents (`enrichment/enrich_connections_api.py`, `enrichment/enrich_companies_api.py`).

## Migration to Phase 2

Phase 2 eliminates CSV dependency entirely:
1. **Data source**: LinkedIn Portability Snapshot API (requires access token)
2. **Caching**: JSON snapshots cached locally (`data/api_snapshots/`)
3. **Enrichment**: Tavily scripts adapted for API-sourced data (no CSV columns)
4. **Ingestion**: Unified pipeline in new `ingest.py` (Phase 2 only)

## Why Archive?

- CSVs are static exports; API provides fresh, current data
- API snapshots enable automated periodic updates (future: changelog polling)
- Cleaner codebase by separating Phase 1 (dev & test) from Phase 2 (production)

## Reference

- See main [README.md](../README.md) for Phase 2 workflows and documentation
- Config reference: [config.py](../config.py) contains legacy CSV paths (kept for reference)
