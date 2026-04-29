"""
utils/schema.py — Unified document schema for all ChromaDB ingestion.

Every chunk entering ChromaDB goes through DocumentChunk, regardless of
whether it came from a CSV, a Tavily MD file, or the Portability API.
This guarantees consistent metadata across all collections.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ─────────────────────────────────────────────
# Valid controlled vocabulary values
# ─────────────────────────────────────────────

VALID_SOURCES = {
    "csv",              # LinkedIn ZIP export
    "tavily_extract",   # Tavily Extract API (companies)
    "tavily_search",    # Tavily Search API (connections)
    "snapshot_api",     # LinkedIn Member Data Portability Snapshot API
    "changelog_api",    # LinkedIn Member Data Portability Changelog API
}

VALID_TYPES = {
    # Own profile
    "profile_bio",
    "position",
    "education",
    "skill",
    "certification",
    "language",
    "publication",
    # Network
    "connection_profile",
    "company_profile",
    "company_post",
    # Activity
    "job_application",
    "job_application_answer",
    "saved_job",
    "saved_job_alert",
    "saved_answer",
    "like",
    # Communications
    "message_thread",
    # Invitation
    "invitation",
}

VALID_COLLECTIONS = {
    "my_profile",
    "my_activity",
    "my_network",
    "companies",
    "communications",
    "jobs",
}


# ─────────────────────────────────────────────
# Core schema
# ─────────────────────────────────────────────

@dataclass
class DocumentChunk:
    """
    A single chunk ready for embedding and upsert into ChromaDB.

    Fields
    ------
    document    : The text that will be embedded. Keep it self-contained —
                  the LLM only sees this text during retrieval.
    collection  : Which ChromaDB collection this belongs to.
    source      : Where the raw data came from.
    type        : The semantic type of this chunk.
    entity_id   : Stable identifier for the parent entity (e.g. LinkedIn URL,
                  company slug). Used to group chunks and build the dedup key.
    entity_name : Human-readable name (for logging and display).

    Optional metadata
    -----------------
    company     : Relevant company name (for connections, positions, jobs).
    location    : Geographic location string.
    date_from   : Start date of the record (ISO string YYYY-MM or YYYY).
    date_to     : End date of the record. "Present" if ongoing.
    url         : Source URL if available.
    extra       : Dict for any additional metadata specific to the type.
    """

    # Required
    document:       str
    collection:     str
    source:         str
    type:           str
    entity_id:      str
    entity_name:    str

    # Optional
    company:        Optional[str] = None
    location:       Optional[str] = None
    date_from:      Optional[str] = None
    date_to:        Optional[str] = None
    url:            Optional[str] = None
    extra:          dict = field(default_factory=dict)

    # Auto-populated — do not pass manually
    chunk_index:    int = 0         # set by chunker when splitting long text
    date_ingested:  str = field(default_factory=lambda: date.today().isoformat())
    content_hash:   str = field(default="")
    chunk_id:       str = field(default="")

    def __post_init__(self):
        # Validate controlled vocabulary
        if self.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{self.source}'. Must be one of {VALID_SOURCES}")
        if self.type not in VALID_TYPES:
            raise ValueError(f"Invalid type '{self.type}'. Must be one of {VALID_TYPES}")
        if self.collection not in VALID_COLLECTIONS:
            raise ValueError(f"Invalid collection '{self.collection}'. Must be one of {VALID_COLLECTIONS}")

        # Derive content hash from document text
        self.content_hash = _hash(self.document)

        # Derive deterministic chunk ID — stable across re-runs
        # Format: {source}::{entity_id}::chunk_{chunk_index}
        self.chunk_id = _make_id(self.source, self.entity_id, self.chunk_index)

    def to_chroma(self) -> dict:
        """
        Serialize to the dict format ChromaDB expects for upsert.
        Returns {"id", "document", "metadata"} — embedding is added separately.
        """
        metadata = {
            "source":       self.source,
            "collection":   self.collection,
            "type":         self.type,
            "entity_id":    self.entity_id,
            "entity_name":  self.entity_name,
            "date_ingested": self.date_ingested,
            "content_hash": self.content_hash,
            "chunk_index":  self.chunk_index,
        }
        # Only include optional fields if they have a value (keeps metadata lean)
        if self.company:    metadata["company"]   = self.company
        if self.location:   metadata["location"]  = self.location
        if self.date_from:  metadata["date_from"] = self.date_from
        if self.date_to:    metadata["date_to"]   = self.date_to
        if self.url:        metadata["url"]        = self.url

        # Flatten extra dict into metadata (prefix with x_ to avoid collisions)
        for k, v in self.extra.items():
            if v is not None:
                metadata[f"x_{k}"] = str(v)

        return {
            "id":       self.chunk_id,
            "document": self.document,
            "metadata": metadata,
        }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _hash(text: str) -> str:
    """SHA-256 of the document text, hex-encoded, first 16 chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _make_id(source: str, entity_id: str, chunk_index: int) -> str:
    """
    Build a stable, deterministic chunk ID.
    Colons inside entity_id are replaced with pipes to avoid confusion.
    """
    safe_entity = entity_id.replace(":", "|").replace("/", "-")
    return f"{source}::{safe_entity}::chunk_{chunk_index}"


def clone_with_chunk(chunk: DocumentChunk, text: str, index: int) -> DocumentChunk:
    """
    Return a new DocumentChunk for a split piece of a longer document.
    Copies all metadata from the parent chunk, updates text + index.
    Used by the chunker.
    """
    return DocumentChunk(
        document=text,
        collection=chunk.collection,
        source=chunk.source,
        type=chunk.type,
        entity_id=chunk.entity_id,
        entity_name=chunk.entity_name,
        company=chunk.company,
        location=chunk.location,
        date_from=chunk.date_from,
        date_to=chunk.date_to,
        url=chunk.url,
        extra=chunk.extra,
        chunk_index=index,
    )
