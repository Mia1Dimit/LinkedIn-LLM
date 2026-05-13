"""
query/ask.py — RAG query layer.

Retrieves relevant chunks from ChromaDB, assembles context,
and calls Bedrock Claude to generate a grounded answer.

Usage:
    python query/ask.py "Who do I know at AWS?"
    python query/ask.py "Summarise my career trajectory"
    python query/ask.py "What companies in my network are hiring?"
    python query/ask.py --interactive    # REPL mode
"""

import argparse
import json
import os
import re
import sys
import logging
from typing import Any
from pathlib import Path

# Allow running as: python query/ask.py ...
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import boto3
from db.vector_store import VectorStore
from config import BEDROCK_MODELS, AWS_REGION, INGEST

logger = logging.getLogger("query.ask")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a personal career intelligence assistant for {INGEST['owner_name']}.
You have deep knowledge of their professional background, network, messages, job history, and activity, all derived from their LinkedIn data.

Guidelines:
- Answer using ONLY the provided context. Never invent names, companies, dates, roles, or relationships.
- If the evidence is thin, say so explicitly and keep the claim narrow.
- Prioritize recent, dated, interaction-heavy evidence over evergreen profile or enrichment content.
- For networking or activity summaries, focus on recent conversations, invitations, reactions, follows, and changes in momentum.
- Prefer concise, high-signal summaries. Use short bullets when it improves readability.
- Ignore noisy boilerplate from scraped pages such as sign-in prompts, "people also viewed", or generic page chrome.
- Never reveal raw chunk IDs, metadata field names, internal collection names, or implementation details.
"""

NOISY_DOCUMENT_MARKERS = [
    "people also viewed",
    "view post activity",
    "sign in to continue",
    "user agreement",
    "privacy policy",
    "cookie policy",
    "join now",
    "new to linkedin",
    "by clicking continue",
]

OBSERVABILITY_ENABLED = os.getenv("QUERY_OBSERVABILITY", "0") == "1"


INTENT_PLANS = {
    "count_metrics": {
        "collections": ["companies", "my_network", "communications", "jobs", "my_activity", "my_profile"],
        "allowed_sources": {"COMPANY_FOLLOWS", "COMPANY_FOLLOWS_TAVILY", "CONNECTIONS", "CONNECTIONS_TAVILY", "INBOX"},
        "blocked_types": {"saved_answer"},
        "n_results": 6,
    },
    "network_summary": {
        "collections": ["communications", "my_activity", "my_network", "companies"],
        "allowed_sources": {"INBOX", "CONNECTIONS_TAVILY", "COMPANY_FOLLOWS_TAVILY", "CONNECTIONS", "COMPANY_FOLLOWS"},
        "blocked_types": {"saved_answer", "job_application", "saved_job", "saved_job_alert"},
        "n_results": 10,
    },
    "messaging": {
        "collections": ["communications", "my_activity", "my_network"],
        "allowed_sources": {"INBOX", "CONNECTIONS_TAVILY"},
        "blocked_types": {"saved_job", "saved_job_alert"},
        "n_results": 10,
    },
    "career_profile": {
        "collections": ["my_profile", "jobs", "my_activity"],
        "allowed_sources": {"PROFILE", "POSITIONS", "EDUCATION", "SKILLS", "CERTIFICATIONS", "LANGUAGES", "PUBLICATIONS", "JOB_APPLICATIONS", "SAVED_JOBS"},
        "blocked_types": set(),
        "n_results": 8,
    },
    "general": {
        "collections": None,
        "allowed_sources": None,
        "blocked_types": set(),
        "n_results": 8,
    },
}

# ─────────────────────────────────────────────
# Bedrock LLM client
# ─────────────────────────────────────────────

class BedrockLLM:
    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        self.model_id = BEDROCK_MODELS["llm"]

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        params = {
            "modelId": self.model_id,
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.2,
            },
        }
        if system:
            params["system"] = [{"text": system}]

        response = self.client.converse(**params)
        content = response["output"]["message"].get("content", [])
        return "".join(block.get("text", "") for block in content if "text" in block)

    def generate_stream(self, system: str, user: str, max_tokens: int = 1500):
        params = {
            "modelId": self.model_id,
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.2,
            },
        }
        if system:
            params["system"] = [{"text": system}]

        response = self.client.converse_stream(**params)
        for event in response["stream"]:
            if "contentBlockDelta" not in event:
                continue
            delta = event["contentBlockDelta"].get("delta", {})
            text = delta.get("text")
            if text:
                yield text


# ─────────────────────────────────────────────
# Retriever
# ─────────────────────────────────────────────

# Map of question keywords → collections to prioritise
ROUTING_RULES = [
    (["networking activity", "recent networking", "networking", "relationship activity"], ["communications", "my_activity", "my_network", "companies"]),
    (["recent messages", "recent conversations", "recent activity", "latest activity"], ["communications", "my_activity", "my_network"]),
    (["who", "connection", "know", "network", "person", "people"],    ["my_network"]),
    (["company", "compan", "follow", "startup", "firm"],               ["companies"]),
    (["job", "role", "appl", "position", "opportunit", "career"],      ["jobs", "my_profile"]),
    (["message", "conversation", "talk", "spoke", "dm"],               ["communications"]),
    (["skill", "experience", "background", "education", "cert"],       ["my_profile"]),
    (["like", "post", "share", "activity"],                            ["my_activity"]),
]

def _route_query(query: str) -> list[str]:
    """Return prioritised collection list based on query keywords."""
    q = query.lower()
    for keywords, collections in ROUTING_RULES:
        if any(kw in q for kw in keywords):
            return collections
    return None   # None → query all collections


def _classify_intent(query: str) -> str:
    q = query.lower()
    if any(token in q for token in ["how many", "count", "number of", "total"]):
        return "count_metrics"
    if any(token in q for token in ["networking", "relationship", "network summary", "network activity"]):
        return "network_summary"
    if any(token in q for token in ["message", "conversation", "inbox", "dm", "talked", "spoke"]):
        return "messaging"
    if any(token in q for token in ["career", "trajectory", "skills", "experience", "education", "profile"]):
        return "career_profile"
    return "general"


def _clean_document(document: str, max_chars: int = 900) -> str:
    lines = []
    for raw_line in document.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if any(marker in lowered for marker in NOISY_DOCUMENT_MARKERS):
            continue
        if line in lines:
            continue
        lines.append(line)
        if len(lines) >= 16:
            break

    cleaned = "\n".join(lines) if lines else document.strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:") + "..."
    return cleaned


def _score_hit(query: str, hit: dict[str, Any], target_collections: list[str] | None) -> float:
    q = query.lower()
    document = hit.get("document", "")
    lowered = document.lower()
    distance = float(hit.get("distance", 1.0))
    collection = hit.get("collection", "")
    metadata = hit.get("metadata", {})
    hit_type = metadata.get("type", "")

    score = -distance

    if target_collections and collection in target_collections:
        score += 0.2 - (0.02 * target_collections.index(collection))

    if any(term in q for term in ["recent", "latest", "current", "recently"]):
        if collection in {"communications", "my_activity", "jobs"}:
            score += 0.16
        if re.search(r"2026|2025|2024", lowered):
            score += 0.05

    if any(term in q for term in ["network", "networking", "relationship", "connect"]):
        if collection == "communications":
            score += 0.18
        elif collection == "my_activity":
            score += 0.1
        elif collection == "my_network":
            score += 0.08
        elif collection == "companies":
            score += 0.03

        if hit_type in {"saved_answer", "job_application", "saved_job", "saved_job_alert"}:
            score -= 0.28

    if any(term in q for term in ["message", "conversation", "talk", "spoke", "dm"]):
        if collection == "communications":
            score += 0.18

    if any(marker in lowered for marker in NOISY_DOCUMENT_MARKERS):
        score -= 0.45

    if len(document) > 2500:
        score -= 0.04

    return score


def _apply_intent_filters(hits: list[dict[str, Any]], intent: str) -> list[dict[str, Any]]:
    plan = INTENT_PLANS.get(intent, INTENT_PLANS["general"])
    allowed_sources = plan.get("allowed_sources")
    blocked_types = plan.get("blocked_types", set())

    filtered_hits = []
    for hit in hits:
        metadata = hit.get("metadata", {})
        source = metadata.get("source", "")
        hit_type = metadata.get("type", "")

        if allowed_sources and source not in allowed_sources:
            continue
        if hit_type in blocked_types:
            continue
        filtered_hits.append(hit)
    return filtered_hits


def _rerank_hits(query: str, hits: list[dict[str, Any]], target_collections: list[str] | None, intent: str) -> list[dict[str, Any]]:
    reranked = sorted(hits, key=lambda hit: _score_hit(query, hit, target_collections), reverse=True)

    # Late-boost recency in messaging/network summaries.
    if intent in {"network_summary", "messaging"}:
        reranked.sort(
            key=lambda hit: (
                bool(re.search(r"2026|2025", hit.get("document", ""))),
                _score_hit(query, hit, target_collections),
            ),
            reverse=True,
        )
    return reranked


def retrieve_hits(store: VectorStore, query: str, n_results: int = 8) -> list[dict[str, Any]]:
    """Retrieve and merge relevant hits for a query."""
    intent = _classify_intent(query)
    plan = INTENT_PLANS.get(intent, INTENT_PLANS["general"])
    target_collections = plan["collections"] or _route_query(query)
    n_results = max(n_results, int(plan.get("n_results", n_results)))

    if target_collections:
        hits = []
        per_coll = max(3, n_results // len(target_collections))
        for coll in target_collections:
            coll_hits = store.query(coll, query, n_results=per_coll)
            for hit in coll_hits:
                hit["collection"] = coll
            hits.extend(coll_hits)

        other_hits = store.query_all_collections(
            query,
            n_per_collection=1,
            exclude=target_collections,
        )
        hits.extend(other_hits[:2])
    else:
        hits = store.query_all_collections(query, n_per_collection=3)

    hits = _apply_intent_filters(hits, intent)
    hits = _rerank_hits(query, hits, target_collections, intent)

    if OBSERVABILITY_ENABLED:
        top_sources = [
            f"{h.get('collection', '?')}:{h.get('metadata', {}).get('source', '?')}:{h.get('metadata', {}).get('type', '?')}"
            for h in hits[:6]
        ]
        logger.info(
            "query='%s' intent=%s target=%s candidates=%d top=%s",
            query,
            intent,
            target_collections,
            len(hits),
            " | ".join(top_sources),
        )

    deduped_hits = []
    seen_keys = set()
    for hit in hits:
        metadata = hit.get("metadata", {})
        dedupe_key = (
            hit.get("collection", ""),
            metadata.get("source", ""),
            metadata.get("entity_name", ""),
            metadata.get("type", ""),
        )
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        deduped_hits.append(hit)
        if len(deduped_hits) >= n_results:
            break

    return deduped_hits


def build_context_from_hits(hits: list[dict[str, Any]]) -> str:
    """Format retrieved hits into a readable context block for the LLM."""
    if not hits:
        return "No relevant information found in the knowledge base."

    sections = []
    for i, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        source_label = f"{meta.get('type', 'info')} [{meta.get('source', '')}]"
        entity = meta.get("entity_name", "")
        header = f"[{i}] {source_label} — {entity}" if entity else f"[{i}] {source_label}"
        sections.append(f"{header}\n{_clean_document(hit['document'])}")

    return "\n\n---\n\n".join(sections)


def build_context(store: VectorStore, query: str, n_results: int = 8) -> str:
    """
    Retrieve relevant chunks and format them as a context block for the LLM.
    """
    return build_context_from_hits(retrieve_hits(store, query, n_results=n_results))


def build_chat_response(
    question: str,
    store: VectorStore | None = None,
    llm: BedrockLLM | None = None,
    n_results: int = 8,
) -> dict[str, Any]:
    """Return answer plus structured source snippets for UI clients."""
    prepared = prepare_chat_request(question, store=store, n_results=n_results)
    llm = llm or BedrockLLM()

    answer = llm.generate(system=SYSTEM_PROMPT, user=prepared["user_message"])
    return {
        "question": question,
        "answer": answer,
        "sources": prepared["sources"],
        "owner_name": INGEST["owner_name"],
    }


def prepare_chat_request(
    question: str,
    store: VectorStore | None = None,
    n_results: int = 8,
) -> dict[str, Any]:
    """Prepare context and sources for synchronous or streaming chat responses."""
    store = store or VectorStore()

    hits = retrieve_hits(store, question, n_results=n_results)
    context = build_context_from_hits(hits)

    user_message = f"""Context from {INGEST['owner_name']}'s LinkedIn knowledge base:

