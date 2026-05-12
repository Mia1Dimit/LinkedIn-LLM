#!/usr/bin/env python3
"""Report whether parsed chunks differ from the current Chroma contents."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db.vector_store import VectorStore
from ingest import parse_all_snapshots
from utils.schema import DocumentChunk


DOMAIN_TO_COLLECTION = {
    "PROFILE": "my_profile",
    "POSITIONS": "my_profile",
    "EDUCATION": "my_profile",
    "SKILLS": "my_profile",
    "CERTIFICATIONS": "my_profile",
    "LANGUAGES": "my_profile",
    "PUBLICATIONS": "my_profile",
    "CONNECTIONS": "my_network",
    "COMPANY_FOLLOWS": "companies",
    "INBOX": "communications",
    "JOB_APPLICATIONS": "jobs",
    "SAVED_JOBS": "jobs",
    "SAVED_JOB_ALERTS": "jobs",
    "JOB_APPLICANT_SAVED_ANSWERS": "my_activity",
}


def bucket_chunks_by_collection(all_chunks: dict[str, list[DocumentChunk]]) -> dict[str, list[DocumentChunk]]:
    by_collection: dict[str, list[DocumentChunk]] = defaultdict(list)
    for domain, chunks in all_chunks.items():
        collection = DOMAIN_TO_COLLECTION.get(domain)
        if collection:
            by_collection[collection].extend(chunks)
    return dict(by_collection)


def build_collection_status(store: VectorStore, collection_name: str, chunks: list[DocumentChunk]) -> dict[str, int]:
    collection = store._get_collection(collection_name)
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    existing_ids = store._existing_ids(collection, chunk_ids)
    existing_hashes = store._existing_hashes(collection, list(existing_ids))

    missing = 0
    changed = 0
    unchanged = 0
    for chunk in chunks:
        if chunk.chunk_id not in existing_ids:
            missing += 1
            continue

        stored_hash = existing_hashes.get(chunk.chunk_id)
        if stored_hash == chunk.content_hash:
            unchanged += 1
        else:
            changed += 1

    return {
        "parsed": len(chunks),
        "current": collection.count(),
        "missing": missing,
        "changed": changed,
        "unchanged": unchanged,
    }


def main() -> int:
    all_chunks = parse_all_snapshots(verbose=False)
    chunks_by_collection = bucket_chunks_by_collection(all_chunks)
    store = VectorStore()

    collections: dict[str, dict[str, int]] = {}
    ingest_needed = False

    for collection_name, chunks in chunks_by_collection.items():
        status = build_collection_status(store, collection_name, chunks)
        collections[collection_name] = status
        if status["missing"] > 0 or status["changed"] > 0:
            ingest_needed = True

    print(json.dumps({
        "ingest_needed": ingest_needed,
        "collections": collections,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())