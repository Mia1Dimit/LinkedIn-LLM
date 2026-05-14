"""
scripts/eval_rag.py — RAG evaluation framework.

Runs a curated test dataset through the RAG pipeline and grades each answer
using Claude as an LLM judge (LLM-as-a-judge pattern), adapted from the
Prompt-Eval course notebook.

Evaluation loop (per test case):
  1. ask()          → run the RAG pipeline, get an answer
  2. grade_by_model → a second LLM call judges the answer against criteria
  3. Aggregate scores by category and overall

Usage:
    python scripts/eval_rag.py
    python scripts/eval_rag.py --verbose              # print answers as they run
    python scripts/eval_rag.py --output results/eval.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import BEDROCK_MODELS, AWS_REGION, INGEST
from db.vector_store import VectorStore
from query.ask import ask, BedrockLLM

ASK_TIMEOUT_SECONDS = 120
GRADE_TIMEOUT_SECONDS = 90

# ─── Test dataset ─────────────────────────────────────────────────────────────
# Each entry: question, category, solution_criteria (list of strings).
# Categories: person_lookup | company_lookup | career | communications | groundedness
EVAL_DATASET = [
    # ── Person lookup ──────────────────────────────────────────────────────────
    {
        "question": "Who is Chan Heng Hong and where does he work?",
        "category": "person_lookup",
        "solution_criteria": [
            "Mentions Chan Heng Hong by name",
            "States their current company or employer",
            "Includes their role or professional context",
            "Does not fabricate a company or role not present in the data",
        ],
    },
    {
        "question": "Summarise Francesca Romana Tonti.",
        "category": "person_lookup",
        "solution_criteria": [
            "Mentions Francesca Romana Tonti by name",
            "Provides professional background (role, company, or industry)",
            "Answer is structured and concise",
            "Does not include invented details",
        ],
    },
    {
        "question": "Who is Adam Barbera and what does his company do?",
        "category": "person_lookup",
        "solution_criteria": [
            "Identifies Adam Barbera by name",
            "Mentions Dost or his role as founder/CEO",
            "Describes the company's focus (AI, finance, or automation)",
            "Does not fabricate funding amounts or company details not in the data",
        ],
    },
    {
        "question": "Who do I know that works in sports technology or esports?",
        "category": "person_lookup",
        "solution_criteria": [
            "Names at least one connection from the network",
            "Associates them with sports technology, esports, or a related sector",
            "People cited are plausible names (not obviously invented)",
            "Answer is professionally relevant",
        ],
    },
    # ── Company lookup ─────────────────────────────────────────────────────────
    {
        "question": "What do we know about Grasp?",
        "category": "company_lookup",
        "solution_criteria": [
            "Mentions the company Grasp",
            "Describes what the company does (product, service, or industry)",
            "Includes at least one specific detail (location, size, founding year, or specialties)",
            "Does not invent company details absent from the data",
        ],
    },
    {
        "question": "Where is Abios based and what do they do?",
        "category": "company_lookup",
        "solution_criteria": [
            "Mentions Abios by name",
            "States their location or headquarters (Stockholm or Sweden)",
            "Describes their focus (esports data, betting, or sports)",
            "Does not fabricate location or business details",
        ],
    },
    {
        "question": "What companies in my network are related to finance or investment?",
        "category": "company_lookup",
        "solution_criteria": [
            "Names at least two companies from the data",
            "Associates them with finance, investment, or capital",
            "Company names cited are plausible (not obviously invented)",
            "Does not broadly hallucinate company names or relationships",
        ],
    },
    {
        "question": "What is the industry focus and size of Dost?",
        "category": "company_lookup",
        "solution_criteria": [
            "Mentions Dost by name",
            "Describes the industry (AI, fintech, or financial automation)",
            "Mentions company size or funding if available in the data",
            "Does not fabricate financial figures not in the data",
        ],
    },
    # ── Career / profile ────────────────────────────────────────────────────────
    {
        "question": "What is my professional background and career trajectory?",
        "category": "career",
        "solution_criteria": [
            f"Refers to {INGEST['owner_name']} or contextualises their career appropriately",
            "Mentions at least one past role, company, or educational institution",
            "Provides a coherent career narrative rather than a random list",
            "Does not invent roles or companies",
        ],
    },
    {
        "question": "What skills or certifications do I have?",
        "category": "career",
        "solution_criteria": [
            "Lists at least two concrete skills or certifications",
            "Skills are relevant professional skills (not generic filler)",
            "Does not fabricate certifications or skills",
            "Answer is concise and factual",
        ],
    },
    {
        "question": "What is my educational background?",
        "category": "career",
        "solution_criteria": [
            "Mentions at least one educational institution or degree",
            "Does not fabricate educational history",
            "Includes relevant details such as field of study or graduation year if available",
            "Answer is concise and accurate",
        ],
    },
    # ── Communications ─────────────────────────────────────────────────────────
    {
        "question": "Who have I been messaging recently?",
        "category": "communications",
        "solution_criteria": [
            "Names at least one person or conversation thread from messages data",
            "Provides context about what was discussed or the nature of the interaction",
            "Does not fabricate conversation participants",
            "Answer draws from communications data, not only profile data",
        ],
    },
    # ── Groundedness / appropriate refusal ─────────────────────────────────────
    {
        "question": "What is my credit score?",
        "category": "groundedness",
        "solution_criteria": [
            "Correctly states that this information is not available in the LinkedIn data",
            "Does not invent or guess a credit score",
            "Response is polite and redirects to what IS available",
            "Does not hallucinate any financial data",
        ],
    },
    {
        "question": "What did I eat for breakfast last Tuesday?",
        "category": "groundedness",
        "solution_criteria": [
            "Correctly states that personal lifestyle data is not in the LinkedIn knowledge base",
            "Does not invent or guess breakfast details",
            "Response is appropriately brief and helpful",
            "Does not confuse LinkedIn professional data with personal life data",
        ],
    },
]

# ─── Bedrock helper ────────────────────────────────────────────────────────────

def _bedrock_converse(
    llm: BedrockLLM,
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 700,
    stop_sequences: list[str] | None = None,
) -> str:
    params: dict = {
        "modelId": llm.model_id,
        "messages": messages,
        "inferenceConfig": {
            "temperature": temperature,
            "maxTokens": max_tokens,
        },
    }
    if stop_sequences:
        params["inferenceConfig"]["stopSequences"] = stop_sequences
    if system:
        params["system"] = [{"text": system}]
    response = llm.client.converse(**params)
    return response["output"]["message"]["content"][0]["text"]


# ─── LLM judge ────────────────────────────────────────────────────────────────

def grade_by_model(llm: BedrockLLM, test_case: dict, output: str) -> dict:
    """
    LLM-as-judge: evaluate a RAG answer against the test case criteria.
    Returns a dict with strengths, weaknesses, criteria_met, reasoning, score.
    """
    n_criteria = len(test_case["solution_criteria"])
    criteria_block = "\n".join(f"- {c}" for c in test_case["solution_criteria"])

    eval_prompt = f"""You are an expert evaluator for a RAG (Retrieval-Augmented Generation) system \
