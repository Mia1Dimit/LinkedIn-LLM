"""
db/vector_store.py — ChromaDB interface.

Responsibilities:
  - Initialize all collections on startup
  - Embed documents via AWS Bedrock
  - Upsert with content-hash dedup (skip unchanged chunks)
  - Query with optional metadata filters
"""

import json
import time
import boto3
import chromadb
from chromadb.config import Settings
from typing import Optional
from utils.schema import DocumentChunk
from config import CHROMA_PATH, COLLECTIONS, BEDROCK_MODELS, AWS_REGION, INGEST


# ─────────────────────────────────────────────
# Bedrock embedding client
# ─────────────────────────────────────────────

class BedrockEmbedder:
    """Wraps AWS Bedrock to embed text using Titan or Cohere."""

    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        self.model_id = BEDROCK_MODELS["embedding"]
        self._is_titan = "titan" in self.model_id
        self._is_cohere = "cohere" in self.model_id
        self._rpm_delay = 60.0 / INGEST["embedding_rpm"]

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a list of floats."""
        if self._is_titan:
            body = json.dumps({"inputText": text})
        elif self._is_cohere:
            body = json.dumps({
                "texts": [text],
                "input_type": "search_document",
            })
        else:
            raise ValueError(f"Unknown embedding model: {self.model_id}")

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())

        if self._is_titan:
            return result["embedding"]
        elif self._is_cohere:
            return result["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts with rate-limit delay between calls."""
        embeddings = []
        for i, text in enumerate(texts):
            embeddings.append(self.embed(text))
            if i < len(texts) - 1:
                time.sleep(self._rpm_delay)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """
        Embed a query string. For Cohere the input_type differs from documents.
        Titan uses the same endpoint for both.
        """
        if self._is_cohere:
            body = json.dumps({
                "texts": [text],
                "input_type": "search_query",
            })
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embeddings"][0]
        else:
            return self.embed(text)


# ─────────────────────────────────────────────
# Vector store
# ─────────────────────────────────────────────

