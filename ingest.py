#!/usr/bin/env python3
"""
LinkedIn Career Assistant — Phase 2 Ingestion
──────────────────────────────────────────────

Unified ingestion pipeline for Phase 2 (LinkedIn Portability Snapshot API):

1. Fetch snapshots from LinkedIn API (or use cached)
2. Enrich enrichment-required domains via Tavily
3. Parse all cached + enriched data
4. Chunk and embed via Bedrock
5. Store in ChromaDB collections

Usage:
    export LINKEDIN_PORTABILITY_TOKEN="YOUR_TOKEN_HERE"
    
    # Full pipeline: fetch + enrich + ingest
    python ingest.py --fetch-all
    
    # Fetch snapshots only
    python ingest.py --fetch-only
    
    # Enrich only (requires cached snapshots)
    python ingest.py --enrich-only
    
    # Ingest only (uses cached snapshots + enriched data)
    python ingest.py --ingest-only
    
    # Dry-run (parse without embedding)
    python ingest.py --dry-run
    
    # Check what's in ChromaDB
    python ingest.py --stats
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

# Allow imports from parent directory
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import PORTABILITY_API, INGEST, COLLECTIONS
from db.vector_store import VectorStore
from utils.schema import DocumentChunk
from utils.chunker import chunk_text


# ── Configuration ─────────────────────────────────────────────────────────────
TOKEN = os.getenv("LINKEDIN_PORTABILITY_TOKEN", "")
SNAPSHOT_CACHE_DIR = REPO_ROOT / "data" / "api_snapshots"
ENRICHED_DIR = REPO_ROOT / "data" / "enriched"

# Domain classification for Phase 2
DOMAINS = {
    "direct": [
        "PROFILE", "POSITIONS", "EDUCATION", "SKILLS", "CERTIFICATIONS",
        "LANGUAGES", "PUBLICATIONS", "JOB_APPLICANT_SAVED_ANSWERS", "INBOX"
    ],
    "enriched": ["CONNECTIONS", "COMPANY_FOLLOWS"],
    "activity": ["JOB_APPLICATIONS", "SAVED_JOBS", "SAVED_JOB_ALERTS"],
}


# ── Snapshot API Integration ──────────────────────────────────────────────────

def run_snapshot_fetcher(domains: Optional[List[str]] = None, skip_cache: bool = False):
    """Orchestrate snapshot API fetcher."""
    if not TOKEN or TOKEN.startswith("YOUR"):
        print("ERROR: LINKEDIN_PORTABILITY_TOKEN not set.\n")
        raise SystemExit(1)
    
    cmd = ["python", "ingestion/snapshot_api.py"]
    
    if domains:
        cmd.extend(["--domains"] + domains)
    else:
        cmd.append("--fetch-all")
    
    if skip_cache:
        cmd.append("--skip-cache")
    
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    
    if result.returncode != 0:
        raise RuntimeError("Snapshot fetch failed")


def run_enrichment_scripts():
    """Orchestrate Tavily enrichment scripts."""
    print("\n[2/4] Enrichment Scripts")
    print("="*70 + "\n")
    
    enrichment_scripts = [
        ("enrichment/enrich_connections_api.py", "Enriching connections..."),
        ("enrichment/enrich_companies_api.py", "Enriching companies..."),
    ]
    
    for script, label in enrichment_scripts:
        script_path = REPO_ROOT / script
        if not script_path.exists():
            print(f"    Skipping {script} (not yet implemented)")
            continue
        
        print(f"  {label}")
        result = subprocess.run(
            [sys.executable, script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"    Warning: {script} failed")
            if result.stderr:
                print(f"    {result.stderr}")


# ── Parsing Snapshots ─────────────────────────────────────────────────────────

def load_snapshot_json(domain: str) -> Dict[str, Any]:
    """Load latest cached snapshot for domain."""
    domain_dir = SNAPSHOT_CACHE_DIR / domain
    if not domain_dir.exists():
        return {"elements": []}
    
    snapshot_files = sorted(domain_dir.glob("*.json"), reverse=True)
    if not snapshot_files:
        return {"elements": []}
    
    import json
    with open(snapshot_files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def parse_profile_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse PROFILE snapshot."""
    chunks = []
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        # Build profile document
        lines = [
            f"# Profile: {snapshot_data.get('First Name', '')} {snapshot_data.get('Last Name', '')}",
            "",
            f"**Headline**: {snapshot_data.get('Headline', '')}",
            f"**Industry**: {snapshot_data.get('Industry', '')}",
            f"**Location**: {snapshot_data.get('Geo Location', '')}",
            "",
            "## Summary",
            snapshot_data.get('Summary', ''),
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_profile",
            max_tokens=INGEST.get("profile_max_tokens", 400),
            overlap=INGEST.get("profile_overlap", 0),
            metadata={
                "type": "profile",
                "source": "PROFILE",
                "entity_name": f"{snapshot_data.get('First Name', '')} {snapshot_data.get('Last Name', '')}",
            }
        ))
    
    return chunks


