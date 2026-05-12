#!/usr/bin/env python3
"""
Phase 2 company enrichment via Tavily Search API.

Reads the latest cached COMPANY_FOLLOWS snapshot, reports the pending
enrichment backlog, and optionally enriches each followed company into markdown
files under data/enriched/companies.

Supports date-based filtering: only enrich companies followed after --start-date.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    slugify_text,
    snapshot_rows,
    sync_legacy_companies,
    utc_timestamp,
)
from enrichment.skip_list import SKIP_COMPANIES


TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
SEARCH_DEPTH = "basic"
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_CALLS = 0.5
OUTPUT_DIR = ENRICHED_DIR / "companies"
ESTIMATED_CREDITS_PER_CALL = 1
CONFIG_FILE = REPO_ROOT / "enrichment" / "enrichment_config.json"


# ── Config Management ─────────────────────────────────────────────────────────

def load_enrichment_config() -> dict:
    """Load enrichment configuration (start dates, tracking info)."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "companies_enrichment": {
            "start_date": "2026-04-16",
            "last_enriched_date": None,
        }
    }


def save_enrichment_config(config: dict) -> None:
    """Save enrichment configuration."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ── Loading and Filtering ─────────────────────────────────────────────────────

def load_companies(start_date: Optional[str] = None) -> list[dict]:
    """
    Load companies from COMPANY_FOLLOWS snapshot.
    
    If start_date is provided, only include companies followed after this date.
    Automatically skips companies in the SKIP_COMPANIES list.
    """
    rows = snapshot_rows("COMPANY_FOLLOWS")
    unique_by_org: dict[str, dict] = {}
    for row in rows:
        organization = str(row.get("Organization", "")).strip()
        if not organization:
            continue
        existing = unique_by_org.get(organization)
        followed_on = str(row.get("Followed On", "")).strip()
        if existing is None or (parse_date(followed_on) or datetime.min) > (parse_date(existing.get("followed_on", "")) or datetime.min):
            unique_by_org[organization] = {
                "organization": organization,
                "followed_on": followed_on,
            }
    
    companies = sorted(
        unique_by_org.values(),
        key=lambda item: parse_date(item.get("followed_on", "")) or datetime.min,
        reverse=True,
    )
    
    # Filter by start_date if provided
    if start_date:
        start_dt = parse_date(start_date)
        if start_dt:
            companies = [
                c for c in companies
                if (parse_date(c.get("followed_on", "")) or datetime.min) > start_dt
            ]
    
    # Remove blacklisted companies
    companies = [c for c in companies if c["organization"] not in SKIP_COMPANIES]
    
    return companies


def output_path(company: dict) -> Path:
    return OUTPUT_DIR / f"Company_{slugify_text(company['organization'])}.md"


def split_pending(companies: list[dict]) -> tuple[list[dict], int]:
    pending = []
    enriched = 0
    for company in companies:
        if file_has_content(output_path(company)):
            enriched += 1
        else:
            pending.append(company)
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
            "include_raw_content": "markdown",
            "max_results": 5,
            "include_usage": True,
            "topic": "general",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def build_query(company: dict) -> str:
    """Build a detailed Tavily search query to extract comprehensive company information."""
    organization = company["organization"]
    # Request specific structured fields: founding info, funding, employees, investors, 
    # specialties, recent announcements, and links to key company profiles
    query_parts = [
        f'"{organization}"',  # only org name quoted; rest unquoted to avoid zero results
        "company founded founding date",
        "funding rounds investors seed series",
        "employee count team size",
        "specialties industries expertise",
        "recent news announcements posts",
        "website LinkedIn Crunchbase",
    ]
    return " ".join(query_parts)


def build_markdown(company: dict, result: dict) -> str:
    """Build markdown matching Phase 1 company enrichment format with structured sections."""
    organization = company["organization"]
    
    # Extract main answer/overview
    answer = (result.get("answer") or "").strip()
    
    # Build header section similar to Phase 1
    lines = [
        f"# {organization}",
        "",
        f"**Followed On:** {company.get('followed_on', '')}",
        f"**Enriched At:** {utc_timestamp()}",
        "",
        "---",
        "",
    ]
    
    # Add Overview section with answer content
    lines.append("## Overview")
    lines.append("")
    if answer:
        lines.append(answer)
    else:
        lines.append("_No overview available._")
    lines.append("")
    
    # Extract and organize information from sources
    results = result.get("results", [])
    sources_text = ""
    
    # Aggregate source content for information extraction
    for item in results[:5]:
        content = item.get("content", "")
        raw_content = item.get("raw_content", "")
        if raw_content:
            sources_text += raw_content + "\n"
        if content:
            sources_text += content + "\n"
    
    # Parse and organize key information sections
    # These sections will be populated if we detect relevant content
    
    # Website, Crunchbase, LinkedIn section
    lines.append("### Key Links")
    lines.append("")
    links_found = False
    for item in results[:5]:
        url = item.get("url", "")
        if url:
            if "linkedin.com" in url.lower():
                lines.append(f"- **LinkedIn:** {url}")
                links_found = True
            elif "crunchbase" in url.lower():
                lines.append(f"- **Crunchbase:** {url}")
                links_found = True
            elif not any(x in url.lower() for x in ["linkedin", "crunchbase"]):
                # Likely company website
                if links_found or url.count(".") >= 1:
                    lines.append(f"- **Website:** {url}")
                    links_found = True
    if not links_found:
        lines.append("_No key links found._")
    lines.append("")
    
    # Industry, Company Size, Founded section
    lines.append("### Company Details")
    lines.append("")
    details_lines = []
    
    # Try to extract structured information from sources
    # Look for patterns like "founded", "employees", "industry", etc.
    sources_lower = sources_text.lower()
    
    # Check for founding date
    if any(word in sources_lower for word in ["founded", "established", "incorporated"]):
        for item in results[:3]:
            content = ((item.get("content") or "") + " " + (item.get("raw_content") or "")).lower()
            if "founded" in content or "established" in content:
                # Try to extract year
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', content)
                if year_match:
                    details_lines.append(f"**Founded:** {year_match.group(1)}")
                    break
    
    # Check for employee count
    if any(word in sources_lower for word in ["employee", "staff", "team size", "workforce"]):
        for item in results[:3]:
            content = (item.get("content") or "") + " " + (item.get("raw_content") or "")
            if any(word in content.lower() for word in ["employee", "staff", "team"]):
                # Extract number range if present
                match = re.search(r'(\d+[,\d]*)\s*(?:-|to)\s*(\d+[,\d]*)\s*(?:employee|staff|people)', content, re.I)
                if match:
                    details_lines.append(f"**Company Size:** {match.group(1)}-{match.group(2)} employees")
                    break
                else:
                    match = re.search(r'(\d+[,\d]*)\+?\s*(?:employee|staff|person|people)', content, re.I)
                    if match:
                        details_lines.append(f"**Company Size:** {match.group(1)}+ employees")
                        break
    
    if details_lines:
        for line in details_lines:
            lines.append(line)
    else:
        lines.append("_Company details not extracted._")
    lines.append("")
    
    # Funding and Investors section
    if "funding" in sources_lower or "investor" in sources_lower or "seed" in sources_lower or "series" in sources_lower:
        lines.append("### Funding & Investors")
        lines.append("")
        funding_found = False
        for item in results[:5]:
            content = (item.get("content") or "") + " " + (item.get("raw_content") or "")
            if any(word in content.lower() for word in ["funding", "raised", "investor", "seed", "series", "round"]):
                # Extract relevant funding information
                round_match = re.search(r'(Series [A-Z]|Seed|Pre-seed|Funding Round)[:\s]+\$?\s*([\d.]+\s*(?:M|B|K)?)', content, re.I)
                if round_match:
                    lines.append(f"**{round_match.group(1)}:** ${round_match.group(2)}")
                    funding_found = True
                
                investor_match = re.search(r'(?:backed by|investors?:?)\s*([^.]+)', content, re.I)
                if investor_match:
                    investors = investor_match.group(1).strip()
                    if len(investors) < 200:  # Reasonable length
                        lines.append(f"**Investors:** {investors}")
                        funding_found = True
        
        if not funding_found:
            lines.append("_Funding information not available._")
        lines.append("")
    
    # Sources section with full details
    lines.append("## Sources")
    lines.append("")
    for index, item in enumerate(results[:5], 1):
        title = item.get('title', 'Untitled')
        lines.append(f"### {index}. {title}")
        url = item.get('url', '')
        if url:
            lines.append(f"**URL:** {url}")
        content = (item.get("content") or "").strip()
        if content:
            lines.append("")
            lines.append(content[:2000])  # Limit to 2000 chars per source
        raw_content = (item.get("raw_content") or "").strip()
        if raw_content and raw_content != content:
            lines.append("")
            lines.append(raw_content[:2000])  # Limit to 2000 chars
        lines.append("")
    
    return "\n".join(lines)


def save_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def print_stats(companies: list[dict], pending: list[dict], enriched: int, usage: dict | None, start_date: Optional[str] = None) -> None:
    latest_date = next((item.get("followed_on", "") for item in companies if item.get("followed_on")), "")
    estimated_credits = len(pending) * ESTIMATED_CREDITS_PER_CALL
    print(f"\n{'=' * 68}")
    print("  Companies Enrichment Status")
    print(f"{'=' * 68}")
    if start_date:
        print(f"  {'Start date filter:':<28} {start_date} (exclusive)")
    print(f"  {'Total in snapshot:':<28} {len(companies)}")
    print(f"  {'Already enriched:':<28} {enriched}")
    print(f"  {'Pending enrichment:':<28} {len(pending)}")
    print(f"  {'Latest follow date:':<28} {latest_date or 'N/A'}")
    print(f"  {'Estimated Tavily credits:':<28} {estimated_credits} ({ESTIMATED_CREDITS_PER_CALL}/company)")
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


def enrich_companies(companies: list[dict], api_key: str, max_calls: int, start_date: Optional[str] = None) -> Optional[str]:
    """
    Enrich companies via Tavily API.
    
    Returns the most recent followed_on date from successfully enriched companies,
    which should be saved as the new start_date for future runs.
    """
    if not api_key:
        print("ERROR: Set TAVILY_API_KEY to enrich companies.\n")
        raise SystemExit(1)

    sync_legacy_companies(companies, OUTPUT_DIR)  # Silently sync legacy files (no stats reporting)
    pending, enriched = split_pending(companies)
    usage = get_tavily_usage(api_key)
    print_stats(companies, pending, enriched, usage, start_date=start_date)

    if not pending:
        return None

    most_recent_date = None
    calls_made = 0
    credits_used = 0
    for index, company in enumerate(pending, 1):
        if max_calls > 0 and calls_made >= max_calls:
            print(f"Max API calls reached ({max_calls}) — stopping.")
            break
        query = build_query(company)
        print(f"[{index}/{len(pending)}] {company['organization']}")
        print(f"  Query: {query}")
        try:
            result = tavily_search(api_key, query)
            calls_made += 1
            credits_used += int((result.get("usage") or {}).get("credits", 0) or 0)
            save_markdown(output_path(company), build_markdown(company, result))
            print(f"  [OK] Saved -> {output_path(company).name}")
            
            # Track most recent date successfully enriched
            company_date = parse_date(company.get("followed_on", ""))
            if company_date:
                if most_recent_date is None or company_date > most_recent_date:
                    most_recent_date = company_date
        except Exception as exc:
            print(f"  [ERR] Failed: {exc}")
        if max_calls == 0 or calls_made < max_calls:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\nCalls made: {calls_made}")
    print(f"Credits reported: {credits_used}\n")
    
    # Return the most recent date to be saved in config
    return most_recent_date.strftime("%m/%d/%y, %I:%M %p") if most_recent_date else None



def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich cached followed companies via Tavily Search.")
    parser.add_argument("--max", type=int, default=0, metavar="N", help="Maximum Tavily calls to make. 0 = no limit.")
    parser.add_argument("--stats", action="store_true", help="Show backlog and estimated credit usage without calling Tavily.")
    parser.add_argument("--start-date", type=str, metavar="DATE", help="Only enrich companies followed after this date (e.g., '04/16/26').")
    args = parser.parse_args()

    # Load config to get start_date if not provided via CLI
    config = load_enrichment_config()
    start_date = args.start_date or config.get("companies_enrichment", {}).get("start_date")

    companies = load_companies(start_date=start_date)
    sync_legacy_companies(companies, OUTPUT_DIR)  # Silently sync legacy files (no stats reporting)
    pending, enriched = split_pending(companies)
    usage = get_tavily_usage(resolve_tavily_api_key())
    print_stats(companies, pending, enriched, usage, start_date=start_date)
    
    if not args.stats:
        most_recent_date = enrich_companies(companies, resolve_tavily_api_key(), args.max, start_date=start_date)
        
        # Update config with the most recent date processed
        if most_recent_date:
            config["companies_enrichment"]["last_enriched_date"] = most_recent_date
            config["companies_enrichment"]["start_date"] = most_recent_date
            save_enrichment_config(config)
            print(f"✅ Updated start_date to: {most_recent_date}")
            print(f"   Next run will only enrich companies followed after this date.\n")


if __name__ == "__main__":
    main()