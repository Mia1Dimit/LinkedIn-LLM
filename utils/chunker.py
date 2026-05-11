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


def chunk_text(text: str, domain: str, max_tokens: int = None, overlap: int = None, metadata: dict = None) -> list[DocumentChunk]:
    """
    Convenience wrapper for ingest.py: converts raw text to DocumentChunk and chunks it.
    
    Parameters
    ----------
    text        : Raw document text
    domain      : ChromaDB collection name (e.g., 'my_profile', 'my_network')
    max_tokens  : Max chunk size in tokens (default: uses config)
    overlap     : Overlap between chunks in tokens (default: uses config)
    metadata    : Dict with 'type', 'source', 'entity_name' (required)
                  Optional: 'entity_id', 'company', 'location', 'date_from', 'date_to', 'url', 'extra'
    """
    # Validate metadata has required fields
    if not metadata or not all(k in metadata for k in ['type', 'source', 'entity_name']):
        raise ValueError(f"metadata must include: type, source, entity_name")
    
    # Generate entity_id if not provided (use hashed entity_name + source)
    entity_id = metadata.get('entity_id')
    if not entity_id:
        import hashlib
        hash_input = f"{metadata['source']}::{metadata['entity_name']}"
        entity_id = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # Create DocumentChunk from raw text
    chunk = DocumentChunk(
        document=text,
        collection=domain,
        source=metadata['source'],
        type=metadata['type'],
        entity_id=entity_id,
        entity_name=metadata['entity_name'],
        company=metadata.get('company'),
        location=metadata.get('location'),
        date_from=metadata.get('date_from'),
        date_to=metadata.get('date_to'),
        url=metadata.get('url'),
        extra=metadata.get('extra', {}),
    )
    
    # Use provided limits or defaults
    if max_tokens is None or overlap is None:
        default_max, default_overlap = _defaults_for_type(chunk.type)
        max_tokens = max_tokens or default_max
        overlap = overlap or default_overlap
    
    # Chunk and return
    return chunk_document(chunk, max_tokens=max_tokens, overlap_tokens=overlap)


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