def parse_positions_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse POSITIONS snapshot."""
    chunks = []
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        lines = [
            f"# {snapshot_data.get('Title', 'Position')}",
            f"**Company**: {snapshot_data.get('Company Name', '')}",
            f"**Employment Type**: {snapshot_data.get('Employment Type', '')}",
            f"**Location**: {snapshot_data.get('Location', '')}",
            f"**Start Date**: {snapshot_data.get('Start Date', '')}",
            f"**End Date**: {snapshot_data.get('End Date', 'Present')}",
            "",
            "## Description",
            snapshot_data.get('Description', ''),
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_profile",
            max_tokens=INGEST.get("profile_max_tokens", 400),
            overlap=0,
            metadata={
                "type": "position",
                "source": "POSITIONS",
                "entity_name": snapshot_data.get('Company Name', ''),
            }
        ))
    
    return chunks


def parse_connections_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse CONNECTIONS snapshot (enriched with Tavily MDs)."""
    chunks = []
    
    # First, add basic connection data
    for elem in elements:
        for snapshot_data in elem.get("snapshotData", []):
            lines = [
                f"# {snapshot_data.get('First Name', '')} {snapshot_data.get('Last Name', '')}",
                f"**Company**: {snapshot_data.get('Company', '')}",
                f"**Position**: {snapshot_data.get('Position', '')}",
                f"**LinkedIn**: {snapshot_data.get('URL', '')}",
                f"**Connected On**: {snapshot_data.get('Connected On', '')}",
            ]
            
            content = "\n".join(lines)
            
            chunks.extend(chunk_text(
                text=content,
                domain="my_network",
                max_tokens=INGEST.get("default_max_tokens", 400),
                overlap=INGEST.get("default_overlap", 50),
                metadata={
                    "type": "connection",
                    "source": "CONNECTIONS",
                    "entity_name": f"{snapshot_data.get('First Name', '')} {snapshot_data.get('Last Name', '')}",
                }
            ))
    
    # Then, add enriched Tavily MDs if they exist
    enriched_dir = ENRICHED_DIR / "connections"
    if enriched_dir.exists():
        for md_file in enriched_dir.glob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks.extend(chunk_text(
                text=content,
                domain="my_network",
                max_tokens=INGEST.get("tavily_max_tokens", 500),
                overlap=INGEST.get("tavily_overlap", 50),
                metadata={
                    "type": "connection_enriched",
                    "source": "CONNECTIONS_TAVILY",
                    "entity_name": md_file.stem,
                }
            ))
    
    return chunks


