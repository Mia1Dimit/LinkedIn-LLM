#!/usr/bin/env python3
"""Rebuild enriched markdowns with only required fields.

This script performs a one-time migration:
1) Renames data/enriched -> data/enriched_unstructured
2) Recreates data/enriched/{companies,connections}
3) Rewrites each markdown with strict, reduced schemas per domain
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
ENRICHED_DIR = DATA_DIR / "enriched"
BACKUP_DIR = DATA_DIR / "enriched_unstructured"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _title_from_slug(url: str) -> str:
    if not url or url.upper() == "N/A" or not url.lower().startswith("http"):
        return "N/A"
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[-_]+", " ", slug)
    return _clean(slug.title()) if slug else "N/A"


def _extract_line_field(text: str, label: str) -> str:
    patterns = [
        rf"\*\*{re.escape(label)}\s*:\*\*\s*(.+)",
        rf"\*\*{re.escape(label)}\*\*\s*:\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _clean(m.group(1))
    return "N/A"


def _extract_header_value(text: str, header: str) -> str:
    pattern = rf"^{re.escape(header)}\s*$\n(.+?)(?=^#|\Z)"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not m:
        return "N/A"
    value = _clean(m.group(1).replace("  ", " "))
    return value if value else "N/A"


def _extract_section_text(text: str, headings: list[str]) -> str:
    for heading in headings:
        pattern = rf"^{re.escape(heading)}\s*$\n(.+?)(?=^##\s|^###\s|^####\s|\Z)"
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not m:
            continue
        block = m.group(1).strip()
        if not block:
            continue
        lines = []
        for raw in block.splitlines():
            line = _clean(raw)
            if not line:
                continue
            lines.append(line)
        if lines:
            return "\n".join(lines)
    return "N/A"


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []

    # Prefer markdown links where destination URL is explicit.
    for _, dest in re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", text):
        urls.append(dest)

    # Then capture any remaining bare URLs.
    urls.extend(re.findall(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", text))

    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        u = url.rstrip(").,;\"]'")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _extract_company_name(text: str, source_url: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.lower().startswith("# extracted:"):
            name = _clean(stripped[2:])
            if name:
                return name
    return _title_from_slug(source_url)


def _extract_industry(text: str) -> str:
    industry = _extract_header_value(text, "### Industry")
    if industry != "N/A":
        return industry

    # Try top summary line style: "Industry • City • ..."
    for line in text.splitlines():
        if "•" in line:
            left = _clean(line.split("•", 1)[0])
            if left and len(left) <= 80:
                return left
    return "N/A"


def _extract_company_size(text: str) -> str:
    size = _extract_header_value(text, "### Company Size")
    if size != "N/A":
        return size.splitlines()[0].strip()

    m = re.search(r"\b\d+[\d,]*\s*-\s*\d+[\d,]*\s+employees\b", text, re.IGNORECASE)
    if m:
        return _clean(m.group(0))

    m = re.search(r"View all\s+\d+[\d,]*\s+employees", text, re.IGNORECASE)
    if m:
        return _clean(m.group(0))

    return "N/A"


def _extract_founded(text: str) -> str:
    for key in ("### Founded", "**Founded**", "Founded:"):
        m = re.search(rf"{re.escape(key)}\s*:?\s*(.+)", text, re.IGNORECASE)
        if m:
            value = _clean(m.group(1))
            if value:
                return value
    return "N/A"


def _extract_website_url(text: str, source_url: str) -> str:
    section = _extract_section_text(text, ["### Website", "## Website"])
    if section != "N/A":
        urls = _extract_urls(section)
        if urls:
            return urls[0]

    candidates: list[str] = []

    def host_for(url: str) -> str:
        try:
            return (urlparse(url).netloc or "").lower()
        except ValueError:
            return ""

    for url in _extract_urls(text):
        lowered = url.lower()
        if "linkedin.com" in lowered or "lnkd.in" in lowered:
            continue
        if source_url != "N/A" and url.rstrip("/") == source_url.rstrip("/"):
            continue
        host = host_for(url)
        if host in {"react.js", "asp.net", "vue.js"}:
            continue
        candidates.append(url)

    if not candidates:
        return "N/A"

    if source_url != "N/A":
        slug = source_url.rstrip("/").split("/")[-1].lower()
        stem = slug.split("-")[0]
        for candidate in candidates:
            host = host_for(candidate)
            if stem and stem in host:
                return candidate

    return candidates[0]


def _extract_locations(text: str) -> list[str]:
    block = _extract_section_text(text, ["## Locations", "### Locations"])
    if block == "N/A":
        return ["N/A"]

    lines = [_clean(line) for line in block.splitlines() if _clean(line)]
    if not lines:
        return ["N/A"]

    compact: list[str] = []
    i = 0
    while i < len(lines):
        if i + 1 < len(lines) and not lines[i].startswith("http") and not lines[i + 1].startswith("http"):
            if re.search(r"\d{4,}", lines[i + 1]) or "," in lines[i + 1]:
                compact.append(f"{lines[i]}, {lines[i + 1]}")
                i += 2
                continue
        compact.append(lines[i])
        i += 1

    seen: set[str] = set()
    out: list[str] = []
    for loc in compact:
        if loc not in seen:
            seen.add(loc)
            out.append(loc)
    return out or ["N/A"]


def _extract_specialties(text: str) -> list[str]:
    block = _extract_section_text(text, ["### Specialties", "## Specialties"])
    if block == "N/A":
        return ["N/A"]
    parts = [p.strip(" -") for p in re.split(r"\n|,|;", block)]
    parts = [p for p in parts if p]
    return parts or ["N/A"]


def normalize_company_md(text: str) -> str:
    source_url = _extract_line_field(text, "Source URL")
    if source_url == "N/A":
        m = re.search(r"^#\s*Extracted:\s*(https?://\S+)", text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            source_url = _clean(m.group(1).rstrip("/")) + "/"
    extracted_at = _extract_line_field(text, "Extracted at")
    company_name = _extract_company_name(text, source_url)

    overview = _extract_section_text(text, ["## Overview", "## About us", "## About Us", "## About"])
    locations = _extract_locations(text)
    website_url = _extract_website_url(text, source_url)
    industry = _extract_industry(text)
    company_size = _extract_company_size(text)
    founded = _extract_founded(text)
    investors = _extract_section_text(text, ["### Investors", "## Investors"])
    funding = _extract_section_text(text, ["### Funding", "## Funding"])
    specialties = _extract_specialties(text)

    lines = [
        f"# {company_name}",
        f"**Company Name:** {company_name}",
        f"**Source URL:** {source_url}",
        f"**Extracted At:** {extracted_at}",
        "",
        "## About Us/Overview",
        overview,
        "",
        "## Locations",
        *[f"- {loc}" for loc in locations],
        "",
        "## Website URL",
        website_url,
        "",
        "## Industry",
        industry,
        "",
        "## Company Size",
        company_size,
        "",
        "## Founded",
        founded,
        "",
        "## Investors",
        investors,
        "",
        "## Funding",
        funding,
        "",
        "## Specialties",
        *[f"- {item}" for item in specialties],
        "",
    ]
    return "\n".join(lines)


def _extract_connected_on(text: str) -> str:
    for label in ("Connected", "Connected On"):
        value = _extract_line_field(text, label)
        if value != "N/A":
            return value
    return "N/A"


def _extract_connection_name(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            name = _clean(stripped[2:])
            # Remove credentials after comma for "Name and Surname" requirement.
            name = _clean(name.split(",", 1)[0])
            if name and not name.lower().startswith("extracted:"):
                return name
    return "N/A"


def normalize_connection_md(text: str) -> str:
    name = _extract_connection_name(text)
    current_company = _extract_line_field(text, "Current Company")
    position = _extract_line_field(text, "Position")
    linkedin_url = _extract_line_field(text, "LinkedIn URL")
    connected_on = _extract_connected_on(text)
    summary = _extract_section_text(text, ["## Professional Summary"])

    lines = [
        f"# {name}",
        f"**Name and Surname:** {name}",
        f"**Current Company:** {current_company}",
        f"**Position:** {position}",
        f"**LinkedIn URL:** {linkedin_url}",
        f"**Connected On:** {connected_on}",
        "",
        "## Professional Summary",
        summary,
        "",
    ]
    return "\n".join(lines)


def migrate() -> tuple[int, int]:
    """Full (re)build: read all files from BACKUP_DIR, normalise, write to ENRICHED_DIR."""
    source_root: Path

    if BACKUP_DIR.exists():
        source_root = BACKUP_DIR
    else:
        if not ENRICHED_DIR.exists():
            raise FileNotFoundError(f"Missing folder: {ENRICHED_DIR}")
        try:
            ENRICHED_DIR.rename(BACKUP_DIR)
        except PermissionError:
            # Fallback on Windows when direct folder rename is denied.
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            for child in ENRICHED_DIR.iterdir():
                target = BACKUP_DIR / child.name
                try:
                    shutil.move(str(child), str(target))
                except Exception:
                    if child.is_dir():
                        shutil.copytree(child, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(child, target)
        source_root = BACKUP_DIR

    # Recreate destination root for normalized output.
    shutil.rmtree(ENRICHED_DIR, ignore_errors=True)
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    new_companies = ENRICHED_DIR / "companies"
    new_connections = ENRICHED_DIR / "connections"
    new_companies.mkdir(parents=True, exist_ok=True)
    new_connections.mkdir(parents=True, exist_ok=True)

    company_count = 0
    connection_count = 0

    old_companies = source_root / "companies"
    if old_companies.exists():
        for md_file in sorted(old_companies.glob("*.md")):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            normalized = normalize_company_md(content)
            (new_companies / md_file.name).write_text(normalized, encoding="utf-8")
            company_count += 1

    old_connections = source_root / "connections"
    if old_connections.exists():
        for md_file in sorted(old_connections.glob("*.md")):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            normalized = normalize_connection_md(content)
            (new_connections / md_file.name).write_text(normalized, encoding="utf-8")
            connection_count += 1

    return company_count, connection_count


def migrate_new_only() -> tuple[int, int]:
    """Incremental build: only normalise files in BACKUP_DIR not yet present in ENRICHED_DIR.

    Used in the regular sync pipeline after enrichment. Leaves existing files in ENRICHED_DIR
    untouched and only adds newly-enriched (unstructured) files.
    """
    if not BACKUP_DIR.exists():
        raise FileNotFoundError(
            f"Unstructured source folder missing: {BACKUP_DIR}\n"
            "Run the full migration first: python scripts/rebuild_enriched_markdowns.py --yes"
        )

    out_companies = ENRICHED_DIR / "companies"
    out_connections = ENRICHED_DIR / "connections"
    out_companies.mkdir(parents=True, exist_ok=True)
    out_connections.mkdir(parents=True, exist_ok=True)

    company_count = 0
    connection_count = 0

    src_companies = BACKUP_DIR / "companies"
    if src_companies.exists():
        for md_file in sorted(src_companies.glob("*.md")):
            dest = out_companies / md_file.name
            if not dest.exists():
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                normalized = normalize_company_md(content)
                dest.write_text(normalized, encoding="utf-8")
                company_count += 1

    src_connections = BACKUP_DIR / "connections"
    if src_connections.exists():
        for md_file in sorted(src_connections.glob("*.md")):
            dest = out_connections / md_file.name
            if not dest.exists():
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                normalized = normalize_connection_md(content)
                dest.write_text(normalized, encoding="utf-8")
                connection_count += 1

    return company_count, connection_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild enriched markdowns to strict minimal schemas")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Execute FULL migration: (re)build all files from enriched_unstructured → enriched",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Incremental mode: only rebuild files in enriched_unstructured not yet in enriched",
    )
    args = parser.parse_args()

    if args.new_only:
        companies, connections = migrate_new_only()
        if companies == 0 and connections == 0:
            print("No new files to rebuild.")
        else:
            print(f"Incremental rebuild completed.")
            print(f"  new companies rebuilt: {companies}")
            print(f"  new connections rebuilt: {connections}")
        return 0

    if not args.yes:
        print("Dry run only. Re-run with --yes to execute full migration, or --new-only for incremental.")
        print(f"Source (unstructured): {BACKUP_DIR}")
        print(f"Destination (structured): {ENRICHED_DIR}")
        return 0

    companies, connections = migrate()
    print("Full migration completed.")
    print(f"companies rewritten: {companies}")
    print(f"connections rewritten: {connections}")
    print(f"source folder: {BACKUP_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