{context}

---

Question: {question}

Answer based strictly on the context above:"""

    sources = []
    for index, hit in enumerate(hits, 1):
        metadata = hit.get("metadata", {})
        sources.append({
            "rank": index,
            "collection": hit.get("collection", metadata.get("collection", "")),
            "entity_name": metadata.get("entity_name", ""),
            "source": metadata.get("source", ""),
            "type": metadata.get("type", "info"),
            "distance": hit.get("distance"),
            "snippet": _clean_document(hit.get("document", ""), max_chars=260),
        })

    return {
        "question": question,
        "sources": sources,
        "owner_name": INGEST["owner_name"],
        "context": context,
        "user_message": user_message,
    }


# ─────────────────────────────────────────────
# Main ask function
# ─────────────────────────────────────────────

def ask(question: str, store: VectorStore = None, llm: BedrockLLM = None, verbose: bool = False) -> str:
    """
    Full RAG pipeline: retrieve context → generate answer.

    Parameters
    ----------
    question : The user's question.
    store    : VectorStore instance (created if not provided).
    llm      : BedrockLLM instance (created if not provided).
    verbose  : If True, print retrieved context before the answer.
    """
    store = store or VectorStore()
    llm   = llm   or BedrockLLM()

    context = build_context(store, question)

    if verbose:
        print("\n── Retrieved context ──────────────────────────")
        print(context)
        print("───────────────────────────────────────────────\n")

    user_message = f"""Context from {INGEST['owner_name']}'s LinkedIn knowledge base:

{context}

---

Question: {question}

Answer based strictly on the context above:"""

    return llm.generate(system=SYSTEM_PROMPT, user=user_message)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def interactive_mode(store: VectorStore, llm: BedrockLLM):
    print(f"\nLinkedIn Career Assistant — Interactive Mode")
    print("Type your question, or 'quit' to exit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break
        answer = ask(question, store=store, llm=llm)
        print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Career Assistant — Query")
    parser.add_argument("question",     nargs="?", help="Question to ask")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive REPL mode")
    parser.add_argument("--verbose",    "-v", action="store_true", help="Show retrieved context")
    args = parser.parse_args()

    store = VectorStore()
    llm   = BedrockLLM()

    if args.interactive:
        interactive_mode(store, llm)
    elif args.question:
        answer = ask(args.question, store=store, llm=llm, verbose=args.verbose)
        print(f"\n{answer}\n")
    else:
        parser.print_help()