def parse_companies_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse COMPANY_FOLLOWS snapshot (enriched with Tavily MDs)."""
    chunks = []
    
    # First, add basic company data
    for elem in elements:
        for snapshot_data in elem.get("snapshotData", []):
            lines = [
                f"# {snapshot_data.get('Organization', '')}",
                f"**Followed On**: {snapshot_data.get('Followed On', '')}",
            ]
            
            content = "\n".join(lines)
            
            chunks.extend(chunk_text(
                text=content,
                domain="companies",
                max_tokens=INGEST.get("default_max_tokens", 400),
                overlap=INGEST.get("default_overlap", 50),
                metadata={
                    "type": "company",
                    "source": "COMPANY_FOLLOWS",
                    "entity_name": snapshot_data.get('Organization', ''),
                }
            ))
    
    # Then, add enriched Tavily MDs if they exist
    enriched_dir = ENRICHED_DIR / "companies"
    if enriched_dir.exists():
        for md_file in enriched_dir.glob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks.extend(chunk_text(
                text=content,
                domain="companies",
                max_tokens=INGEST.get("tavily_max_tokens", 500),
                overlap=INGEST.get("tavily_overlap", 50),
                metadata={
                    "type": "company_enriched",
                    "source": "COMPANY_FOLLOWS_TAVILY",
                    "entity_name": md_file.stem,
                }
            ))
    
    return chunks


def parse_jobs_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse JOB_APPLICATIONS, SAVED_JOBS, SAVED_JOB_ALERTS snapshots."""
    chunks = []
    
    for elem in elements:
        for snapshot_data in elem.get("snapshotData", []):
            lines = [
                f"# {snapshot_data.get('Job Title', snapshot_data.get('Title', 'Job'))}",
                f"**Company**: {snapshot_data.get('Company', '')}",
                f"**Location**: {snapshot_data.get('Location', '')}",
            ]
            
            # Handle optional fields depending on source
            if "Applied Date" in snapshot_data:
                lines.append(f"**Applied**: {snapshot_data.get('Applied Date', '')}")
            if "Saved Date" in snapshot_data:
                lines.append(f"**Saved**: {snapshot_data.get('Saved Date', '')}")
            if "Description" in snapshot_data:
                lines.append(f"\n## Description\n\n{snapshot_data.get('Description', '')}")
            
            content = "\n".join(lines)
            
            chunks.extend(chunk_text(
                text=content,
                domain="jobs",
                max_tokens=INGEST.get("default_max_tokens", 400),
                overlap=INGEST.get("default_overlap", 50),
                metadata={
                    "type": "job",
                    "source": elem.get("snapshotDomain", "JOBS"),
                    "entity_name": snapshot_data.get('Company', ''),
                }
            ))
    
    return chunks


def parse_education_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse EDUCATION snapshot."""
    chunks = []
    
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        lines = [
            f"# {snapshot_data.get('School Name', 'Education')}",
            f"**Degree**: {snapshot_data.get('Degree Name', '')}",
            f"**Field of Study**: {snapshot_data.get('Field of Study', '')}",
            f"**Start Date**: {snapshot_data.get('Start Date', '')}",
            f"**End Date**: {snapshot_data.get('End Date', '')}",
            f"**Grade**: {snapshot_data.get('Grade', '')}",
            f"**Description**: {snapshot_data.get('Description', '')}",
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_profile",
            max_tokens=INGEST.get("profile_max_tokens", 400),
            overlap=0,
            metadata={
                "type": "education",
                "source": "EDUCATION",
                "entity_name": snapshot_data.get('School Name', ''),
            }
        ))
    
    return chunks


def parse_skills_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse SKILLS snapshot."""
    chunks = []
    
    skills = [elem.get("snapshotData", [{}])[0].get("Skill", "") for elem in elements]
    skills = [s for s in skills if s]
    
    content = "# Skills\n\n" + "\n".join(f"- {skill}" for skill in skills)
    
    chunks.extend(chunk_text(
        text=content,
        domain="my_profile",
        max_tokens=INGEST.get("profile_max_tokens", 400),
        overlap=0,
        metadata={
            "type": "skills",
            "source": "SKILLS",
            "entity_name": "Skills",
        }
    ))
    
    return chunks


def parse_certifications_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse CERTIFICATIONS snapshot."""
    chunks = []
    
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        lines = [
            f"# {snapshot_data.get('Name', 'Certification')}",
            f"**Issuer**: {snapshot_data.get('Issuer Organization Name', '')}",
            f"**Issued**: {snapshot_data.get('Issued On', '')}",
            f"**Expires**: {snapshot_data.get('Expires On', '')}",
            f"**Credential**: {snapshot_data.get('Credential ID', '')}",
            f"**URL**: {snapshot_data.get('Credential URL', '')}",
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_profile",
            max_tokens=INGEST.get("profile_max_tokens", 400),
            overlap=0,
            metadata={
                "type": "certification",
                "source": "CERTIFICATIONS",
                "entity_name": snapshot_data.get('Name', ''),
            }
        ))
    
    return chunks


def parse_languages_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse LANGUAGES snapshot."""
    chunks = []
    
    languages = [elem.get("snapshotData", [{}])[0].get("Language", "") for elem in elements]
    languages = [l for l in languages if l]
    
    content = "# Languages\n\n" + "\n".join(f"- {lang}" for lang in languages)
    
    chunks.extend(chunk_text(
        text=content,
        domain="my_profile",
        max_tokens=INGEST.get("profile_max_tokens", 400),
        overlap=0,
        metadata={
            "type": "languages",
            "source": "LANGUAGES",
            "entity_name": "Languages",
        }
    ))
    
    return chunks


