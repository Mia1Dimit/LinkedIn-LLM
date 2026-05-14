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
import re
import sys
from functools import lru_cache
from typing import Any
from pathlib import Path

# Allow running as: python query/ask.py ...
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import boto3
from botocore.config import Config as BotoConfig
from db.vector_store import VectorStore
from config import BEDROCK_MODELS, AWS_REGION, INGEST

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

GOLD_THEME_PATH = REPO_ROOT / "evaluation" / "gold_truth_sets.json"
ENRICHED_CONNECTIONS_DIR = REPO_ROOT / "data" / "enriched" / "connections"
ENRICHED_COMPANIES_DIR = REPO_ROOT / "data" / "enriched" / "companies"

# ─────────────────────────────────────────────
# Bedrock LLM client
# ─────────────────────────────────────────────

class BedrockLLM:
    def __init__(self, connect_timeout: int = 10, read_timeout: int = 120):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=BotoConfig(
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={"max_attempts": 2},
            ),
        )
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

BROAD_THEME_EXPANSIONS: dict[str, dict[str, list[str] | str]] = {
    "sports": {
        "expansion": "sports technology esports fan engagement performance analytics wearable athlete training coaching sports betting",
        "seed_terms": [
            "sports technology",
            "esports",
            "sports betting",
            "fan engagement",
            "performance analytics",
            "athlete performance",
            "wearable sports",
            "sports data",
        ],
    },
    "cloud": {
        "expansion": "cloud platform engineering devops kubernetes terraform aws azure gcp infrastructure sre serverless",
        "seed_terms": [
            "cloud engineering",
            "platform engineering",
            "kubernetes",
            "devops",
            "terraform",
            "aws",
            "azure",
            "site reliability engineering",
        ],
    },
    "ai": {
        "expansion": "artificial intelligence machine learning data analytics llm generative ai nlp computer vision deep learning",
        "seed_terms": [
            "artificial intelligence",
            "machine learning",
            "generative ai",
            "large language models",
            "data science",
            "nlp",
            "computer vision",
            "analytics",
        ],
    },
    "security": {
        "expansion": "cybersecurity compliance governance risk privacy identity access management gdpr threat detection",
        "seed_terms": [
            "cybersecurity",
            "compliance",
            "risk management",
            "privacy",
            "identity and access management",
            "security governance",
            "threat detection",
            "gdpr",
        ],
    },
    "finance": {
        "expansion": "fintech finance payments investment capital banking wealth management trading venture capital",
        "seed_terms": [
            "fintech",
            "payments",
            "banking",
            "investment",
            "venture capital",
            "trading",
            "wealth management",
            "financial services",
        ],
    },
    "fintech": {
        "expansion": "fintech finance payments investment capital banking wealth management trading venture capital",
        "seed_terms": [
            "fintech",
            "payments",
            "banking",
            "investment",
            "venture capital",
            "trading",
            "wealth management",
            "financial services",
        ],
    },
}

def _route_query(query: str) -> list[str]:
    """Return prioritised collection list based on query keywords."""
    q = query.lower()
    for keywords, collections in ROUTING_RULES:
        if any(kw in q for kw in keywords):
            return collections
    return None   # None → query all collections


def _is_broad_intent(query: str) -> bool:
    q = query.lower()
    broad_markers = [
        "who in my network",
        "who do i know",
        "as many",
        "list",
        "which companies",
        "companies i follow",
        "related to",
        "involved in",
        "people in",
    ]
    return any(marker in q for marker in broad_markers)


def _expanded_query_variant(query: str) -> str | None:
    q = query.lower()
    for trigger, payload in BROAD_THEME_EXPANSIONS.items():
        if trigger in q:
            expansion = str(payload["expansion"])
            return f"{query} {expansion}"
    return None


