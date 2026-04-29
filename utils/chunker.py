"""
utils/chunker.py — Splits long text into overlapping chunks.

Uses a simple word-based splitter (no tiktoken dependency) that approximates
token count at ~0.75 words per token. This is accurate enough for chunking
purposes without requiring an external tokenizer.
"""

from utils.schema import DocumentChunk, clone_with_chunk
from config import CHUNK


def _approx_tokens(text: str) -> int:
    """Approximate token count: words / 0.75."""
    return int(len(text.split()) / 0.75)


def _split_text(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """
    Split text into chunks of at most max_tokens (approximate),
    with overlap_tokens of context carried forward between chunks.

    Returns a list of text strings. If the text fits in one chunk,
    returns a single-element list.
    """
    words = text.split()
    if not words:
        return []

    # Convert token budgets to approximate word counts
    max_words = int(max_tokens * 0.75)
    overlap_words = int(overlap_tokens * 0.75)

    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = end - overlap_words   # step back by overlap for context continuity

    return chunks


def chunk_document(chunk: DocumentChunk, max_tokens: int = None, overlap_tokens: int = None) -> list[DocumentChunk]:
    """
    Split a DocumentChunk into multiple chunks if its document text
    exceeds the token budget.

    If the document fits within max_tokens, returns the original chunk
    unchanged (as a single-element list).

    Parameters
    ----------
    chunk         : The source DocumentChunk.
    max_tokens    : Override config value. If None, uses config defaults
                    based on chunk type.
    overlap_tokens: Override config value.
    """
    if max_tokens is None:
        max_tokens, overlap_tokens = _defaults_for_type(chunk.type)

    pieces = _split_text(chunk.document, max_tokens, overlap_tokens)

    if len(pieces) == 1:
        # No split needed — just ensure chunk_index is 0
        chunk.chunk_index = 0
        return [chunk]

    return [clone_with_chunk(chunk, text, i) for i, text in enumerate(pieces)]


def chunk_all(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """
    Run chunk_document over a list of DocumentChunks.
    Returns a flat list of all resulting chunks.
    """
    result = []
    for c in chunks:
        result.extend(chunk_document(c))
    return result


def _defaults_for_type(doc_type: str) -> tuple[int, int]:
    """Return (max_tokens, overlap_tokens) for a given document type."""
    message_types = {"message_thread"}
    tavily_types  = {"company_profile", "company_post", "connection_profile"}

    if doc_type in message_types:
        return CHUNK["messages_max_tokens"], CHUNK["messages_overlap"]
    elif doc_type in tavily_types:
        return CHUNK["tavily_max_tokens"], CHUNK["tavily_overlap"]
    else:
        return CHUNK["profile_max_tokens"], CHUNK["profile_overlap"]
