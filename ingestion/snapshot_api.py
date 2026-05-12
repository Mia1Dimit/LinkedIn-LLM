#!/usr/bin/env python3
"""
LinkedIn Portability API — Snapshot Fetcher
─────────────────────────────────────────────

Fetch all configured snapshot domains from LinkedIn Portability API.
Caches results locally and supports resumable downloads.

Usage:
    export LINKEDIN_PORTABILITY_TOKEN="YOUR_TOKEN_HERE"
    
    # Fetch all domains
    python ingestion/snapshot_api.py --fetch-all
    
    # Fetch specific domains only
    python ingestion/snapshot_api.py --domains PROFILE CONNECTIONS SAVED_JOBS
    
    # Validate token & show quota info (dry-run)
    python ingestion/snapshot_api.py --validate
    
    # Resume interrupted fetch (skips cached domains)
    python ingestion/snapshot_api.py --resume
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime, UTC
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Optional, Dict, List, Any

# Allow imports from parent directory
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import PORTABILITY_API


# ── Configuration ─────────────────────────────────────────────────────────────
TOKEN = ""
BASE_URL = PORTABILITY_API["base_url"]
API_VERSION = PORTABILITY_API["api_version"]
SNAPSHOT_DOMAINS = PORTABILITY_API["snapshot_domains"]
CACHE_DIR = REPO_ROOT / "data" / "api_snapshots"
REQUEST_TIMEOUT = 60
DELAY_BETWEEN_REQUESTS = 0.5  # seconds


def resolve_token() -> str:
    """Resolve portability token from env or known credentials files."""
    env_token = os.getenv("LINKEDIN_PORTABILITY_TOKEN", "").strip()
    if env_token:
        return env_token

    candidate_paths = [
        REPO_ROOT / "linkedin_api_creds.json",
        REPO_ROOT / "data" / "creds" / "linkedin_api_creds.json",
    ]
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        access_token = str(payload.get("access_token", "")).strip()
        if access_token:
            return access_token

    return str(PORTABILITY_API.get("token", "")).strip()


TOKEN = resolve_token()


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_cache_dir():
    """Create cache directory structure."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_domain_cache_dir(domain: str) -> Path:
    """Get or create domain-specific cache folder."""
    domain_dir = CACHE_DIR / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    return domain_dir


def cache_exists(domain: str) -> bool:
    """Check if domain has cached snapshot (non-empty)."""
    domain_dir = get_domain_cache_dir(domain)
    cache_files = list(domain_dir.glob("*.json"))
    return len(cache_files) > 0


def get_latest_cache(domain: str) -> Optional[Path]:
    """Get most recent cache file for domain."""
    domain_dir = get_domain_cache_dir(domain)
    cache_files = sorted(domain_dir.glob("*.json"), reverse=True)
    return cache_files[0] if cache_files else None


def load_cache(domain: str) -> Optional[Dict[str, Any]]:
    """Load latest cached snapshot for domain."""
    cache_path = get_latest_cache(domain)
    if cache_path:
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"    ✗ Failed to load cache: {e}")
            return None
    return None


