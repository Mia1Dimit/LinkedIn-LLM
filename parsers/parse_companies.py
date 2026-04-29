"""
parsers/parse_companies.py — Parses company follows CSV + Tavily extract MD files.

Entity ID convention: LinkedIn company URL (from CSV column 3 or extracted from MD).
"""

import csv
import re
from pathlib import Path
from utils.schema import DocumentChunk
from config import CSV, TAVILY


def _read_company_follows_csv() -> list[dict]:
    path = CSV["company_follows"]
    if not path.exists():
        print(f"[parse_companies] Warning: {path} not found.")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _clean_md_text(text: str) -> str:
    """Strip image markdown, collapse whitespace."""
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────
# Company Follows CSV
# ─────────────────────────────────────────────

def parse_company_follows_csv() -> list[DocumentChunk]:
    rows = _read_company_follows_csv()
    chunks = []
    for row in rows:
        org         = row.get("Organization", "").strip()
        followed_on = row.get("Followed On", "").strip()
        li_url      = row.get("LinkedIn URL", "").strip()   # manually added column

        if not org:
            continue

        parts = [f"Company followed: {org}"]
        if followed_on: parts.append(f"Followed since: {followed_on}")
        if li_url:      parts.append(f"LinkedIn: {li_url}")

        entity_id = li_url if li_url else f"company_follows::{org.lower().replace(' ', '_')}"

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="companies",
            source="csv",
            type="company_profile",
            entity_id=entity_id,
            entity_name=org,
            url=li_url or None,
            extra={"followed_on": followed_on},
        ))

    print(f"[parse_companies] {len(chunks)} company chunks from CSV.")
    return chunks


# ─────────────────────────────────────────────
# Tavily extract MD files (companies)
# ─────────────────────────────────────────────

def parse_companies_tavily() -> list[DocumentChunk]:
    tavily_dir = TAVILY["companies_dir"]
    if not tavily_dir.exists():
        print(f"[parse_companies] Warning: Tavily companies dir not found: {tavily_dir}")
        return []

    md_files = list(tavily_dir.glob("*.md"))
    print(f"[parse_companies] Found {len(md_files)} Tavily company MD files.")

    chunks = []
    for md_path in md_files:
        try:
            raw = md_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[parse_companies] Could not read {md_path}: {e}")
            continue

        if not raw:
            continue

        text = _clean_md_text(raw)

        # Extract company name from first heading
        name_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        entity_name = name_match.group(1).strip() if name_match else md_path.stem

        # Extract LinkedIn company URL
        url_match = re.search(
            r"https://(?:www\.)?linkedin\.com/company/[\w\-]+", text
        )
        url = url_match.group(0).rstrip("/") if url_match else ""

        entity_id = url if url else f"tavily_extract::{md_path.stem}"

        # Split company profile from posts — posts get separate chunks
        # Look for a "## Posts" section
        post_section_match = re.search(r"^##\s+Posts", text, re.MULTILINE)

        if post_section_match:
            profile_text = text[:post_section_match.start()].strip()
            posts_text   = text[post_section_match.start():].strip()
        else:
            profile_text = text
            posts_text   = ""

        # Profile chunk
        if profile_text:
            chunks.append(DocumentChunk(
                document=profile_text,
                collection="companies",
                source="tavily_extract",
                type="company_profile",
                entity_id=entity_id,
                entity_name=entity_name,
                url=url or None,
                extra={"md_file": md_path.name},
            ))

        # Posts chunk (separate so retrieval can target just posts)
        if posts_text:
            chunks.append(DocumentChunk(
                document=f"Recent posts from {entity_name}:\n\n{posts_text}",
                collection="companies",
                source="tavily_extract",
                type="company_post",
                entity_id=f"{entity_id}::posts",
                entity_name=f"{entity_name} — Posts",
                url=url or None,
                extra={"md_file": md_path.name},
            ))

    print(f"[parse_companies] {len(chunks)} chunks from Tavily company MDs.")
    return chunks


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def parse_all_companies() -> list[DocumentChunk]:
    chunks = []
    chunks.extend(parse_company_follows_csv())
    chunks.extend(parse_companies_tavily())
    print(f"[parse_companies] Total company chunks: {len(chunks)}")
    return chunks
