"""
parsers/parse_network.py — Parses connections CSV + Tavily search MD files.

Strategy:
  1. Load Connections.csv → one DocumentChunk per connection (basic info)
  2. For each connection, look for a matching Tavily MD file in the
     connections enrichment folder → parse and add as additional chunks
  3. If no MD file exists, the CSV chunk is the only data for that person

Entity ID convention: the LinkedIn profile URL from the CSV.
This ensures CSV chunks and Tavily chunks for the same person share
the same entity_id prefix, enabling future dedup and joining.
"""

import csv
import re
from pathlib import Path
from utils.schema import DocumentChunk
from config import CSV, TAVILY


def _read_connections_csv() -> list[dict]:
    path = CSV["connections"]
    if not path.exists():
        print(f"[parse_network] Warning: {path} not found.")
        return []
    with open(path, encoding="utf-8-sig") as f:
        # LinkedIn sometimes adds 3 header rows — skip until we find the real header
        content = f.read()
    lines = content.splitlines()
    # Find the line that contains the actual CSV header
    header_idx = next(
        (i for i, l in enumerate(lines) if "First Name" in l), 0
    )
    reader = csv.DictReader(lines[header_idx:])
    return list(reader)


def _url_to_filename(url: str) -> str:
    """
    Convert a LinkedIn URL to the expected MD filename.
    e.g. https://www.linkedin.com/in/daveagill → Connection_in_daveagill.md
    """
    slug = url.rstrip("/").split("/")[-1]
    return f"Connection_in_{slug}.md"


def _parse_md_file(path: Path) -> str:
    """Read a Tavily MD file and return its text content."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"[parse_network] Warning: could not read {path}: {e}")
        return ""


def _clean_md_text(text: str) -> str:
    """
    Strip image markdown and excessive whitespace from Tavily MD output.
    Keeps text content, links (as plain text), and headings.
    """
    # Remove image tags: ![...](...)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────
# Parse connections CSV
# ─────────────────────────────────────────────

def parse_connections_csv() -> list[DocumentChunk]:
    rows = _read_connections_csv()
    chunks = []
    for row in rows:
        first   = row.get("First Name", "").strip()
        last    = row.get("Last Name", "").strip()
        url     = row.get("URL", "").strip()
        email   = row.get("Email Address", "").strip()
        company = row.get("Company", "").strip()
        pos     = row.get("Position", "").strip()
        conn_on = row.get("Connected On", "").strip()

        name = f"{first} {last}".strip()
        if not name:
            continue

        parts = [f"Connection: {name}"]
        if pos:     parts.append(f"Role: {pos}")
        if company: parts.append(f"Company: {company}")
        if email:   parts.append(f"Email: {email}")
        if conn_on: parts.append(f"Connected since: {conn_on}")
        if url:     parts.append(f"LinkedIn: {url}")

        entity_id = url if url else f"connection::{name.lower().replace(' ', '_')}"

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_network",
            source="csv",
            type="connection_profile",
            entity_id=entity_id,
            entity_name=name,
            company=company or None,
            url=url or None,
            extra={"email": email} if email else {},
        ))
    print(f"[parse_network] {len(chunks)} connection chunks from CSV.")
    return chunks


# ─────────────────────────────────────────────
# Parse Tavily enrichment MD files for connections
# ─────────────────────────────────────────────

def parse_connections_tavily() -> list[DocumentChunk]:
    tavily_dir = TAVILY["connections_dir"]
    if not tavily_dir.exists():
        print(f"[parse_network] Warning: Tavily connections dir not found: {tavily_dir}")
        return []

    md_files = list(tavily_dir.glob("*.md"))
    print(f"[parse_network] Found {len(md_files)} Tavily connection MD files.")

    chunks = []
    seen_entity_ids: set[str] = set()

    for md_path in md_files:
        raw = _parse_md_file(md_path)
        if not raw:
            continue

        text = _clean_md_text(raw)

        # Extract name from first heading if present
        name_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        entity_name = name_match.group(1).strip() if name_match else md_path.stem

        # Extract LinkedIn URL from the file content
        url_match = re.search(r"https://(?:www\.)?linkedin\.com/in/[\w\-]+", text)
        url = url_match.group(0) if url_match else ""

        base_id   = url if url else f"tavily_search::{md_path.stem}"
        entity_id = base_id

        if entity_id in seen_entity_ids:
            # Duplicate MD file for the same person — make ID unique via filename
            entity_id = f"{base_id}::{md_path.stem}"
            print(f"[parse_network] Duplicate entity_id resolved: {base_id} → {entity_id}")

        seen_entity_ids.add(entity_id)

        chunks.append(DocumentChunk(
            document=text,
            collection="my_network",
            source="tavily_search",
            type="connection_profile",
            entity_id=entity_id,
            entity_name=entity_name,
            url=url or None,
            extra={"md_file": md_path.name},
        ))

    print(f"[parse_network] {len(chunks)} chunks from Tavily connection MDs.")
    return chunks


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def parse_all_network() -> list[DocumentChunk]:
    chunks = []
    chunks.extend(parse_connections_csv())
    chunks.extend(parse_connections_tavily())
    print(f"[parse_network] Total network chunks: {len(chunks)}")
    return chunks