#!/usr/bin/env python3
"""
Daily Data Synchronization Orchestrator

Automatically fetches fresh LinkedIn data, enriches new connections/companies,
and ingests everything into ChromaDB. Can be run via cron/scheduler for daily updates.

Usage:
    export LINKEDIN_PORTABILITY_TOKEN="YOUR_TOKEN"
    export TAVILY_API_KEY="YOUR_KEY"
    
    # Full daily sync (fetch + enrich + ingest)
    python sync_all_data.py
    
    # Dry run (no changes)
    python sync_all_data.py --dry-run
    
    # Force refresh (ignore cache)
    python sync_all_data.py --force-refresh
    
    # Skip enrichment (only fetch + ingest)
    python sync_all_data.py --skip-enrich
    
    # Show status without running
    python sync_all_data.py --status
"""

import os
import sys
import json
import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import PORTABILITY_API
from enrichment.common import get_tavily_usage, resolve_tavily_api_key


# ── State Management ──────────────────────────────────────────────────────────

STATE_FILE = REPO_ROOT / ".sync_state.json"
SNAPSHOT_CACHE_DIR = REPO_ROOT / "data" / "api_snapshots"
ENRICHED_DIR = REPO_ROOT / "data" / "enriched"


def load_state() -> Dict[str, Any]:
    """Load synchronization state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "last_fetch": None,
        "last_enrichment": None,
        "last_ingest": None,
        "last_full_sync": None,
        "connections_enriched_total": 0,
        "companies_enriched_total": 0,
        "credits_used_total": 0,
        "runs": [],
    }


def save_state(state: Dict[str, Any]) -> None:
    """Save synchronization state to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def is_data_stale(hours: int = 24) -> bool:
    """Check if cached snapshots are older than specified hours."""
    state = load_state()
    last_fetch = state.get("last_fetch")
    
    if not last_fetch:
        return True  # Never fetched before
    
    try:
        last_fetch_dt = datetime.fromisoformat(last_fetch)
        age = datetime.now() - last_fetch_dt
        return age > timedelta(hours=hours)
    except Exception:
        return True


def count_pending_enrichments() -> tuple[int, int]:
    """Count pending connections and companies that need enrichment."""
    pending_connections = 0
    pending_companies = 0
    
    # Count connections needing enrichment — check Phase 2 output only.
    # The enrichment scripts handle Phase 1 → Phase 2 legacy copy internally.
    conn_enriched_dir = ENRICHED_DIR / "connections"
    enriched_conn_files = set()
    if conn_enriched_dir.exists():
        enriched_conn_files = {f.stem for f in conn_enriched_dir.glob("*.md")}
    
    from enrichment.enrich_connections_api import load_connections
    from enrichment.common import slugify_linkedin_url, slugify_text
    try:
        connections = load_connections()
        pending_connections = len([c for c in connections 
                                  if f"Connection_{slugify_linkedin_url(c['url'])}" not in enriched_conn_files])
    except Exception:
        pending_connections = 0
    
    # Count companies needing enrichment — check Phase 2 output only.
    comp_enriched_dir = ENRICHED_DIR / "companies"
    enriched_comp_files = set()
    if comp_enriched_dir.exists():
        enriched_comp_files = {f.stem for f in comp_enriched_dir.glob("*.md")}
    
    from enrichment.enrich_companies_api import load_companies
    try:
        companies = load_companies()
        pending_companies = len([c for c in companies 
                                if f"Company_{slugify_text(c['organization'])}" not in enriched_comp_files])
    except Exception:
        pending_companies = 0
    
    return pending_connections, pending_companies