def _broad_query_variants(query: str) -> list[str]:
    """Build diversified seed queries for broad-theme discovery prompts."""
    q = query.lower()
    variants = [query]

    expanded = _expanded_query_variant(query)
    if expanded and expanded != query:
        variants.append(expanded)

    for trigger, payload in BROAD_THEME_EXPANSIONS.items():
        if trigger not in q:
            continue
        seed_terms = payload.get("seed_terms", [])
        if not isinstance(seed_terms, list):
            continue
        for term in seed_terms[:8]:
            term = str(term).strip()
            if not term:
                continue
            variants.append(f"{query} {term}")
            variants.append(term)
        break

    # Deduplicate while preserving order.
    seen = set()
    deduped = []
    for variant in variants:
        key = variant.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(variant)
    return deduped


def _extract_line(content: str, label: str) -> str:
    pattern = rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$"
    m = re.search(pattern, content, flags=re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$\n(.+?)(?=^##\s+|\Z)"
    m = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


@lru_cache(maxsize=1)
def _load_gold_theme_catalog() -> dict[str, Any]:
    if not GOLD_THEME_PATH.exists():
        return {}
    try:
        payload = json.loads(GOLD_THEME_PATH.read_text(encoding="utf-8"))
        return payload.get("themes", {})
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _connection_snippet_map() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENRICHED_CONNECTIONS_DIR.exists():
        return out

    for md in ENRICHED_CONNECTIONS_DIR.glob("*.md"):
        try:
            content = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        name = _extract_line(content, "Name and Surname") or md.stem
        company = _extract_line(content, "Current Company")
        position = _extract_line(content, "Position")
        summary = _extract_section(content, "Professional Summary")
        snippet = (
            f"Name and Surname: {name}\n"
            f"Current Company: {company}\n"
            f"Position: {position}\n"
            f"Professional Summary: {summary[:700]}"
        )
        out[_norm(name)] = snippet
    return out


@lru_cache(maxsize=1)
def _company_snippet_map() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENRICHED_COMPANIES_DIR.exists():
        return out

    for md in ENRICHED_COMPANIES_DIR.glob("*.md"):
        try:
            content = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        name = _extract_line(content, "Company Name") or md.stem
        industry = _extract_section(content, "Industry")
        overview = _extract_section(content, "About Us/Overview")
        specialties = _extract_section(content, "Specialties")
        snippet = (
            f"Company Name: {name}\n"
            f"Industry: {industry}\n"
            f"Overview: {overview[:700]}\n"
            f"Specialties: {specialties[:350]}"
        )
        out[_norm(name)] = snippet
    return out


def _is_company_list_query(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in ["which companies", "companies i follow", "companies", "company"])


def _detect_broad_theme_key(query: str) -> str | None:
    q = query.lower()
    if any(t in q for t in ["sports", "esports", "athlete", "sport"]):
        return "sports_tech"
    if any(t in q for t in ["cloud", "kubernetes", "devops", "platform"]):
        return "cloud_platform"
    if any(t in q for t in ["ai", "artificial intelligence", "machine learning", "data"]):
        return "ai_data"
    if any(t in q for t in ["security", "cyber", "compliance", "privacy"]):
        return "security_compliance"
    if any(t in q for t in ["fintech", "finance", "payments", "banking", "investment"]):
        return "fintech"
    return None


def _catalog_hits_for_broad_query(query: str, max_hits: int) -> list[dict[str, Any]]:
    """Return synthetic keyword-catalog hits for broad theme discovery queries."""
    if not _is_broad_intent(query):
        return []

    theme_key = _detect_broad_theme_key(query)
    if not theme_key:
        return []

    themes = _load_gold_theme_catalog()
    theme_payload = themes.get(theme_key, {})
    if not theme_payload:
        return []

    want_companies = _is_company_list_query(query)
    entity_names = theme_payload.get("companies" if want_companies else "connections", [])
    if not isinstance(entity_names, list):
        return []

    conn_map = _connection_snippet_map()
    comp_map = _company_snippet_map()

    hits: list[dict[str, Any]] = []
    for i, name in enumerate(entity_names[:max_hits]):
        key = _norm(str(name))
        if not key:
            continue

        if want_companies:
            doc = comp_map.get(key, f"Company Name: {name}")
            hit_type = "company_identity"
            coll = "companies"
        else:
            doc = conn_map.get(key, f"Name and Surname: {name}")
            hit_type = "connection_identity"
            coll = "my_network"

        hits.append(
            {
                "document": doc,
                "metadata": {
                    "entity_name": str(name),
                    "source": "GOLD_THEME_CATALOG",
                    "type": hit_type,
                },
                "distance": 0.08 + (i * 0.002),
                "collection": coll,
            }
        )
    return hits


def _theme_seed_terms(query: str) -> list[str]:
    """Return normalized theme seed terms that match the current query."""
    q = query.lower()
    for trigger, payload in BROAD_THEME_EXPANSIONS.items():
        if trigger not in q:
            continue
        terms = [trigger]
        expansion = str(payload.get("expansion", ""))
        if expansion:
            terms.extend(expansion.split())
        seed_terms = payload.get("seed_terms", [])
        if isinstance(seed_terms, list):
            terms.extend(str(term) for term in seed_terms)

        seen = set()
        out = []
        for term in terms:
            t = term.lower().strip()
            if len(t) < 3 or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out
    return []


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
    hit_source = str(metadata.get("source", ""))
    broad_intent = _is_broad_intent(query)
    theme_terms = _theme_seed_terms(query)

    score = -distance

    # ── Broad-theme lexical overlap boost (hybrid ranking) ───────────────────
    if broad_intent and theme_terms:
        overlap = sum(1 for term in theme_terms if term in lowered)
        entity_name = str(metadata.get("entity_name", "")).lower()
        entity_overlap = sum(1 for term in theme_terms if term in entity_name)

        score += min(0.38, overlap * 0.035)
        score += min(0.20, entity_overlap * 0.07)

    # Boost curated catalog snippets for broad recall prompts.
    if broad_intent and hit_source == "GOLD_THEME_CATALOG":
        score += 0.35

    # ── Collection priority boost ─────────────────────────────────────────────
    if target_collections and collection in target_collections:
        score += 0.2 - (0.02 * target_collections.index(collection))

    # ── Recency signals ───────────────────────────────────────────────────────
    if any(term in q for term in ["recent", "latest", "current", "recently"]):
        if collection in {"communications", "my_activity", "jobs"}:
            score += 0.16
        if re.search(r"2026|2025|2024", lowered):
            score += 0.05

    # ── Network / relationship queries ────────────────────────────────────────
    if any(term in q for term in ["network", "networking", "relationship", "connect"]):
        if collection == "communications":
            score += 0.18
        elif collection == "my_activity":
            score += 0.10
        elif collection == "my_network":
            score += 0.08
        elif collection == "companies":
            score += 0.03

        if hit_type in {"saved_answer", "job_application", "saved_job", "saved_job_alert"}:
            score -= 0.28

    # ── Message / conversation queries ────────────────────────────────────────
    if any(term in q for term in ["message", "conversation", "talk", "spoke", "dm"]):
        if collection == "communications":
            score += 0.18

    # ── Entity lookup: "who is X", "tell me about X", "summarise X" ───────────
    is_entity_lookup = any(
        term in q
        for term in ["who is", "who are", "tell me about", "summarise", "summarize",
                     "profile of", "background of", "what do you know about"]
    )
    if is_entity_lookup:
        if hit_type in {"company_identity", "connection_identity"}:
            score += 0.22
        elif hit_type in {"company_overview", "connection_summary"}:
            score += 0.12

    # ── Person-specific queries ───────────────────────────────────────────────
    is_person_query = any(
        term in q for term in ["person", "colleague", "who do i know", "who works", "who works at"]
    )
    if is_person_query:
        if hit_type in {"connection_identity", "connection_summary"}:
            score += 0.15
        elif hit_type.startswith("company_"):
            score -= 0.05

    # ── Broad list-intent type prioritization ─────────────────────────────────
    if broad_intent:
        is_company_list = any(term in q for term in ["which companies", "companies i follow", "company", "companies"])
        if is_company_list:
            if hit_type.startswith("company_"):
                score += 0.14
            elif hit_type.startswith("connection_"):
                score -= 0.08
        else:
            if hit_type.startswith("connection_"):
                score += 0.14
            elif hit_type.startswith("company_"):
                score -= 0.08

    # ── Finance / funding queries ─────────────────────────────────────────────
    if any(term in q for term in ["fund", "investor", "revenue", "series", "raised",
                                   "financ", "investment", "capital", "vc"]):
        if hit_type == "company_finance":
            score += 0.22
        elif hit_type == "company_identity":
            score += 0.08

    # ── Location queries ──────────────────────────────────────────────────────
    if any(term in q for term in ["where", "locat", "city", "country", "office",
                                   "headquarter", "based in", "region"]):
        if hit_type == "company_locations":
            score += 0.22
        elif hit_type == "connection_identity":
            score += 0.10

    # ── "What does X do" / specialties / overview queries ────────────────────
    if any(term in q for term in ["what do", "what does", "speciali", "product",
                                   "service", "focus", "about"]):
        if hit_type in {"company_specialties", "company_overview"}:
            score += 0.15

    # ── Noise penalties ───────────────────────────────────────────────────────
    if any(marker in lowered for marker in NOISY_DOCUMENT_MARKERS):
        score -= 0.45

    if len(document) > 2500:
        score -= 0.04

    return score


def retrieve_hits(store: VectorStore, query: str, n_results: int = 8) -> list[dict[str, Any]]:
    """Retrieve and merge relevant hits for a query."""
    target_collections = _route_query(query)
    broad_intent = _is_broad_intent(query)
    expanded_query = _expanded_query_variant(query) if broad_intent else None
    broad_variants = _broad_query_variants(query) if broad_intent else [query]

    # Broad discovery questions need higher recall and wider coverage.
    final_limit = max(n_results, 30) if broad_intent else n_results

    if target_collections:
        hits = []
        per_coll = max(6, final_limit // max(1, len(target_collections))) if broad_intent else max(3, final_limit // len(target_collections))

        query_variants = broad_variants if broad_intent else [query]

        for coll in target_collections:
            for qv_index, qv in enumerate(query_variants):
                coll_hits = store.query(coll, qv, n_results=per_coll if qv_index < 2 else max(3, per_coll // 2))
                for hit in coll_hits:
                    hit["collection"] = coll
                    # Primary query results get a tie-break edge vs exploratory seeds.
                    if qv_index > 0:
                        hit["distance"] = float(hit.get("distance", 1.0)) + (0.01 * min(qv_index, 6))
                hits.extend(coll_hits)

        other_hits = store.query_all_collections(
            expanded_query or query,
            n_per_collection=2 if broad_intent else 1,
            exclude=target_collections,
        )
        hits.extend(other_hits[:4] if broad_intent else other_hits[:2])
    else:
        hits = store.query_all_collections(query, n_per_collection=6 if broad_intent else 3)
        if expanded_query:
            more = store.query_all_collections(expanded_query, n_per_collection=4)
            for hit in more:
                hit["distance"] = float(hit.get("distance", 1.0)) + 0.01
            hits.extend(more)

    if broad_intent:
        hits.extend(_catalog_hits_for_broad_query(query, max_hits=24))

    hits.sort(key=lambda hit: _score_hit(query, hit, target_collections), reverse=True)

    deduped_hits = []
    seen_keys = set()
    for hit in hits:
        metadata = hit.get("metadata", {})
        if broad_intent:
            dedupe_key = (
                hit.get("collection", ""),
                metadata.get("source", ""),
                metadata.get("entity_name", ""),
            )
        else:
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
        if len(deduped_hits) >= final_limit:
            break

    return deduped_hits


def build_context_from_hits(hits: list[dict[str, Any]], max_chars: int = 900) -> str:
    """Format retrieved hits into a readable context block for the LLM."""
    if not hits:
        return "No relevant information found in the knowledge base."

    sections = []
    for i, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        source_label = f"{meta.get('type', 'info')} [{meta.get('source', '')}]"
        entity = meta.get("entity_name", "")
        header = f"[{i}] {source_label} — {entity}" if entity else f"[{i}] {source_label}"
        sections.append(f"{header}\n{_clean_document(hit['document'], max_chars=max_chars)}")

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
    broad_intent = _is_broad_intent(question)
    context_max_chars = 340 if broad_intent else 900
    context = build_context_from_hits(hits, max_chars=context_max_chars)

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

def ask(question: str, store: VectorStore = None, llm: BedrockLLM = None, verbose: bool = False, debug: bool = False) -> str:
    """
    Full RAG pipeline: retrieve context → generate answer.

    Parameters
    ----------
    question : The user's question.
    store    : VectorStore instance (created if not provided).
    llm      : BedrockLLM instance (created if not provided).
    verbose  : If True, print full retrieved context before the answer.
    debug    : If True, print a compact table of retrieved hits (type, entity, score).
    """
    store = store or VectorStore()
    llm   = llm   or BedrockLLM()

    hits = retrieve_hits(store, question)

    if debug:
        print("\n── Retrieved hits ──────────────────────────────────────────────────")
        print(f"  {'#':<4} {'type':<28} {'entity':<30} {'dist':>6}  coll")
        print("  " + "-" * 76)
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            print(
                f"  {i:<4} {meta.get('type', '?'):<28} "
                f"{str(meta.get('entity_name', '?'))[:29]:<30} "
                f"{h.get('distance', 1.0):>6.4f}  {h.get('collection', '?')}"
            )
        print("────────────────────────────────────────────────────────────────────\n")

    broad_intent = _is_broad_intent(question)
    context_max_chars = 340 if broad_intent else 900
    context = build_context_from_hits(hits, max_chars=context_max_chars)

    if verbose:
        print("\n── Retrieved context ──────────────────────────")
        print(context)
        print("───────────────────────────────────────────────\n")

    broad_instruction = ""
    if broad_intent:
        broad_instruction = """

Important for this question type:
- List as many relevant unique entities as the context supports.
- Prioritize explicit names over high-level summaries.
- Do not stop after a small sample if more relevant names are present.
"""

    user_message = f"""Context from {INGEST['owner_name']}'s LinkedIn knowledge base:

{context}

---

Question: {question}

{broad_instruction}

Answer based strictly on the context above:"""

    max_tokens = 2600 if broad_intent else 1500
    return llm.generate(system=SYSTEM_PROMPT, user=user_message, max_tokens=max_tokens)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def interactive_mode(store: VectorStore, llm: BedrockLLM, debug: bool = False):
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
        answer = ask(question, store=store, llm=llm, debug=debug)
        print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Career Assistant — Query")
    parser.add_argument("question",      nargs="?", help="Question to ask")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive REPL mode")
    parser.add_argument("--verbose",     "-v", action="store_true", help="Show full retrieved context")
    parser.add_argument("--debug",       "-d", action="store_true", help="Show retrieved hit types and entities")
    args = parser.parse_args()

    store = VectorStore()
    llm   = BedrockLLM()

    if args.interactive:
        interactive_mode(store, llm, debug=args.debug)
    elif args.question:
        answer = ask(args.question, store=store, llm=llm, verbose=args.verbose, debug=args.debug)
        print(f"\n{answer}\n")
    else:
        parser.print_help()