def parse_publications_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse PUBLICATIONS snapshot."""
    chunks = []
    
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        lines = [
            f"# {snapshot_data.get('Title', 'Publication')}",
            f"**Publisher**: {snapshot_data.get('Publisher', '')}",
            f"**Published Date**: {snapshot_data.get('Published On', '')}",
            f"**Description**: {snapshot_data.get('Description', '')}",
            f"**URL**: {snapshot_data.get('Publication URL', '')}",
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_profile",
            max_tokens=INGEST.get("profile_max_tokens", 400),
            overlap=0,
            metadata={
                "type": "publication",
                "source": "PUBLICATIONS",
                "entity_name": snapshot_data.get('Title', ''),
            }
        ))
    
    return chunks


def parse_inbox_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse INBOX (messages) snapshot."""
    chunks = []
    
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        # Group messages by conversation
        lines = [
            f"# Conversation",
            f"**Participants**: {snapshot_data.get('Participants', '')}",
            f"**Last Message**: {snapshot_data.get('Last Activity', '')}",
            "",
            "## Messages",
            snapshot_data.get('Messages', ''),
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="communications",
            max_tokens=INGEST.get("messages_max_tokens", 300),
            overlap=INGEST.get("messages_overlap", 100),
            metadata={
                "type": "message",
                "source": "INBOX",
                "entity_name": "Conversation",
            }
        ))
    
    return chunks