def show_status() -> None:
    """Display current synchronization status."""
    state = load_state()
    stale = is_data_stale()
    pending_conn, pending_comp = count_pending_enrichments()
    
    print("\n" + "="*70)
    print("  Data Synchronization Status")
    print("="*70 + "\n")
    
    print(f"Last Fetch:                    {state.get('last_fetch', 'Never')}")
    print(f"Data Status:                   {'[STALE]' if stale else '[FRESH]'} (>24h old)" if stale else "Data Status:                   [FRESH]")
    print(f"Last Enrichment:               {state.get('last_enrichment', 'Never')}")
    print(f"Last Ingestion:                {state.get('last_ingest', 'Never')}")
    print(f"Last Full Sync:                {state.get('last_full_sync', 'Never')}")
    print(f"\nPending Enrichments:")
    print(f"  Connections:                 {pending_conn} pending")
    print(f"  Companies:                   {pending_comp} pending")
    print(f"  Estimated Tavily credits:    ~{pending_conn * 2 + pending_comp}")
    
    print(f"\nLifetime Stats:")
    print(f"  Total connections enriched:  {state.get('connections_enriched_total', 0)}")
    print(f"  Total companies enriched:    {state.get('companies_enriched_total', 0)}")
    print(f"  Total Tavily credits used:   {state.get('credits_used_total', 0)}")
    print(f"  Total sync runs:             {len(state.get('runs', []))}")
    
    tavily_key = resolve_tavily_api_key()
    if tavily_key:
        usage = get_tavily_usage(tavily_key)
        if usage:
            key_usage = usage.get("key", {})
            account_usage = usage.get("account", {})
            print(f"\nTavily Account Status:")
            print(f"  Key usage:                   {key_usage.get('usage', '?')} / {key_usage.get('limit', '?')}")
            print(f"  Account plan:                {account_usage.get('plan_usage', '?')} / {account_usage.get('plan_limit', '?')}")
    
    print("\n" + "="*70 + "\n")


# ── Orchestration ─────────────────────────────────────────────────────────────

