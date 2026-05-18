from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator, Iterable

import boto3
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import AWS_REGION, BEDROCK_MODELS
from enrichment.common import resolve_tavily_api_key
from query.ask import SYSTEM_PROMPT


REPO_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DB_PATH = REPO_ROOT / "data" / "chat_memory.db"
TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    model_id: str | None = None
    use_web_search: bool = False
    n_results: int = 8


class TavilySource(BaseModel):
    title: str
    url: str
    snippet: str


@dataclass
class ModelOption:
    id: str
    label: str


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at)"
            )

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), session_id, role, content, datetime.now(UTC).isoformat()),
            )

    def recent(self, session_id: str, limit: int = 16) -> list[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        rows = list(reversed(rows))
        return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]

    def clear(self, session_id: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            return cur.rowcount


class BedrockChat:
    def __init__(self, region_name: str):
        self.region_name = region_name

    def generate(
        self,
        model_id: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> str:
        return _safe_generate_text(
            region_name=self.region_name,
            model_id=model_id,
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def stream(
        self,
        model_id: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        # NOTE: converse_stream currently crashes this process on some Windows environments
        # with access violation (0xC0000005). We keep streaming UX by chunking a stable
        # converse() response into small deltas.
        full_text = self.generate(
            model_id=model_id,
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        chunk_size = 28
        for idx in range(0, len(full_text), chunk_size):
            yield full_text[idx : idx + chunk_size]


def _model_options() -> list[ModelOption]:
    defaults = [
        ModelOption(id=BEDROCK_MODELS["llm"], label="Claude Haiku 4.5 (default)"),
        ModelOption(id="eu.anthropic.claude-sonnet-4-20250514-v1:0", label="Claude Sonnet 4"),
        ModelOption(id="eu.anthropic.claude-3-7-sonnet-20250219-v1:0", label="Claude 3.7 Sonnet"),
    ]

    seen: set[str] = set()
    unique: list[ModelOption] = []
    for item in defaults:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return unique


def _tavily_search(query: str, max_results: int = 5) -> list[TavilySource]:
    api_key = resolve_tavily_api_key()
    if not api_key:
        return []

    try:
        response = requests.post(
            TAVILY_SEARCH_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "search_depth": "basic",
                "include_answer": "advanced",
                "include_raw_content": False,
                "max_results": max_results,
                "topic": "general",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    sources: list[TavilySource] = []
    for item in payload.get("results", []):
        sources.append(
            TavilySource(
                title=str(item.get("title", "Untitled")),
                url=str(item.get("url", "")),
                snippet=str(item.get("content", "")).strip(),
            )
        )
    return sources


def _build_bedrock_messages(
    memory_messages: Iterable[ChatMessage],
    rag_user_message: str,
    web_sources: list[TavilySource],
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    for msg in memory_messages:
        messages.append(
            {
                "role": msg.role,
                "content": [{"text": msg.content}],
            }
        )

    if web_sources:
        web_block = "\n\n".join(
            [
                f"- {source.title}\n  URL: {source.url}\n  Snippet: {source.snippet[:500]}"
                for source in web_sources
            ]
        )
        rag_user_message = (
            f"{rag_user_message}\n\n---\n\n"
            "Additional web context (use only if relevant and do not fabricate beyond these snippets):\n"
            f"{web_block}"
        )

    messages.append(
        {
            "role": "user",
            "content": [{"text": rag_user_message}],
        }
    )
    return messages


def _build_retrieval_query(memory_messages: list[ChatMessage], question: str) -> str:
    """Build a retrieval query that carries short-term conversational context.

    This helps follow-up questions like "Was the call planned?" stay anchored to
    the previously discussed person/entity.
    """
    recent_user_turns = [m.content.strip() for m in memory_messages if m.role == "user" and m.content.strip()]
    if not recent_user_turns:
        return question

    prior = recent_user_turns[-2:]
    context_block = "\n".join(f"- {item}" for item in prior)
    return (
        f"Conversation context (previous user questions):\n{context_block}\n\n"
        f"Current user question:\n{question}"
    )


def _build_grounded_user_message(owner_name: str, context: str, question: str) -> str:
    return f"""Context from {owner_name}'s LinkedIn knowledge base:

{context}

---

Question: {question}

Answer based strictly on the context above:"""


def _ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _safe_prepare_chat_request(question: str, n_results: int) -> dict[str, Any]:
    """Prepare retrieval context in a subprocess so native crashes are isolated.

    Some local Windows setups can hard-crash (access violation) when Chroma/embedding
    paths run inside the API process. Running retrieval in a child process keeps the API alive.
    """
    code = (
        "import json; "
        "from query.ask import prepare_chat_request; "
        f"result=prepare_chat_request({question!r}, n_results={n_results}); "
        "print(json.dumps(result, ensure_ascii=True))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or f"return code {completed.returncode}"
        raise RuntimeError(f"retrieval subprocess failed: {detail}")

    raw = (completed.stdout or "").strip()
    if not raw:
        raise RuntimeError("retrieval subprocess returned no output")

    lines = [line for line in raw.splitlines() if line.strip()]
    json_line = lines[-1] if lines else raw
    return json.loads(json_line)


def _safe_generate_text(
    region_name: str,
    model_id: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> str:
    """Generate text in a subprocess so native Bedrock crashes don't kill the API process."""
    payload = {
        "region_name": region_name,
        "model_id": model_id,
        "system_prompt": system_prompt,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    code = (
        "import json,sys,boto3; "
        "p=json.loads(sys.stdin.read()); "
        "client=boto3.client('bedrock-runtime', region_name=p['region_name']); "
        "params={'modelId': p['model_id'], 'messages': p['messages'], "
        "'inferenceConfig': {'maxTokens': p['max_tokens'], 'temperature': p['temperature']}}; "
        "sys_prompt=p.get('system_prompt',''); "
        "params.update({'system':[{'text': sys_prompt}]}) if sys_prompt else None; "
        "resp=client.converse(**params); "
        "content=resp['output']['message'].get('content', []); "
        "text=''.join([b.get('text','') for b in content if 'text' in b]); "
        "print(json.dumps({'text': text}, ensure_ascii=True))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        input=json.dumps(payload, ensure_ascii=True),
        text=True,
        capture_output=True,
        timeout=180,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or f"return code {completed.returncode}"
        raise RuntimeError(f"generation subprocess failed: {detail}")

    raw = (completed.stdout or "").strip()
    if not raw:
        raise RuntimeError("generation subprocess returned no output")

    lines = [line for line in raw.splitlines() if line.strip()]
    json_line = lines[-1] if lines else raw
    return json.loads(json_line).get("text", "")


memory_store = MemoryStore(MEMORY_DB_PATH)
chat_client = BedrockChat(AWS_REGION)
model_options = _model_options()

app = FastAPI(title="LinkedIn LLM Chat API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/models")
def models() -> dict[str, Any]:
    return {
        "models": [{"id": m.id, "label": m.label} for m in model_options],
        "default": BEDROCK_MODELS["llm"],
    }


@app.get("/api/memory/{session_id}")
def memory(session_id: str) -> dict[str, Any]:
    messages = memory_store.recent(session_id=session_id, limit=100)
    return {"messages": [m.model_dump() for m in messages]}


@app.delete("/api/memory/{session_id}")
def clear_memory(session_id: str) -> dict[str, Any]:
    deleted = memory_store.clear(session_id=session_id)
    return {"deleted": deleted}


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    selected_model = payload.model_id.strip() if payload.model_id else BEDROCK_MODELS["llm"]

    try:
        memory_messages = memory_store.recent(payload.session_id, limit=16)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build chat message context: {exc}") from exc

    retrieval_query = _build_retrieval_query(memory_messages, payload.message)
    try:
        prepared = _safe_prepare_chat_request(retrieval_query, n_results=max(1, min(payload.n_results, 30)))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}") from exc

    owner_name = prepared.get("owner_name", "Dimitris")
    context = prepared.get("context", "No relevant information found in the knowledge base.")
    grounded_user_message = _build_grounded_user_message(owner_name, context, payload.message)

    web_sources = _tavily_search(payload.message, max_results=5) if payload.use_web_search else []
    try:
        bedrock_messages = _build_bedrock_messages(memory_messages, grounded_user_message, web_sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare model messages: {exc}") from exc

    def event_stream() -> Generator[str, None, None]:
        yield _ndjson_line(
            {
                "type": "meta",
                "sources": prepared["sources"],
                "web_sources": [w.model_dump() for w in web_sources],
                "model_id": selected_model,
            }
        )

        assistant_chunks: list[str] = []
        try:
            for token in chat_client.stream(
                model_id=selected_model,
                system_prompt=SYSTEM_PROMPT,
                messages=bedrock_messages,
            ):
                assistant_chunks.append(token)
                yield _ndjson_line({"type": "delta", "text": token})
                # Pacing makes streaming visibly progressive in the frontend.
                time.sleep(0.015)

            assistant_text = "".join(assistant_chunks).strip()
            memory_store.append(payload.session_id, "user", payload.message)
            memory_store.append(payload.session_id, "assistant", assistant_text)
            yield _ndjson_line({"type": "done"})
        except Exception as exc:
            yield _ndjson_line({"type": "error", "message": f"Streaming failed: {exc}"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.chat_server:app", host="127.0.0.1", port=8000, reload=True)
