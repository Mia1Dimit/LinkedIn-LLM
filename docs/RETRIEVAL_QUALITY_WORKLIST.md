# Retrieval Quality Worklist

This worklist tracks quality improvements for retrieval relevance and signal-to-noise ratio.

## Implemented

1. Tavily markdown pre-cleaning before chunking.
2. Chunk quality gates before embedding/upsert.
3. Ingestion-time deduplication of semantically identical chunks.
4. Intent-aware retrieval plans.
5. Source/type filtering per intent.
6. Reranking stage after first-pass retrieval.
7. Query observability via optional retrieval traces.
8. Tuned chunk policy per content type.
9. Retrieval evaluation suite with 20 real-world queries.

## Remaining / Next

1. Add deterministic metrics path for count-style questions (exact stats, no LLM estimation).
2. Introduce lightweight lexical reranker (hybrid semantic + lexical).
3. Add recency-aware metadata features (`last_message_at`, `last_interaction_at`).
4. Add nightly eval pipeline and quality trend dashboard.
5. Add hard-fail quality guardrails before ingesting low-signal snapshots.
