"""Run a retrieval-quality evaluation suite over the local vector store.

This harness evaluates retrieval quality without calling the LLM.
It focuses on evidence quality, noise rate, and collection/source coverage.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from db.vector_store import VectorStore
from query.ask import NOISY_DOCUMENT_MARKERS, retrieve_hits


def detect_noise_hits(text: str) -> int:
    lowered = text.lower()
    return sum(1 for marker in NOISY_DOCUMENT_MARKERS if marker in lowered)


def evaluate_query(store: VectorStore, query: str, top_k: int) -> dict:
    hits = retrieve_hits(store, query, n_results=top_k)
    if not hits:
        return {
            "query": query,
            "hit_count": 0,
            "avg_distance": None,
            "noise_hit_rate": 0.0,
            "collection_breakdown": {},
            "source_breakdown": {},
            "top_hit_preview": "",
        }

    distances = [float(hit.get("distance", 1.0)) for hit in hits]
    noisy_hits = [hit for hit in hits if detect_noise_hits(hit.get("document", "")) > 0]
    collections = Counter(hit.get("collection", "unknown") for hit in hits)
    sources = Counter(hit.get("metadata", {}).get("source", "unknown") for hit in hits)

    top_preview = hits[0].get("document", "").replace("\n", " ").strip()[:200]

    return {
        "query": query,
        "hit_count": len(hits),
        "avg_distance": sum(distances) / len(distances),
        "noise_hit_rate": len(noisy_hits) / len(hits),
        "collection_breakdown": dict(collections),
        "source_breakdown": dict(sources),
        "top_hit_preview": top_preview,
    }


def aggregate_results(results: list[dict]) -> dict:
    non_empty = [r for r in results if r["hit_count"] > 0]
    if not non_empty:
        return {
            "queries": len(results),
            "answered": 0,
            "avg_hits": 0,
            "avg_distance": None,
            "avg_noise_hit_rate": 0,
            "collection_coverage": {},
            "source_coverage": {},
        }

    collection_counter = Counter()
    source_counter = Counter()
    for row in non_empty:
        collection_counter.update(row["collection_breakdown"])
        source_counter.update(row["source_breakdown"])

    return {
        "queries": len(results),
        "answered": len(non_empty),
        "avg_hits": sum(row["hit_count"] for row in non_empty) / len(non_empty),
        "avg_distance": sum(row["avg_distance"] for row in non_empty if row["avg_distance"] is not None) / len(non_empty),
        "avg_noise_hit_rate": sum(row["noise_hit_rate"] for row in non_empty) / len(non_empty),
        "collection_coverage": dict(collection_counter),
        "source_coverage": dict(source_counter),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run retrieval quality eval suite")
    parser.add_argument(
        "--queries",
        default="evaluation/queries_retrieval.json",
        help="Path to JSON array of evaluation queries",
    )
    parser.add_argument("--top-k", type=int, default=8, help="Number of hits per query")
    parser.add_argument(
        "--output",
        default="evaluation/reports/retrieval_eval_latest.json",
        help="JSON report output path",
    )
    args = parser.parse_args()

    queries_path = Path(args.queries)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
        raise ValueError("queries file must be a JSON array of strings")

    store = VectorStore()
    results = [evaluate_query(store, query, args.top_k) for query in queries]
    summary = aggregate_results(results)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_k": args.top_k,
        "summary": summary,
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Retrieval evaluation complete")
    print(f"  queries: {summary['queries']}")
    print(f"  answered: {summary['answered']}")
    print(f"  avg_hits: {summary['avg_hits']:.2f}")
    print(f"  avg_noise_hit_rate: {summary['avg_noise_hit_rate']:.3f}")
    print(f"  report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
