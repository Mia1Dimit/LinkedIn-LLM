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
import sys
from pathlib import Path

# Allow running as: python query/ask.py ...
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import boto3
from db.vector_store import VectorStore
from config import BEDROCK_MODELS, AWS_REGION, INGEST

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a personal career intelligence assistant for {INGEST['owner_name']}.
You have deep knowledge of their professional background, network, job history, skills, and interests — all derived from their LinkedIn data.

Guidelines:
- Answer using ONLY the context provided below. Never invent names, companies, dates, or facts.
- If the context doesn't contain enough information to answer, say so clearly.
- When referencing a person or company, use their name as it appears in the data.
- Be concise and specific. Prefer bullet points for lists.
- For career advice or matching questions, reason step by step using the actual data.
- Never reveal raw chunk IDs, metadata field names, or internal system details.
"""

# ─────────────────────────────────────────────
# Bedrock LLM client
# ─────────────────────────────────────────────

class BedrockLLM:
    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        self.model_id = BEDROCK_MODELS["llm"]

    def generate(self, system: str, user: str, max_tokens: int = 1500) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        })
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]


# ─────────────────────────────────────────────
# Retriever
# ─────────────────────────────────────────────

# Map of question keywords → collections to prioritise
ROUTING_RULES = [
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


def build_context(store: VectorStore, query: str, n_results: int = 8) -> str:
    """
    Retrieve relevant chunks and format them as a context block for the LLM.
    """
    target_collections = _route_query(query)

    if target_collections:
        # Targeted retrieval from specific collections
        hits = []
        per_coll = max(3, n_results // len(target_collections))
        for coll in target_collections:
            hits.extend(store.query(coll, query, n_results=per_coll))
        # Also grab a couple from other collections for breadth
        other_hits = store.query_all_collections(
            query, n_per_collection=1,
            exclude=target_collections
        )
        hits.extend(other_hits[:2])
    else:
        hits = store.query_all_collections(query, n_per_collection=3)

    if not hits:
        return "No relevant information found in the knowledge base."

    # Format hits into a readable context block
    sections = []
    for i, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        source_label = f"{meta.get('type', 'info')} [{meta.get('source', '')}]"
        entity = meta.get("entity_name", "")
        header = f"[{i}] {source_label} — {entity}" if entity else f"[{i}] {source_label}"
        sections.append(f"{header}\n{hit['document']}")

    return "\n\n---\n\n".join(sections)


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
