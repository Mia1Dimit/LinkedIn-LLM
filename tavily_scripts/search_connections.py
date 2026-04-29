#!/usr/bin/env python3
"""
LinkedIn Connections Enricher via Tavily Search API
----------------------------------------------------
Reads connection profiles from:
  - "Connections.csv" → columns: First Name, Last Name, URL, Company, Position

Enriches each connection with public professional data via Tavily Search API:
  - About / Professional Summary
  - Experience (past/current roles)
  - Education
  - Certifications
  - Public information

Saves each result as a structured Markdown file:
  - Connections/Connection_<slug>.md

Resume logic skips already-saved files.

Usage:
  export TAVILY_API_KEY="tvly-YOUR_KEY_HERE"
  python search_connections.py

  # Limit to 10 API calls:
  python search_connections.py --max 10

  # Or specify custom CSV:
  python search_connections.py --connections "Connections.csv" --max 20
"""

import os
import re
import csv
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
TAVILY_API_KEY        = os.environ.get("TAVILY_API_KEY", "tvly-YOUR_KEY_HERE")
TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
SEARCH_DEPTH          = "advanced"
DELAY_BETWEEN_CALLS   = 0.5   # seconds — increase if you hit rate limits
REQUEST_TIMEOUT       = 30    # seconds per API call