class VectorStore:
    """
    Manages all ChromaDB collections and handles upsert + query.

    Usage
    -----
        store = VectorStore()
        store.upsert(chunks)           # list[DocumentChunk]
        results = store.query(
            collection="my_network",
            query_text="Who do I know at AWS?",
            n_results=5,
        )
    """

    def __init__(self):
        self.chroma = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedder = BedrockEmbedder()
        self._collections: dict[str, chromadb.Collection] = {}
        self._init_collections()

    def _init_collections(self):
        """Create all collections if they don't exist yet."""
        for name in COLLECTIONS.values():
            self._collections[name] = self.chroma.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},   # cosine similarity
            )
        print(f"[VectorStore] Initialized {len(self._collections)} collections.")

    def _get_collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            raise ValueError(f"Unknown collection '{name}'. Valid: {list(self._collections.keys())}")
        return self._collections[name]

    # ── Upsert ────────────────────────────────

    def upsert(self, chunks: list[DocumentChunk], verbose: bool = True) -> dict:
        """
        Embed and upsert a list of DocumentChunks.

        If INGEST["skip_unchanged"] is True, chunks whose content_hash
        already exists in ChromaDB are skipped (no re-embedding cost).

        Returns a stats dict: {"inserted": N, "skipped": N, "errors": N}
        """
        stats = {"inserted": 0, "skipped": 0, "errors": 0}
        if not chunks:
            return stats

        # Group chunks by collection for batch processing
        by_collection: dict[str, list[DocumentChunk]] = {}
        for chunk in chunks:
            by_collection.setdefault(chunk.collection, []).append(chunk)

        for coll_name, coll_chunks in by_collection.items():
            collection = self._get_collection(coll_name)

            to_upsert = []
            if INGEST["skip_unchanged"]:
                # Check which chunk IDs already exist
                existing_ids = self._existing_ids(collection, [c.chunk_id for c in coll_chunks])
                existing_hashes = self._existing_hashes(collection, list(existing_ids))

                for chunk in coll_chunks:
                    if chunk.chunk_id in existing_ids:
                        stored_hash = existing_hashes.get(chunk.chunk_id)
                        if stored_hash == chunk.content_hash:
                            stats["skipped"] += 1
                            continue   # identical content — skip
                    to_upsert.append(chunk)
            else:
                to_upsert = coll_chunks

            if not to_upsert:
                continue

            # Embed and upsert in batches of 50
            batch_size = 50
            for i in range(0, len(to_upsert), batch_size):
                batch = to_upsert[i:i + batch_size]
                try:
                    texts = [c.document for c in batch]
                    embeddings = self.embedder.embed_batch(texts)
                    chroma_docs = [c.to_chroma() for c in batch]

                    collection.upsert(
                        ids=[d["id"] for d in chroma_docs],
                        documents=[d["document"] for d in chroma_docs],
                        metadatas=[d["metadata"] for d in chroma_docs],
                        embeddings=embeddings,
                    )
                    stats["inserted"] += len(batch)
                    if verbose:
                        print(f"[VectorStore] Upserted {len(batch)} chunks → '{coll_name}' "
                              f"(total so far: {stats['inserted']})")
                except Exception as e:
                    stats["errors"] += len(batch)
                    print(f"[VectorStore] ERROR upserting batch in '{coll_name}': {e}")

        return stats

    # ── Query ─────────────────────────────────

    def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,   # ChromaDB metadata filter
    ) -> list[dict]:
        """
        Semantic search within a single collection.

        Returns a list of dicts: {"document", "metadata", "distance"}
        sorted by relevance (closest first).
        """
        coll = self._get_collection(collection)
        query_embedding = self.embedder.embed_query(query_text)

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, coll.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = coll.query(**kwargs)

        # Flatten ChromaDB's nested list response
        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append({"document": doc, "metadata": meta, "distance": dist})
        return hits

    def query_all_collections(
        self,
        query_text: str,
        n_per_collection: int = 3,
        exclude: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Query all collections and merge results, sorted by distance.
        Useful for open-ended questions that span multiple data domains.
        """
        exclude = exclude or []
        all_hits = []
        for name in COLLECTIONS.values():
            if name in exclude:
                continue
            try:
                hits = self.query(name, query_text, n_results=n_per_collection)
                for hit in hits:
                    hit["collection"] = name
                all_hits.extend(hits)
            except Exception as e:
                print(f"[VectorStore] Warning: could not query '{name}': {e}")

        # Sort all hits by distance (lower = more similar)
        all_hits.sort(key=lambda x: x["distance"])
        return all_hits

    # ── Stats ─────────────────────────────────

    def stats(self) -> dict:
        """Return document count per collection."""
        return {name: self._get_collection(name).count() for name in COLLECTIONS.values()}

    # ── Internal helpers ──────────────────────

    def _existing_ids(self, collection: chromadb.Collection, ids: list[str]) -> set[str]:
        """
        Return the subset of ids that already exist in the collection.
        Batched in groups of 500 — ChromaDB's collection.get() silently
        truncates large ID lists, so we must page through them manually.
        """
        if not ids:
            return set()
        found: set[str] = set()
        for i in range(0, len(ids), 500):
            batch = ids[i:i + 500]
            try:
                result = collection.get(ids=batch, include=[])
                found.update(result["ids"])
            except Exception:
                pass
        return found

    def _existing_hashes(self, collection: chromadb.Collection, ids: list[str]) -> dict[str, str]:
        """
        Return {chunk_id: content_hash} for existing chunks.
        Batched for the same reason as _existing_ids.
        """
        if not ids:
            return {}
        hashes: dict[str, str] = {}
        for i in range(0, len(ids), 500):
            batch = ids[i:i + 500]
            try:
                result = collection.get(ids=batch, include=["metadatas"])
                for id_, meta in zip(result["ids"], result["metadatas"]):
                    hashes[id_] = meta.get("content_hash", "")
            except Exception:
                pass
        return hashes