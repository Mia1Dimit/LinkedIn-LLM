"""FastAPI wrapper around the RAG query layer for the web client."""

from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db.vector_store import VectorStore
from query.ask import BedrockLLM, SYSTEM_PROMPT, build_chat_response, prepare_chat_request


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    question: str
    answer: str
    owner_name: str
    sources: list[dict]


def _format_sse(event_name: str, payload) -> str:
    if not isinstance(payload, str):
        payload = json.dumps(payload)

    lines = payload.replace("\r", "").split("\n")
    rendered = [f"event: {event_name}\n"]
    rendered.extend(f"data: {line}\n" for line in lines)
    rendered.append("\n")
    return "".join(rendered)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = VectorStore()
    app.state.llm = BedrockLLM()
    yield


app = FastAPI(title="LinkedIn Career Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> dict:
    store = app.state.store
    return {
        "status": "ok",
        "collections": store.stats(),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    payload = build_chat_response(
        message,
        store=app.state.store,
        llm=app.state.llm,
    )
    return ChatResponse(**payload)


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    prepared = prepare_chat_request(
        message,
        store=app.state.store,
    )

    def event_stream():
        answer_parts: list[str] = []
        yield _format_sse(
            "meta",
            {
                "question": prepared["question"],
                "owner_name": prepared["owner_name"],
                "sources": prepared["sources"],
            },
        )

        try:
            for chunk in app.state.llm.generate_stream(
                system=SYSTEM_PROMPT,
                user=prepared["user_message"],
            ):
                answer_parts.append(chunk)
                yield _format_sse("token", chunk)

            yield _format_sse(
                "done",
                {
                    "question": prepared["question"],
                    "answer": "".join(answer_parts),
                    "owner_name": prepared["owner_name"],
                    "sources": prepared["sources"],
                },
            )
        except Exception as exc:
            yield _format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
