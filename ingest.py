"""
ingest.py — Main ingestion pipeline.

Runs all parsers → chunker → upserts to ChromaDB via Bedrock embeddings.

Usage:
    python ingest.py                    # ingest everything
    python ingest.py --only profile     # ingest only my_profile data
    python ingest.py --dry-run          # parse + chunk, no embedding/upsert
    python ingest.py --stats            # print ChromaDB collection stats
"""

import argparse
import time
from utils.chunker import chunk_all
from db.vector_store import VectorStore
from parsers.parse_profile   import parse_all_profile
from parsers.parse_network   import parse_all_network
from parsers.parse_companies import parse_all_companies
from parsers.parse_activity  import parse_all_activity
from parsers.parse_messages  import parse_messages


PARSERS = {
    "profile":    parse_all_profile,
    "network":    parse_all_network,
    "companies":  parse_all_companies,
    "activity":   parse_all_activity,
    "messages":   parse_messages,
}


def run_ingestion(only: str = None, dry_run: bool = False):
    start = time.time()
    total_stats = {"inserted": 0, "skipped": 0, "errors": 0}

    # Initialise vector store (connects to ChromaDB, sets up Bedrock)
    store = None if dry_run else VectorStore()

    parsers_to_run = (
        {only: PARSERS[only]} if only and only in PARSERS
        else PARSERS
    )

    for name, parser_fn in parsers_to_run.items():
        print(f"\n{'─'*50}")
        print(f"[ingest] Parsing: {name}")
        print(f"{'─'*50}")

        # 1. Parse raw data into DocumentChunks
        raw_chunks = parser_fn()

        # 2. Chunk long documents
        chunked = chunk_all(raw_chunks)
        print(f"[ingest] {name}: {len(raw_chunks)} raw → {len(chunked)} after chunking")

        if dry_run:
            # Print a sample chunk for inspection
            if chunked:
                sample = chunked[0]
                print(f"\n[DRY RUN] Sample chunk from '{name}':")
                print(f"  ID:         {sample.chunk_id}")
                print(f"  Collection: {sample.collection}")
                print(f"  Type:       {sample.type}")
                print(f"  Entity:     {sample.entity_name}")
                print(f"  Hash:       {sample.content_hash}")
                print(f"  Document preview:\n    {sample.document[:200]}...")
            continue

        # 3. Embed + upsert to ChromaDB
        stats = store.upsert(chunked)
        for k in total_stats:
            total_stats[k] += stats.get(k, 0)

        print(f"[ingest] {name} done: "
              f"{stats['inserted']} inserted, "
              f"{stats['skipped']} skipped, "
              f"{stats['errors']} errors")

    elapsed = time.time() - start
    print(f"\n{'═'*50}")
    print(f"[ingest] Ingestion complete in {elapsed:.1f}s")
    if not dry_run:
        print(f"  Inserted: {total_stats['inserted']}")
        print(f"  Skipped:  {total_stats['skipped']}")
        print(f"  Errors:   {total_stats['errors']}")
        print(f"\n[ingest] Collection stats:")
        for coll, count in store.stats().items():
            print(f"  {coll}: {count} chunks")
    print(f"{'═'*50}")


def print_stats():
    store = VectorStore()
    print("\nChromaDB collection stats:")
    for coll, count in store.stats().items():
        print(f"  {coll:20s}: {count:6d} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Career Assistant — Ingestion Pipeline")
    parser.add_argument("--only",    choices=list(PARSERS.keys()), help="Run only one parser")
    parser.add_argument("--dry-run", action="store_true", help="Parse + chunk only, no embedding/upsert")
    parser.add_argument("--stats",   action="store_true", help="Print collection stats and exit")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        run_ingestion(only=args.only, dry_run=args.dry_run)