OUTPUT_DIR_CONNECTIONS = Path("Connections")


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(url: str) -> str:
    """Turn a LinkedIn URL into a safe filename slug."""
    slug = re.sub(r"https?://(www\.)?linkedin\.com/", "", url)
    slug = re.sub(r"[^\w\-]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:120]


def load_connections_from_csv(filepath: str) -> list[dict]:
    """Load connections with metadata for search enrichment."""
    entries = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("URL", "").strip()
            if url and url.startswith("http"):
                entries.append({
                    "url": url,
                    "first_name": row.get("First Name", "").strip(),
                    "last_name": row.get("Last Name", "").strip(),
                    "company": row.get("Company", "").strip(),
                    "position": row.get("Position", "").strip(),
                    "connected_on": row.get("Connected On", "").strip(),
                    "row": row
                })
    return entries


def already_extracted(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def build_connection_markdown(connection: dict, search_result: dict) -> str:
    """Build structured markdown for connection profile enrichment."""
    name = f"{connection['first_name']} {connection['last_name']}".strip()
    company = connection.get('company', '')
    position = connection.get('position', '')
    
    # Extract search result fields
    answer = search_result.get('answer', 'No summary available.')
    results = search_result.get('results', [])
    
    # Build content sections
    lines = [
        f"# {name}",
        "",
        f"**Current Company:** {company}  ",
        f"**Position:** {position}  ",
        f"**LinkedIn URL:** {connection['url']}  ",
        f"**Connected:** {connection.get('connected_on', 'N/A')}  ",
        f"**Enriched at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  ",
        "",
        "---",
        "",
        "## Professional Summary",
        "",
        answer if answer else "_No summary available._",
        "",
    ]
    
    # Add top search results as sources
    if results:
        lines += [
            "## Sources",
            "",
        ]
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Untitled')
            url = result.get('url', '#')
            content = result.get('content', '')
            lines.append(f"### {i}. {title}")
            lines.append(f"**URL:** {url}")
            if content:
                lines.append(f"\n{content}\n")
            lines.append("")
    
    return "\n".join(lines)


def save_markdown(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ── Tavily API ────────────────────────────────────────────────────────────────

def tavily_search(query: str) -> dict:
    """Call Tavily Search API to enrich connection profile.
    
    Uses exact_match to prevent returning profiles with same first name
    but different surnames (e.g., Konstantinos Kanaris vs Konstantinos Tantoulas).
    """
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "search_depth": SEARCH_DEPTH,
        "include_answer": "advanced",
        "include_raw_content": False,
        "max_results": 5,
        "include_usage": True,
        "exact_match": True,
    }
    try:
        response = requests.post(
            TAVILY_SEARCH_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    ✗ Search error: {e}")
        return {"answer": f"Error: {str(e)}", "results": []}


# ── Core Processing ────────────────────────────────────────────────────────────

def process_connection(connection: dict, output_dir: Path, stats: dict) -> bool:
    """
    Search and enrich a single connection profile.
    Returns True if saved, False otherwise.
    """
    name = f"{connection['first_name']} {connection['last_name']}".strip()
    company = connection.get('company', '')
    position = connection.get('position', '')
    
    # Create filename
    slug = slugify(connection['url'])
    path = output_dir / f"Connection_{slug}.md"
    
    # Check if already processed
    if already_extracted(path):
        stats["skipped"] += 1
        return False
    
    # Build search query from available data
    # Wrap full name in quotes to ensure exact match (prevents Konstantinos -> other Konstantinos)
    query_parts = [f'"{name}"']
    if company:
        query_parts.append(company)
    if position:
        query_parts.append(position)
    query = " ".join(query_parts)
    
    print(f"  Searching: {query}")
    
    # Execute search
    result = tavily_search(query)
    stats["credits"] += result.get("usage", {}).get("credits", 0)
    
    # Save result
    markdown = build_connection_markdown(connection, result)
    save_markdown(path, markdown)
    
    print(f"    ✓ Saved → {path.name}")
    stats["saved"] += 1
    return True


def process_connections(
    connections: list[dict],
    output_dir: Path,
    stats: dict,
    max_calls: int,
) -> int:
    """Process connections and return number of API calls made."""
    pending = []
    skipped_here = 0
    
    for conn in connections:
        slug = slugify(conn['url'])
        path = output_dir / f"Connection_{slug}.md"
        if already_extracted(path):
            skipped_here += 1
            stats["skipped"] += 1
        else:
            pending.append(conn)
    
    print(f"      {skipped_here} already processed (skipping)")
    print(f"      {len(pending)} to process\n")
    
    calls_made = 0
    for i, conn in enumerate(pending, 1):
        if calls_made >= max_calls and max_calls > 0:
            print(f"\n  Max API calls reached ({max_calls}) — stopping.")
            break
        
        name = f"{conn['first_name']} {conn['last_name']}".strip()
        print(f"  [{i}/{len(pending)}] {name}")
        
        process_connection(conn, output_dir, stats)
        calls_made += 1
        
        if calls_made < max_calls and i < len(pending):
            time.sleep(DELAY_BETWEEN_CALLS)
    
    return calls_made


# ── Entry Point ────────────────────────────────────────────────────────────────

def run(connections_csv: str, max_calls: int):
    calls_info = f"unlimited" if max_calls == 0 else f"{max_calls}"
    print(f"\n{'='*64}")
    print("  LinkedIn Connections Enricher — Tavily Search API")
    print(f"  Max API calls   : {calls_info}")
    print(f"  Search depth    : {SEARCH_DEPTH}")
    print(f"{'='*64}\n")

    if TAVILY_API_KEY.startswith("tvly-YOUR"):
        print("ERROR: Set your TAVILY_API_KEY environment variable first.\n")
        raise SystemExit(1)

    stats = {
        "saved": 0,
        "skipped": 0,
        "failed": 0,
        "credits": 0,
    }

    OUTPUT_DIR_CONNECTIONS.mkdir(exist_ok=True)

    # ── Connections ────────────────────────────────────────────────────────────
    print(f"[1/1] Connections — {connections_csv}")
    connections = load_connections_from_csv(connections_csv)
    print(f"      {len(connections)} connections found")
    
    budget = max_calls if max_calls > 0 else float("inf")
    calls_used = process_connections(connections, OUTPUT_DIR_CONNECTIONS, stats, budget)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*64}")
    print("  Run Summary")
    print(f"  {'Enriched:':<22} {stats['saved']}")
    print(f"  {'Skipped (resume):':<22} {stats['skipped']}")
    print(f"  {'Failed:':<22} {stats['failed']}")
    print(f"  {'API credits used:':<22} {stats['credits']}")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich LinkedIn connections with public professional data via Tavily Search."
    )
    parser.add_argument(
        "--connections",
        default="Connections.csv",
        help='Path to connections CSV (default: "Connections.csv")',
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Maximum number of Tavily API calls to make. "
            "0 = no limit (default). "
            "Each call processes one connection."
        ),
    )
    args = parser.parse_args()
    run(args.connections, args.max)
