# Retrieval Evaluation Suite

The retrieval evaluation harness runs retrieval-only checks without LLM generation.

## Query Set

- File: `evaluation/queries_retrieval.json`
- Size: 20 real use-case queries (networking, profile, jobs, counts, summaries)

## Runner

- Script: `evaluation/run_retrieval_eval.py`

## Run

```bash
python evaluation/run_retrieval_eval.py
```

Optional flags:

```bash
python evaluation/run_retrieval_eval.py --top-k 10 --output evaluation/reports/retrieval_eval_custom.json
```

## Output Metrics

1. `avg_hits`: average retrieved hits per query.
2. `avg_distance`: average semantic distance for retrieved hits.
3. `avg_noise_hit_rate`: fraction of hits containing known boilerplate markers.
4. `collection_coverage`: total retrieved hits by collection.
5. `source_coverage`: total retrieved hits by source.

## Usage

Use this report to compare retrieval quality before and after parser/chunker/query changes.

Suggested acceptance checks:

1. `avg_noise_hit_rate` should trend down.
2. `collection_coverage` should match query intent distribution.
3. Count-style queries should be moved to deterministic stats path over time.
