#!/usr/bin/env python3
"""
LinkedIn Companies Extractor via Tavily Extract API
---------------------------------------------------
Reads company URLs from:
  - "Company Follows.csv" → column: LinkedIn URL

Extracts company profile data via Tavily Extract API (basic depth, batches of 5):
  - Company overview & description
  - Industry, size, locations
  - Founded date, funding info
  - Employee count
  - Website & social links

Saves each result as a Markdown file:
  - Companies/Company_<slug>.md

Resume logic skips already-extracted files.

Usage:
  export TAVILY_API_KEY="tvly-YOUR_KEY_HERE"
  python extract_companies.py

  # Limit to 5 API calls (= 25 company URLs):
  python extract_companies.py --max 5

  # Or specify custom CSV:
  python extract_companies.py --companies "Company Follows.csv" --max 10
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
TAVILY_EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
EXTRACT_DEPTH         = "basic"
BATCH_SIZE            = 5
DELAY_BETWEEN_BATCHES = 1.0   # seconds — increase if you hit rate limits
REQUEST_TIMEOUT       = 30    # seconds per API call

OUTPUT_DIR_COMPANIES  = Path("Companies")


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(url: str) -> str:
    """Turn a LinkedIn URL into a safe filename slug."""
    slug = re.sub(r"https?://(www\.)?linkedin\.com/", "", url)
    slug = re.sub(r"[^\w\-]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:120]


def load_companies_from_csv(filepath: str) -> list[dict]:
    """Load company URLs from CSV file."""
    entries = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("LinkedIn URL", "").strip()
            if url and url.startswith("http"):
                entries.append({
                    "url": url,
                    "organization": row.get("Organization", "").strip(),
                    "followed_on": row.get("Followed On", "").strip(),
                    "row": row
                })
    return entries


def already_extracted(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def build_company_markdown(url: str, raw_content: str, metadata: dict = None) -> str:
    """Build structured markdown for company profile."""
    if metadata is None:
        metadata = {}
    
    lines = [
        f"# Extracted: {url}",
        "",
        f"**Source URL:** {url}  ",
        f"**Extracted at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  ",
        "",
        "---",
        "",
    ]
    
    # Add metadata if present
    if metadata:
        lines += ["## Metadata", ""]
        for key, value in metadata.items():
            if value:
                lines.append(f"- **{key}:** {value}")
        lines += ["", "---", ""]
    
    # Add extracted content
    if raw_content:
        lines.append(raw_content)
    else:
        lines.append("_No content extracted._")
    
    return "\n".join(lines)


def save_markdown(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ── Tavily API ────────────────────────────────────────────────────────────────

def tavily_extract(urls: list[str]) -> dict:
    """Call Tavily Extract API for a batch of URLs.
    
    Returns:
      {
        "results": [{"url": str, "raw_content": str}, ...],
        "failed_results": [{"url": str, "error": str}, ...],
        "usage": {"credits": int}
      }
    """
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "urls": urls,
        "extraction_depth": EXTRACT_DEPTH,
        "include_usage": True,
    }
    try:
        response = requests.post(
            TAVILY_EXTRACT_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print(f"    ✗ HTTP error: {e}")
        return {"results": [], "failed_results": [{"urls": urls, "error": str(e)}], "usage": {"credits": 0}}
    except Exception as e:
        print(f"    ✗ Extraction error: {e}")
        return {"results": [], "failed_results": [{"urls": urls, "error": str(e)}], "usage": {"credits": 0}}


# ── Core Processing ────────────────────────────────────────────────────────────

def process_batch(batch: list[dict], output_dir: Path, stats: dict):
    """Extract a batch of company URLs and save each result as a .md file."""
    urls = [item["url"] for item in batch]

    # ── API call ──────────────────────────────────────────────────────────────
    print(f"    Extracting {len(urls)} URLs...")
    data = tavily_extract(urls)

    results_by_url = {r["url"]: r for r in data.get("results", [])}
    failed_urls    = {r["url"] for r in data.get("failed_results", [])}
    stats["credits"] += data.get("usage", {}).get("credits", 0)

    # ── Save each URL individually ─────────────────────────────────────────────
    for item in batch:
        url  = item["url"]
        path = output_dir / f"Company_{slugify(url)}.md"

        if url in results_by_url:
            raw = results_by_url[url].get("raw_content", "")
            markdown = build_company_markdown(url, raw, item.get("row", {}))
            save_markdown(path, markdown)
            print(f"      ✓ Saved [{len(raw):,} chars] → {path.name}")
            stats["saved"] += 1

        elif url in failed_urls:
            stats["failed"] += 1
            print(f"      ⚠ Extraction failed → {url}")
            markdown = build_company_markdown(
                url, "_Tavily could not extract this page._",
                {"Status": "FAILED"}
            )
            save_markdown(path, markdown)

        else:
            print(f"      ? No result returned for {url}")
            stats["failed"] += 1


def process_all(
    entries: list[dict],
    output_dir: Path,
    stats: dict,
    max_calls: int,
) -> int:
    """
    Skip already-done entries then process the rest in batches.
    Stops once `max_calls` API calls have been made.
    Returns the number of calls consumed.
    """
    pending = []
    skipped_here = 0
    
    for item in entries:
        path = output_dir / f"Company_{slugify(item['url'])}.md"
        if already_extracted(path):
            skipped_here += 1
            stats["skipped"] += 1
        else:
            pending.append(item)

    print(f"      {skipped_here} already extracted (skipping)")
    print(f"      {len(pending)} to process\n")

    calls_made = 0
    total_batches = min(
        (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE,
        max_calls if max_calls > 0 else float("inf"),
    )
    
    for i in range(0, len(pending), BATCH_SIZE):
        if max_calls > 0 and calls_made >= max_calls:
            print(f"    Max API calls reached ({max_calls}) — stopping.")
            break
        
        batch = pending[i : i + BATCH_SIZE]
        batch_num = calls_made + 1
        print(f"    Batch {batch_num}/{int(total_batches)}:")
        for item in batch:
            print(f"      {item['url']}")
        
        process_batch(batch, output_dir, stats)
        calls_made += 1
        
        if calls_made < max_calls and i + BATCH_SIZE < len(pending):
            time.sleep(DELAY_BETWEEN_BATCHES)

    return calls_made


# ── Entry Point ────────────────────────────────────────────────────────────────

def run(companies_csv: str, max_calls: int):
    calls_info = f"unlimited" if max_calls == 0 else f"{max_calls} (≈ {max_calls * BATCH_SIZE} URLs)"
    print(f"\n{'='*64}")
    print("  LinkedIn Companies Extractor — Tavily Extract API")
    print(f"  Max API calls   : {calls_info}")
    print(f"  Batch size      : {BATCH_SIZE} URLs per call")
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

    OUTPUT_DIR_COMPANIES.mkdir(exist_ok=True)

    # ── Companies ──────────────────────────────────────────────────────────────
    print(f"[1/1] Companies — {companies_csv}")
    companies = load_companies_from_csv(companies_csv)
    print(f"      {len(companies)} companies found\n")
    
    budget = max_calls if max_calls > 0 else float("inf")
    process_all(companies, OUTPUT_DIR_COMPANIES, stats, budget)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*64}")
    print("  Run Summary")
    print(f"  {'Extracted:':<22} {stats['saved']}")
    print(f"  {'Skipped (resume):':<22} {stats['skipped']}")
    print(f"  {'Failed (Tavily):':<22} {stats['failed']}")
    print(f"  {'API credits used:':<22} {stats['credits']}")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract LinkedIn company profiles via Tavily Extract API."
    )
    parser.add_argument(
        "--companies",
        default="Company Follows.csv",
        help='Path to companies CSV (default: "Company Follows.csv")',
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Maximum number of Tavily API calls to make across all companies. "
            f"Each call processes up to {BATCH_SIZE} URLs. "
            "0 = no limit (default)."
        ),
    )
    args = parser.parse_args()
    run(args.companies, args.max)