def run_fetch(force_refresh: bool = False) -> bool:
    """Fetch fresh snapshots from LinkedIn API."""
    print("\n[1/3] Fetching Snapshots")
    print("="*70 + "\n")
    
    # Check if data is stale
    if not force_refresh and not is_data_stale():
        print("  [OK] Snapshots are fresh (<24h), skipping fetch")
        print("  (use --force-refresh to ignore cache)\n")
        return True
    
    cmd = [sys.executable, "ingestion/snapshot_api.py", "--fetch-all"]
    if force_refresh:
        cmd.append("--skip-cache")
    
    print(f"  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    
    if result.returncode != 0:
        print("\n  [ERROR] Fetch failed")
        return False
    
    # Update state
    state = load_state()
    state["last_fetch"] = datetime.now().isoformat()
    save_state(state)
    
    print("\n  [OK] Fetch complete")
    return True


def run_enrichment(max_credits: Optional[int] = None, dry_run: bool = False) -> tuple[bool, int]:
    """Enrich pending connections and companies."""
    print("\n[2/3] Enriching New Entities")
    print("="*70 + "\n")
    
    # In dry-run mode, just report what would be enriched without calling Tavily
    if dry_run:
        pending_conn, pending_comp = count_pending_enrichments()
        print(f"  [DRY RUN] Would enrich {pending_conn} connections and {pending_comp} companies")
        print(f"  [DRY RUN] Estimated cost: ~{pending_conn * 2 + pending_comp} Tavily credits\n")
        return True, 0
    
    # Check Tavily key before attempting enrichment
    tavily_key = resolve_tavily_api_key()
    if not tavily_key:
        print("  [WARN] TAVILY_API_KEY not set — skipping enrichment")
        print("  Set TAVILY_API_KEY env var or add data/creds/tavily_key.json to enable enrichment\n")
        return True, 0
    
    pending_conn, pending_comp = count_pending_enrichments()
    
    if pending_conn == 0 and pending_comp == 0:
        print("  [OK] No pending enrichments")
        return True, 0
    
    estimated_cost = pending_conn * 2 + pending_comp
    print(f"  Pending enrichments:")
    print(f"    Connections: {pending_conn} (2 credits each)")
    print(f"    Companies: {pending_comp} (1 credit each)")
    print(f"    Total estimated: {estimated_cost} credits\n")
    
    # Determine enrichment strategy
    if max_credits and estimated_cost > max_credits:
        print(f"  [BUDGET] Budget constraint: {max_credits} credits available, {estimated_cost} needed")
        print(f"  [BUDGET] Strategy: Prioritize connections (more recent data)\n")
        
        max_connections = min(pending_conn, max_credits // 2)
        max_companies = min(pending_comp, (max_credits - (max_connections * 2)))
    else:
        max_connections = pending_conn
        max_companies = pending_comp
    
    credits_used = 0
    
    # Enrich connections
    if max_connections > 0:
        print(f"  Enriching {max_connections}/{pending_conn} connections...")
        cmd = [
            sys.executable,
            "enrichment/enrich_connections_api.py",
            "--max", str(max_connections),
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Extract credits from output
        for line in result.stdout.split('\n'):
            if "Credits reported:" in line:
                try:
                    credits_used += int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        
        if result.returncode != 0:
            print(f"    [WARN] Connections enrichment exited with code {result.returncode}, continuing...")
        else:
            print(f"    [OK] Completed\n")
    if max_companies > 0:
        print(f"  Enriching {max_companies}/{pending_comp} companies...")
        cmd = [
            sys.executable,
            "enrichment/enrich_companies_api.py",
            "--max", str(max_companies),
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Extract credits from output
        for line in result.stdout.split('\n'):
            if "Credits reported:" in line:
                try:
                    credits_used += int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        
        if result.returncode != 0:
            print(f"    [WARN] Companies enrichment exited with code {result.returncode}, continuing...")
        else:
            print(f"    [OK] Completed\n")
    
    # Update state
    state = load_state()
    state["last_enrichment"] = datetime.now().isoformat()
    state["connections_enriched_total"] += max_connections
    state["companies_enriched_total"] += max_companies
    state["credits_used_total"] += credits_used
    save_state(state)
    
    return True, credits_used


def run_ingest(dry_run: bool = False) -> bool:
    """Parse and ingest all snapshots into ChromaDB."""
    print("\n[3/3] Parsing & Ingesting into ChromaDB")
    print("="*70 + "\n")
    
    cmd = [sys.executable, "ingest.py", "--ingest-only"]
    if dry_run:
        cmd.insert(2, "--dry-run")
    
    print(f"  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    
    if result.returncode != 0:
        print("\n  [ERROR] Ingestion failed")
        return False
    
    # Update state
    state = load_state()
    state["last_ingest"] = datetime.now().isoformat()
    state["last_full_sync"] = datetime.now().isoformat()
    
    # Add run record
    run_record = {
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    if "runs" not in state:
        state["runs"] = []
    state["runs"].append(run_record)
    
    save_state(state)
    
    print("\n  [OK] Ingestion complete")
    return True


def run_full_sync(dry_run: bool = False, force_refresh: bool = False, 
                  skip_enrich: bool = False, max_credits: Optional[int] = None) -> bool:
    """Run complete sync pipeline: fetch → enrich → ingest."""
    print("\n" + "="*70)
    print("  LinkedIn Data Synchronization Pipeline")
    print(f"  {'DRY RUN' if dry_run else 'LIVE'} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Step 1: Fetch
    if not run_fetch(force_refresh=force_refresh):
        return False
    
    # Step 2: Enrich
    if not skip_enrich:
        success, credits = run_enrichment(max_credits=max_credits, dry_run=dry_run)
        if not success:
            return False
    
    # Step 3: Ingest
    if not run_ingest(dry_run=dry_run):
        return False
    
    # Final summary
    print("\n" + "="*70)
    print("  [OK] Synchronization Complete!")
    print("="*70 + "\n")
    
    show_status()
    
    return True


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily data synchronization for LinkedIn Career Assistant"
    )
    parser.add_argument("--dry-run", action="store_true", 
                       help="Parse without embedding (no ChromaDB changes)")
    parser.add_argument("--force-refresh", action="store_true",
                       help="Ignore cache, fetch fresh snapshots")
    parser.add_argument("--skip-enrich", action="store_true",
                       help="Skip enrichment, only fetch + ingest")
    parser.add_argument("--max-credits", type=int, default=None, metavar="N",
                       help="Limit Tavily credits to N (default: unlimited)")
    parser.add_argument("--status", action="store_true",
                       help="Show sync status and exit")
    
    args = parser.parse_args()
    
    # Validate environment
    if not os.getenv("LINKEDIN_PORTABILITY_TOKEN"):
        print("ERROR: LINKEDIN_PORTABILITY_TOKEN not set")
        raise SystemExit(1)
    
    # Status-only mode
    if args.status:
        show_status()
        return
    
    # Full sync mode
    success = run_full_sync(
        dry_run=args.dry_run,
        force_refresh=args.force_refresh,
        skip_enrich=args.skip_enrich,
        max_credits=args.max_credits,
    )
    
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
