#!/usr/bin/env python3
"""
Phase 2 connections enrichment via Tavily Search API.

Reads the latest cached CONNECTIONS snapshot, reports the pending enrichment
backlog, and optionally enriches each connection into markdown files under
data/enriched/connections.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from enrichment.common import (
    ENRICHED_DIR,
    file_has_content,
    get_tavily_usage,
    parse_date,
    resolve_tavily_api_key,
    slugify_linkedin_url,
    snapshot_rows,
    sync_legacy_connections,
    utc_timestamp,
)


TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
SEARCH_DEPTH = "advanced"
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_CALLS = 0.5
OUTPUT_DIR = ENRICHED_DIR / "connections"
ESTIMATED_CREDITS_PER_CALL = 2


def load_connections() -> list[dict]:
    rows = snapshot_rows("CONNECTIONS")
    unique_by_url: dict[str, dict] = {}
    for row in rows:
        url = str(row.get("URL", "")).strip()
        if not url:
            continue
        unique_by_url[url] = {
            "url": url,
            "first_name": str(row.get("First Name", "")).strip(),
            "last_name": str(row.get("Last Name", "")).strip(),
            "company": str(row.get("Company", "")).strip(),
            "position": str(row.get("Position", "")).strip(),
            "connected_on": str(row.get("Connected On", "")).strip(),
        }
    return sorted(
        unique_by_url.values(),
        key=lambda item: parse_date(item.get("connected_on", "")) or datetime.min,
        reverse=True,
    )


def output_path(connection: dict) -> Path:
    return OUTPUT_DIR / f"Connection_{slugify_linkedin_url(connection['url'])}.md"


def split_pending(connections: list[dict]) -> tuple[list[dict], int]:
    pending = []
    enriched = 0
    for connection in connections:
        if file_has_content(output_path(connection)):
            enriched += 1
        else:
            pending.append(connection)
    return pending, enriched


def tavily_search(api_key: str, query: str) -> dict:
    response = requests.post(
        TAVILY_SEARCH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "query": query,
            "search_depth": SEARCH_DEPTH,
            "include_answer": "advanced",
            "include_raw_content": False,
            "max_results": 5,
            "include_usage": True,
            "exact_match": True,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def build_query(connection: dict) -> str:
    """Build a detailed Tavily search query to extract professional context."""
    name = f"{connection['first_name']} {connection['last_name']}".strip()
    parts = [f'"{name}"'] if name else []
    if connection.get("company"):
        parts.append(connection["company"])  # unquoted — exact_match on company+title too often returns 0 results
    if connection.get("position"):
        parts.append(connection["position"])  # unquoted
    # Request structured information: background, expertise, past roles, education, specialties
    parts.append("professional background career experience expertise specialties education")
    return " ".join(parts)


def build_markdown(connection: dict, result: dict) -> str:
    """Build markdown matching Phase 1 connection enrichment format."""
    name = f"{connection['first_name']} {connection['last_name']}".strip()
    
    # Format the connected_on date similar to Phase 1 (e.g., "30-Jan-26")
    connected_date = connection.get('connected_on', '')
    if connected_date:
        try:
            dt = parse_date(connected_date)
            if dt:
                connected_date = dt.strftime('%d-%b-%y')
        except:
            pass
    
    lines = [
        f"# {name}",
        "",
        f"**Current Company:** {connection.get('company', '')}",
        f"**Position:** {connection.get('position', '')}",
        f"**LinkedIn URL:** {connection['url']}",
        f"**Connected:** {connected_date}",
        f"**Enriched at:** {utc_timestamp()}",
        "",
        "---",
        "",
        "## Professional Summary",
        "",
    ]
    
    # Add answer/summary
    answer = (result.get("answer") or "").strip()
    if answer:
        lines.append(answer)
    else:
        lines.append("_No summary available._")
    
    lines.append("")
    
    # Add sources section with expanded content
    results = result.get("results", [])
    if results:
        lines.extend(["## Sources", ""])
        for index, item in enumerate(results[:5], 1):
            title = item.get('title', 'Untitled')
            lines.append(f"### {index}. {title}")
            url = item.get('url', '')
            if url:
                lines.append(f"**URL:** {url}")
            content = item.get("content", "").strip()
            if content:
                lines.append("")
                lines.append(content)
            lines.append("")
    
    return "\n".join(lines)


def save_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def print_stats(connections: list[dict], pending: list[dict], enriched: int, usage: dict | None) -> None:
    latest_date = next((item.get("connected_on", "") for item in connections if item.get("connected_on")), "")
    estimated_credits = len(pending) * ESTIMATED_CREDITS_PER_CALL
    print(f"\n{'=' * 68}")
    print("  Connections Enrichment Status")
    print(f"{'=' * 68}")
    print(f"  {'Total in snapshot:':<28} {len(connections)}")
    print(f"  {'Already enriched:':<28} {enriched}")
    print(f"  {'Pending enrichment:':<28} {len(pending)}")
    print(f"  {'Latest connection date:':<28} {latest_date or 'N/A'}")
    print(f"  {'Estimated Tavily credits:':<28} {estimated_credits} ({ESTIMATED_CREDITS_PER_CALL}/connection)")
    if usage:
        key_usage = usage.get("key", {})
        account = usage.get("account", {})
        limit = key_usage.get("limit")
        used = key_usage.get("usage")
        remaining = "unknown" if limit in (None, "") or used is None else max(limit - used, 0)
        print(f"  {'Current Tavily key usage:':<28} {used}")
        print(f"  {'Current Tavily key limit:':<28} {limit}")
        print(f"  {'Estimated key remaining:':<28} {remaining}")
        print(f"  {'Plan usage / limit:':<28} {account.get('plan_usage')} / {account.get('plan_limit')}")
    else:
        print(f"  {'Tavily usage lookup:':<28} unavailable (set TAVILY_API_KEY)")
    print(f"{'=' * 68}\n")


def enrich_connections(connections: list[dict], api_key: str, max_calls: int) -> None:
    if not api_key:
        print("ERROR: Set TAVILY_API_KEY to enrich connections.\n")
        raise SystemExit(1)

    sync_legacy_connections(connections, OUTPUT_DIR)  # Silently sync legacy files (no stats reporting)
    pending, enriched = split_pending(connections)
    usage = get_tavily_usage(api_key)
    print_stats(connections, pending, enriched, usage)

    if not pending:
        return

    calls_made = 0
    credits_used = 0
    for index, connection in enumerate(pending, 1):
        if max_calls > 0 and calls_made >= max_calls:
            print(f"Max API calls reached ({max_calls}) — stopping.")
            break
        query = build_query(connection)
        name = f"{connection['first_name']} {connection['last_name']}".strip()
        print(f"[{index}/{len(pending)}] {name}")
        print(f"  Query: {query}")
        try:
            result = tavily_search(api_key, query)
            calls_made += 1
            credits_used += int((result.get("usage") or {}).get("credits", 0) or 0)
            save_markdown(output_path(connection), build_markdown(connection, result))
            print(f"  [OK] Saved -> {output_path(connection).name}")
        except Exception as exc:
            print(f"  [ERR] Failed: {exc}")
        if max_calls == 0 or calls_made < max_calls:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nCalls made: {calls_made}")
    print(f"Credits reported: {credits_used}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich cached LinkedIn connections via Tavily Search.")
    parser.add_argument("--max", type=int, default=0, metavar="N", help="Maximum Tavily calls to make. 0 = no limit.")
    parser.add_argument("--stats", action="store_true", help="Show backlog and estimated credit usage without calling Tavily.")
    args = parser.parse_args()

    connections = load_connections()
    sync_legacy_connections(connections, OUTPUT_DIR)  # Silently sync legacy files (no stats reporting)
    pending, enriched = split_pending(connections)
    usage = get_tavily_usage(resolve_tavily_api_key())
    print_stats(connections, pending, enriched, usage)
    if not args.stats:
        enrich_connections(connections, resolve_tavily_api_key(), args.max)


if __name__ == "__main__":
    main()