def parse_job_saved_answers_snapshot(elements: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Parse JOB_APPLICANT_SAVED_ANSWERS snapshot."""
    chunks = []
    
    for elem in elements:
        snapshot_data = elem.get("snapshotData", [{}])[0]
        
        lines = [
            f"# Application Answer",
            f"**Question**: {snapshot_data.get('Question', '')}",
            f"**Answer**: {snapshot_data.get('Answer', '')}",
        ]
        
        content = "\n".join(lines)
        
        chunks.extend(chunk_text(
            text=content,
            domain="my_activity",
            max_tokens=INGEST.get("default_max_tokens", 400),
            overlap=0,
            metadata={
                "type": "saved_answer",
                "source": "JOB_APPLICANT_SAVED_ANSWERS",
                "entity_name": snapshot_data.get('Question', ''),
            }
        ))
    
    return chunks


PARSERS = {
    "PROFILE": parse_profile_snapshot,
    "POSITIONS": parse_positions_snapshot,
    "EDUCATION": parse_education_snapshot,
    "SKILLS": parse_skills_snapshot,
    "CERTIFICATIONS": parse_certifications_snapshot,
    "LANGUAGES": parse_languages_snapshot,
    "PUBLICATIONS": parse_publications_snapshot,
    "CONNECTIONS": parse_connections_snapshot,
    "COMPANY_FOLLOWS": parse_companies_snapshot,
    "JOB_APPLICATIONS": parse_jobs_snapshot,
    "SAVED_JOBS": parse_jobs_snapshot,
    "SAVED_JOB_ALERTS": parse_jobs_snapshot,
    "INBOX": parse_inbox_snapshot,
    "JOB_APPLICANT_SAVED_ANSWERS": parse_job_saved_answers_snapshot,
}


def parse_all_snapshots(verbose: bool = False) -> Dict[str, List[DocumentChunk]]:
    """Parse all cached snapshots into DocumentChunks."""
    all_chunks = {}
    
    for domain in PORTABILITY_API["snapshot_domains"]:
        if domain not in PARSERS:
            if verbose:
                print(f"  [{domain}] No parser defined, skipping")
            continue
        
        snapshot = load_snapshot_json(domain)
        elements = snapshot.get("elements", [])
        
        if not elements:
            if verbose:
                print(f"  [{domain}] No cached data found")
            continue
        
        try:
            parser = PARSERS[domain]
            chunks = parser(elements)
            all_chunks[domain] = chunks
            if verbose:
                print(f"  [{domain}] ✓ {len(chunks)} chunks")
        except Exception as e:
            print(f"  [{domain}] ✗ Parse error: {e}")
    
    return all_chunks


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_chunks(all_chunks: Dict[str, List[DocumentChunk]], dry_run: bool = False):
    """Ingest parsed chunks into ChromaDB collections."""
    if dry_run:
        print("\n[3/4] Ingestion (DRY RUN)\n")
        total_chunks = sum(len(chunks) for chunks in all_chunks.values())
        print(f"  Total chunks to ingest: {total_chunks}")
        for domain, chunks in all_chunks.items():
            print(f"    {domain}: {len(chunks)} chunks")
        return
    
    print("\n[3/4] Ingestion\n")
    
    store = VectorStore()
    total_ingested = 0
    
    for domain, chunks in all_chunks.items():
        # Determine which collection(s) this domain goes to
        if domain in ["PROFILE", "POSITIONS", "EDUCATION", "SKILLS", "CERTIFICATIONS", "LANGUAGES", "PUBLICATIONS"]:
            collection = "my_profile"
        elif domain in ["JOB_APPLICATIONS", "SAVED_JOBS", "SAVED_JOB_ALERTS", "JOB_APPLICANT_SAVED_ANSWERS"]:
            collection = "my_activity" if domain == "JOB_APPLICANT_SAVED_ANSWERS" else "jobs"
        elif domain == "CONNECTIONS":
            collection = "my_network"
        elif domain == "COMPANY_FOLLOWS":
            collection = "companies"
        elif domain == "INBOX":
            collection = "communications"
        else:
            continue
        
        print(f"  [{domain} → {collection}] Ingesting {len(chunks)} chunks...")
        store.upsert(collection, chunks)
        total_ingested += len(chunks)
    
    print(f"\n  ✓ Ingested {total_ingested} total chunks")


def show_stats():
    """Display ChromaDB collection statistics."""
    print("\nChromaDB collection stats:\n")
    store = VectorStore()
    
    total_chunks = 0
    for collection_name in COLLECTIONS.values():
        count = store.count(collection_name)
        total_chunks += count
        print(f"  {collection_name:<25} : {count:>6} chunks")
    
    print(f"\n  {'TOTAL':<25} : {total_chunks:>6} chunks\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def run():
    parser = argparse.ArgumentParser(description="LinkedIn Career Assistant — Phase 2 Ingestion")
    
    parser.add_argument("--fetch-all", action="store_true", help="Fetch all domains from API")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch only, do not enrich/ingest")
    parser.add_argument("--enrich-only", action="store_true", help="Enrich only, do not fetch/ingest")
    parser.add_argument("--ingest-only", action="store_true", help="Ingest only, do not fetch/enrich")
    parser.add_argument("--dry-run", action="store_true", help="Parse without embedding")
    parser.add_argument("--stats", action="store_true", help="Show ChromaDB stats only")
    parser.add_argument("--skip-cache", action="store_true", help="Ignore cached snapshots, fetch fresh")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # ── Stats mode (early exit)
    if args.stats:
        show_stats()
        return
    
    print(f"\n{'='*70}")
    print("  LinkedIn Career Assistant — Phase 2 Ingestion")
    print(f"{'='*70}\n")
    
    # ── Fetch
    if args.fetch_all or args.fetch_only or (not args.enrich_only and not args.ingest_only and not args.dry_run):
        print("[1/4] Snapshot Fetcher\n")
        try:
            run_snapshot_fetcher(skip_cache=args.skip_cache)
        except Exception as e:
            print(f"ERROR: {e}\n")
            raise SystemExit(1)
    
    if args.fetch_only:
        print("\n✓ Fetch complete.\n")
        return
    
    # ── Enrich
    if not args.ingest_only and not args.dry_run:
        run_enrichment_scripts()
    
    # ── Parse
    print("\n[3/4] Parsing Snapshots\n")
    all_chunks = parse_all_snapshots(verbose=args.verbose)
    print(f"  ✓ Parsed {sum(len(c) for c in all_chunks.values())} total chunks")
    
    # ── Ingest
    if not args.dry_run:
        ingest_chunks(all_chunks, dry_run=False)
    else:
        ingest_chunks(all_chunks, dry_run=True)
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        raise SystemExit(1)
    except Exception as e:
        print(f"\nERROR: {e}\n")
        raise SystemExit(1)
