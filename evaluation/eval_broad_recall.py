"""Broad-intent recall evaluation using strict gold truth sets.

This script measures whether broad discovery questions retrieve enough entities.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db.vector_store import VectorStore
from query.ask import ask, BedrockLLM
from evaluation.rebuild_gold_truth_sets_strict import rebuild


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _mentions(answer: str, expected_names: list[str]) -> list[str]:
    lowered = _normalize(answer)
    matched: list[str] = []
    for name in expected_names:
        if not name:
            continue
        token = re.escape(_normalize(name))
        if re.search(rf"\b{token}\b", lowered):
            matched.append(name)
    return matched


def _score_from_recall(ratio: float) -> float:
    return round(min(10.0, ratio * 10.0), 2)


def _build_broad_cases(truth: dict, max_themes: int = 5, expected_per_theme: int = 15) -> list[dict]:
    themes = []
    for key, item in truth.get("themes", {}).items():
        themes.append((key, item))
    themes.sort(key=lambda kv: kv[1].get("connection_count", 0), reverse=True)

    cases: list[dict] = []
    for key, item in themes[:max_themes]:
        expected_conn = item.get("connections", [])[:expected_per_theme]
        expected_comp = item.get("companies", [])[:expected_per_theme]
        label = item.get("label", key)

        if expected_conn:
            cases.append(
                {
                    "id": f"{key}_connections",
                    "category": "broad_recall",
                    "kind": "connections",
                    "theme": key,
                    "label": label,
                    "question": f"Who in my network works in {label}? List as many people as possible.",
                    "expected_names": expected_conn,
                }
            )

        if expected_comp:
            cases.append(
                {
                    "id": f"{key}_companies",
                    "category": "broad_recall",
                    "kind": "companies",
                    "theme": key,
                    "label": label,
                    "question": f"Which companies I follow are related to {label}? List as many as possible.",
                    "expected_names": expected_comp,
                }
            )

    return cases


def run_broad_eval(
    cases: list[dict],
    verbose: bool = False,
) -> dict:
    store = VectorStore()
    llm = BedrockLLM(read_timeout=120)

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']} -> {case['question']}")
        answer = ask(case["question"], store=store, llm=llm)
        matched = _mentions(answer, case["expected_names"])
        expected_n = len(case["expected_names"])
        recall = (len(matched) / expected_n) if expected_n else 0.0
        score = _score_from_recall(recall)

        if verbose:
            print(f"  matched {len(matched)}/{expected_n} ({recall:.1%})")

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "kind": case["kind"],
                "theme": case["theme"],
                "label": case["label"],
                "question": case["question"],
                "score": score,
                "recall_ratio": round(recall, 4),
                "expected_count": expected_n,
                "matched_count": len(matched),
                "matched_names": matched,
                "answer": answer,
            }
        )

    avg_score = round(sum(r["score"] for r in results) / len(results), 2) if results else 0.0
    avg_recall = round(sum(r["recall_ratio"] for r in results) / len(results), 4) if results else 0.0

    print("\nBroad recall summary")
    print(f"  cases: {len(results)}")
    print(f"  avg score (0-10): {avg_score}")
    print(f"  avg recall ratio: {avg_recall:.1%}")

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "avg_score": avg_score,
        "avg_recall_ratio": avg_recall,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate broad-intent recall using strict gold truth sets")
    parser.add_argument("--output", default="evaluation/results/broad_eval_results.json")
    parser.add_argument("--truth", default="evaluation/gold_truth_sets.json")
    parser.add_argument("--max-themes", type=int, default=5)
    parser.add_argument("--expected-per-theme", type=int, default=15)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    truth_path = REPO_ROOT / args.truth
    if truth_path.exists():
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
    else:
        truth = rebuild(top_n=15)
        truth_path.parent.mkdir(parents=True, exist_ok=True)
        truth_path.write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")

    cases = _build_broad_cases(
        truth,
        max_themes=args.max_themes,
        expected_per_theme=args.expected_per_theme,
    )
    report = run_broad_eval(cases, verbose=args.verbose)

    out = REPO_ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Results saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
