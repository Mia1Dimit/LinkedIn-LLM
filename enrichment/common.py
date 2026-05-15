#!/usr/bin/env python3

import json
import os
import re
import shutil
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = REPO_ROOT / "data" / "api_snapshots"
# Enrichment scripts write raw Tavily output here; rebuild then normalises to data/enriched/
ENRICHED_DIR = REPO_ROOT / "data" / "enriched_unstructured"
LEGACY_ENRICHMENT_DIR = REPO_ROOT / "Phase 1" / "tavily_scripts"
LEGACY_CONNECTIONS_DIR = LEGACY_ENRICHMENT_DIR / "Connections"
LEGACY_COMPANIES_DIR = LEGACY_ENRICHMENT_DIR / "Companies"
TAVILY_USAGE_ENDPOINT = "https://api.tavily.com/usage"

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S UTC",
    "%a %b %d %H:%M:%S UTC %Y",
    "%m/%d/%y, %I:%M %p",
    "%d %b %Y",
    "%b %Y",
    "%Y",
]


def utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def file_has_content(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def slugify_text(value: str, max_len: int = 120) -> str:
    slug = re.sub(r"[^\w\-]", "_", value.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:max_len] or "item"


def normalize_lookup_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"https?://(www\.)?linkedin\.com/(company|showcase|in)/", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def slugify_linkedin_url(url: str, max_len: int = 120) -> str:
    slug = re.sub(r"https?://(www\.)?linkedin\.com/", "", url.strip(), flags=re.IGNORECASE)
    slug = re.sub(r"[^\w\-]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:max_len] or "connection"


def parse_date(value: str) -> Optional[datetime]:
    cleaned = value.strip()
    if not cleaned:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def latest_snapshot_path(domain: str) -> Optional[Path]:
    domain_dir = SNAPSHOT_DIR / domain
    if not domain_dir.exists():
        return None
    snapshot_files = sorted(domain_dir.glob("*.json"), reverse=True)
    return snapshot_files[0] if snapshot_files else None


def load_latest_snapshot(domain: str) -> dict[str, Any]:
    snapshot_path = latest_snapshot_path(domain)
    if snapshot_path is None:
        raise FileNotFoundError(f"No cached snapshot found for domain {domain}")
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def snapshot_rows(domain: str) -> list[dict[str, Any]]:
    payload = load_latest_snapshot(domain)
    rows: list[dict[str, Any]] = []
    for element in payload.get("elements", []):
        rows.extend(element.get("snapshotData", []))
    return rows


def resolve_tavily_api_key() -> str:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if key:
        return key
    # Fallback: load from credentials file
    creds_path = REPO_ROOT / "data" / "creds" / "tavily_key.json"
    if creds_path.exists():
        try:
            payload = json.loads(creds_path.read_text(encoding="utf-8"))
            key = str(payload.get("api_key", "")).strip()
            if key:
                return key
        except Exception:
            pass
    return ""


def get_tavily_usage(api_key: str) -> Optional[dict[str, Any]]:
    if not api_key:
        return None
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        project_id = os.getenv("TAVILY_PROJECT_ID", "").strip()
        if project_id:
            headers["X-Project-ID"] = project_id

        response = requests.get(
            TAVILY_USAGE_ENDPOINT,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def sync_legacy_connections(connections: list[dict[str, Any]], output_dir: Path) -> int:
    if not LEGACY_CONNECTIONS_DIR.exists():
        return 0

    legacy_by_url: dict[str, Path] = {}
    for path in LEGACY_CONNECTIONS_DIR.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        match = re.search(r"\*\*LinkedIn URL:\*\*\s*(\S+)", text)
        if match:
            legacy_by_url[match.group(1).strip()] = path

    copied = 0
    for connection in connections:
        target_path = output_dir / f"Connection_{slugify_linkedin_url(connection['url'])}.md"
        if file_has_content(target_path):
            continue
        legacy_path = legacy_by_url.get(connection.get("url", ""))
        if legacy_path is None:
            fallback = LEGACY_CONNECTIONS_DIR / target_path.name
            legacy_path = fallback if file_has_content(fallback) else None
        if legacy_path and file_has_content(legacy_path):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_path, target_path)
            copied += 1
    return copied


def sync_legacy_companies(companies: list[dict[str, Any]], output_dir: Path) -> int:
    if not LEGACY_COMPANIES_DIR.exists():
        return 0

    legacy_index: dict[str, Path] = {}
    for path in LEGACY_COMPANIES_DIR.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        aliases: set[str] = set()
        source_match = re.search(r"^# Extracted:\s+(\S+)", text, flags=re.M)
        if source_match:
            aliases.add(source_match.group(1).strip())
        for heading in re.findall(r"^#\s+(.+)$", text, flags=re.M):
            if heading.startswith("Extracted:"):
                continue
            aliases.add(heading.strip())
        aliases.add(path.stem.removeprefix("Company_"))

        for alias in aliases:
            key = normalize_lookup_key(alias)
            if key and key not in legacy_index:
                legacy_index[key] = path

    copied = 0
    for company in companies:
        target_path = output_dir / f"Company_{slugify_text(company['organization'])}.md"
        if file_has_content(target_path):
            continue
        legacy_path = legacy_index.get(normalize_lookup_key(company.get("organization", "")))
        if legacy_path and file_has_content(legacy_path):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_path, target_path)
            copied += 1
    return copied