def save_cache(domain: str, data: Dict[str, Any]) -> Path:
    """Save snapshot to cache with timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    cache_path = get_domain_cache_dir(domain) / f"{domain}_{timestamp}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return cache_path


class SnapshotNoDataError(RuntimeError):
    """Raised when LinkedIn reports no snapshot data for the member/domain."""


# ── LinkedIn API ────────────────────────────────────────────────────────────────

def build_headers() -> Dict[str, str]:
    """Build request headers with authorization."""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": API_VERSION,
    }


def extract_next_start(paging: Dict[str, Any]) -> Optional[int]:
    """Read the next page index from LinkedIn paging links."""
    for link in paging.get("links", []):
        if link.get("rel") != "next":
            continue
        href = link.get("href", "")
        if not href:
            continue
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        next_values = query.get("start", [])
        if next_values:
            try:
                return int(next_values[0])
            except ValueError:
                return None
    return None


def snapshot_item_count(data: Dict[str, Any]) -> int:
    """Count records inside snapshotData payloads across all elements."""
    total = 0
    for element in data.get("elements", []):
        total += len(element.get("snapshotData", []))
    return total


def fetch_snapshot(domain: str, start: int = 0, count: int = 10) -> Dict[str, Any]:
    """
    Fetch a snapshot domain from LinkedIn Portability API.
    
    Handles pagination via 'start' and 'count' parameters.
    Returns the response JSON (may contain 'links' for pagination).
    """
    url = f"{BASE_URL}/memberSnapshotData"
    params = {
        "q": "criteria",
        "domain": domain,
        "start": start,
        "count": count,
    }
    headers = build_headers()
    
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401:
            raise RuntimeError("Unauthorized: Invalid or missing LINKEDIN_PORTABILITY_TOKEN")
        elif status_code == 404 and "No data found" in e.response.text:
            raise SnapshotNoDataError(e.response.text)
        elif status_code == 429:
            raise RuntimeError("Rate limited: Please retry after a delay")
        else:
            raise RuntimeError(f"HTTP {status_code}: {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Request failed: {str(e)}")


def fetch_domain_paginated(domain: str, max_results: Optional[int] = None, count: int = 10) -> Dict[str, Any]:
    """
    Fetch all pages of a snapshot domain via pagination.
    
    Returns aggregated result with all elements combined.
    """
    print(f"  Fetching: {domain}")
    
    merged_snapshot_data = []
    snapshot_domain = domain
    start = 0
    pages_fetched = 0
    seen_starts = set()
    
    while True:
        if start in seen_starts:
            raise RuntimeError(f"Pagination loop detected for {domain} at start={start}")
        seen_starts.add(start)

        try:
            result = fetch_snapshot(domain, start=start, count=count)
        except SnapshotNoDataError:
            if pages_fetched == 0:
                return {
                    "paging": {"start": 0, "count": 0, "total": 0},
                    "elements": [],
                }
            break

        paging = result.get("paging", {})
        elements = result.get("elements", [])

        if elements:
            snapshot_domain = elements[0].get("snapshotDomain", domain)
        for element in elements:
            merged_snapshot_data.extend(element.get("snapshotData", []))

        pages_fetched += 1
        
        # Check if we should continue
        next_start = extract_next_start(paging)
        if next_start is None:
            break
        
        # Check if we've hit max results limit
        if max_results and len(merged_snapshot_data) >= max_results:
            merged_snapshot_data = merged_snapshot_data[:max_results]
            break
        
        start = next_start
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return {
        "paging": {
            "start": 0,
            "count": len(merged_snapshot_data),
            "total": len(merged_snapshot_data),
        },
        "elements": [
            {
                "snapshotDomain": snapshot_domain,
                "snapshotData": merged_snapshot_data,
            }
        ] if merged_snapshot_data else [],
    }


# ── Validation & Dry-run ────────────────────────────────────────────────────────

def validate_token() -> bool:
    """Validate token by doing a lightweight request."""
    if not TOKEN or TOKEN.startswith("YOUR"):
        print("ERROR: LinkedIn portability token not found in env or credentials file.\n")
        return False
    
    print("Validating token...")
    try:
        # Try fetching PROFILE domain with count=1 to minimize quota usage
        result = fetch_snapshot("PROFILE", start=0, count=1)
        print("✓ Token is valid")
        print(f"  API version: {API_VERSION}")
        print(f"  Base URL: {BASE_URL}")
        return True
    except Exception as e:
        print(f"✗ Token validation failed: {e}\n")
        return False


# ── Main Processing ────────────────────────────────────────────────────────────

def fetch_domains(
    domains: List[str],
    skip_cache: bool = False,
    verbose: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch specified domains from LinkedIn API.
    
    If cache exists and skip_cache=False, uses cached data instead.
    
    Returns dict: {domain_name: {paging, elements}}
    """
    results = {}
    stats = {
        "fetched": 0,
        "cached": 0,
        "empty": 0,
        "failed": 0,
        "total_records": 0,
    }
    
    ensure_cache_dir()
    
    for domain in domains:
        # Check if cached
        if cache_exists(domain) and not skip_cache:
            print(f"  [{domain}] Using cached snapshot")
            cached_data = load_cache(domain)
            if cached_data:
                results[domain] = cached_data
                element_count = snapshot_item_count(cached_data)
                stats["cached"] += 1
                stats["total_records"] += element_count
                if verbose:
                    print(f"      {element_count} records")
                continue
        
        # Fetch fresh
        try:
            print(f"  [{domain}] Fetching...")
            data = fetch_domain_paginated(domain)
            
            # Save to cache
            cache_path = save_cache(domain, data)
            element_count = snapshot_item_count(data)
            
            results[domain] = data
            stats["total_records"] += element_count

            if element_count == 0:
                stats["empty"] += 1
                print(f"      ○ No snapshot data yet → {cache_path.name}")
            else:
                stats["fetched"] += 1
                print(f"      ✓ {element_count} records → {cache_path.name}")
            
            # Delay before next request to respect rate limits
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"      ✗ Failed: {e}")
            stats["failed"] += 1
    
    return results, stats


# ── CLI ────────────────────────────────────────────────────────────────────────

def run():
    parser = argparse.ArgumentParser(
        description="LinkedIn Portability Snapshot API Fetcher"
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch all configured domains (respects existing cache)",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        metavar="DOMAIN",
        help="Fetch specific domains only (e.g., PROFILE CONNECTIONS SAVED_JOBS)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate token and show API config (dry-run, no fetch)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted fetch (skips already-cached domains)",
    )
    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Ignore cached data and fetch all fresh",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed element counts",
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print("  LinkedIn Portability Snapshot API Fetcher")
    print(f"{'='*70}\n")
    
    # ── Validate token first
    if not validate_token():
        raise SystemExit(1)
    
    print()
    
    # ── Handle --validate flag (early exit)
    if args.validate:
        print("✓ Validation complete. Use --fetch-all or --domains to fetch data.\n")
        return
    
    # ── Determine domains to fetch
    if args.fetch_all:
        target_domains = SNAPSHOT_DOMAINS
    elif args.resume:
        # Resume = fetch all but skip cached
        target_domains = SNAPSHOT_DOMAINS
    elif args.domains:
        target_domains = args.domains
    else:
        parser.print_help()
        print()
        raise SystemExit(0)
    
    # ── Fetch
    print(f"[1/1] Snapshot Domains — {len(target_domains)} domains\n")
    
    results, stats = fetch_domains(
        target_domains,
        skip_cache=args.skip_cache,
        verbose=args.verbose,
    )
    
    # ── Summary
    print(f"\n{'='*70}")
    print("  Fetch Summary")
    print(f"  {'Fetched (fresh):':<25} {stats['fetched']}")
    print(f"  {'Cached (reused):':<25} {stats['cached']}")
    print(f"  {'Empty (not ready):':<25} {stats['empty']}")
    print(f"  {'Failed:':<25} {stats['failed']}")
    print(f"  {'Total records:':<25} {stats['total_records']}")
    print(f"{'='*70}\n")
    
    # Show cache info
    print(f"Cached snapshots location: {CACHE_DIR}\n")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        raise SystemExit(1)
    except Exception as e:
        print(f"\nERROR: {e}\n")
        raise SystemExit(1)