built on a user's LinkedIn professional data.

Original question:
<question>
{test_case["question"]}
</question>

Category: {test_case["category"]}

RAG system answer:
<answer>
{output}
</answer>

Evaluation criteria ({n_criteria} total):
<criteria>
{criteria_block}
</criteria>

Evaluate the answer strictly against each criterion. Be rigorous:
- Penalise vague, fabricated, or irrelevant answers.
- Reward concise, grounded, specific answers that cite actual data.
- For groundedness questions, reward an honest "I don't know" over a plausible-sounding invention.

Output a JSON object with these fields in this exact order:
- "strengths": array of 1-3 key strengths (strings)
- "weaknesses": array of 1-3 areas for improvement (strings)
- "criteria_met": integer — how many of the {n_criteria} criteria are fully met
- "reasoning": 1-2 sentence explanation of your overall assessment
- "score": integer from 1 to 10

Respond with JSON only."""

    messages = [
        {"role": "user", "content": [{"text": eval_prompt}]},
        {"role": "assistant", "content": [{"text": "```json\n{"}]},
    ]

    try:
        raw = "{" + _bedrock_converse(
            llm, messages, temperature=0.1, max_tokens=600,
            stop_sequences=["```"]
        )
        return json.loads(raw.strip())
    except (json.JSONDecodeError, Exception) as exc:
        # Fallback: try regex extraction
        m = re.search(r"\{.*\}", raw if "raw" in dir() else "", re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {
            "strengths": [],
            "weaknesses": [f"Grader parse error: {exc}"],
            "criteria_met": 0,
            "reasoning": f"Grader failed: {str(exc)[:120]}",
            "score": 0,
        }


# ─── Test runner ───────────────────────────────────────────────────────────────

def run_test_case(
    store: VectorStore,
    llm: BedrockLLM,
    test_case: dict,
    verbose: bool = False,
) -> dict:
    """Run one test case: ask → grade → return result record."""
    question = test_case["question"]

    if verbose:
        print(f"\n  Q [{test_case['category']}]: {question}")

    output = ask(question, store=store, llm=llm)

    if verbose:
        preview = output[:300] + ("..." if len(output) > 300 else "")
        print(f"  A: {preview}")

    grade = grade_by_model(llm, test_case, output)
    score = int(grade.get("score", 0))

    if verbose:
        print(f"  Score: {score}/10 — {grade.get('reasoning', '')}")

    return {
        "question": question,
        "category": test_case["category"],
        "output": output,
        "score": score,
        "criteria_met": grade.get("criteria_met", 0),
        "total_criteria": len(test_case["solution_criteria"]),
        "strengths": grade.get("strengths", []),
        "weaknesses": grade.get("weaknesses", []),
        "reasoning": grade.get("reasoning", ""),
    }


def run_eval(
    dataset: list[dict],
    verbose: bool = False,
    ask_timeout_s: int = ASK_TIMEOUT_SECONDS,
    grade_timeout_s: int = GRADE_TIMEOUT_SECONDS,
) -> list[dict]:
    """Run the full evaluation pipeline over the entire dataset."""
    store = VectorStore()
    llm = BedrockLLM(read_timeout=max(ask_timeout_s, grade_timeout_s))

    results: list[dict] = []
    total = len(dataset)
    print(f"\nRunning evaluation — {total} test cases, model: {BEDROCK_MODELS['llm']}\n")

    for i, test_case in enumerate(dataset, 1):
        label = f"[{i}/{total}]"
        q_short = test_case["question"][:65] + "..." if len(test_case["question"]) > 65 else test_case["question"]
        print(f"  {label} {test_case['category']:<16} {q_short}")
        try:
            result = run_test_case(
                store,
                llm,
                test_case,
                verbose=verbose,
            )
            results.append(result)
        except Exception as exc:
            print(f"    !! ERROR: {exc}")
            results.append({
                "question": test_case["question"],
                "category": test_case["category"],
                "output": "",
                "score": 0,
                "criteria_met": 0,
                "total_criteria": len(test_case["solution_criteria"]),
                "strengths": [],
                "weaknesses": [str(exc)],
                "reasoning": f"Exception during evaluation: {exc}",
            })

        # Avoid Bedrock throttling between cases
        if i < total:
            time.sleep(0.8)

    return results


# ─── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list[dict]) -> None:
    scores = [r["score"] for r in results]
    avg_score = mean(scores) if scores else 0.0
    pass_count = sum(1 for s in scores if s >= 7)
    pass_rate = 100.0 * pass_count / len(scores) if scores else 0.0

    # Per-category averages
    by_category: dict[str, list[int]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r["score"])

    print("\n" + "=" * 65)
    print("  RAG EVALUATION REPORT")
    print("=" * 65)
    print(f"  Total test cases : {len(results)}")
    print(f"  Average score    : {avg_score:.1f} / 10")
    print(f"  Pass rate (>=7)  : {pass_rate:.0f}%  ({pass_count}/{len(results)})")
    print()
    print("  Per-category averages:")
    for cat, cat_scores in sorted(by_category.items()):
        bar = "#" * round(mean(cat_scores))
        print(f"    {cat:<20} {mean(cat_scores):4.1f}  {bar}")
    print()
    print(f"  {'#':<4} {'Pass':<5} {'Score':<8} {'Category':<20} Question")
    print("  " + "-" * 70)
    for i, r in enumerate(results, 1):
        flag = "PASS" if r["score"] >= 7 else "FAIL"
        q_short = r["question"][:42] + "..." if len(r["question"]) > 42 else r["question"]
        print(f"  {i:<4} {flag:<5} {r['score']}/10   {r['category']:<20} {q_short}")
    print("=" * 65)

    # Surface the lowest-scoring weaknesses for quick review
    worst = sorted(results, key=lambda r: r["score"])[:3]
    if worst and worst[0]["score"] < 7:
        print("\n  Lowest-scoring cases (improvement targets):")
        for r in worst:
            if r["score"] < 7:
                print(f"    [{r['score']}/10] {r['question']}")
                for w in r.get("weaknesses", []):
                    print(f"           - {w}")
    print()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RAG Evaluation — LinkedIn Career Assistant"
    )
    parser.add_argument(
        "--output", "-o",
        default="evaluation/results/eval_results.json",
        help="Path to save JSON results (default: evaluation/results/eval_results.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print each answer and grade as the eval runs",
    )
    parser.add_argument(
        "--ask-timeout",
        type=int,
        default=ASK_TIMEOUT_SECONDS,
        help=f"Timeout in seconds for each answer generation (default: {ASK_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--grade-timeout",
        type=int,
        default=GRADE_TIMEOUT_SECONDS,
        help=f"Timeout in seconds for each grading call (default: {GRADE_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Run only the first N test cases (0 = all)",
    )
    args = parser.parse_args()

    dataset = EVAL_DATASET[: args.limit] if args.limit and args.limit > 0 else EVAL_DATASET
    results = run_eval(
        dataset,
        verbose=args.verbose,
        ask_timeout_s=args.ask_timeout,
        grade_timeout_s=args.grade_timeout,
    )
    print_report(results)

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Results saved -> {output_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
