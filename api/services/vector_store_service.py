"""Vector store service backed by ChromaDB.

Owns the lifecycle of the vector store: collection creation/access,
chunk persistence, retrieval by document, deletion, and existence
checks. All ChromaDB-specific details (HNSW configuration, metadata
schema, ID format) are encapsulated here.

Design notes:
    - PersistentClient: ChromaDB writes to local SQLite + index files
      under settings.chroma_persist_dir. Data survives restarts.
    - One collection, document_id as metadata: querying across the
      whole corpus is a single call; per-document operations use a
      `where` filter. Avoids the N-collections-N-lookups antipattern.
    - Cosine space, explicit: our embeddings are L2-normalized
      (Day 11), so cosine similarity = dot product. ChromaDB's default
      is L2 (Euclidean), which would silently give wrong rankings.
      The collection is created with hnsw:space=cosine.
    - Upsert, not add: re-processing a document overwrites existing
      chunks at the same chunk_id. Idempotent at the storage layer.
    - Stable IDs: chunk_id is f"{document_id}::{index}". Deterministic
      and human-readable for debugging.
    - Telemetry disabled: ChromaDB phones home by default; we turn
      that off in the client settings. Not appropriate for academic
      research where reproducibility and data sovereignty matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaClientSettings

from api.exceptions.document_exceptions import ChromaDBError
from api.models.document_schemas import EmbeddedChunk, StoredChunk
from api.utils.config import Settings, get_settings
from api.utils.logger import logger


def _make_chunk_id(document_id: UUID, index: int) -> str:
    """Build the stable storage key for a chunk.

    Format: "{document_id}::{index}". Deterministic, human-readable,
    and unique within the collection. The same (document_id, index)
    pair always produces the same key, which is what makes upserts
    idempotent.
    """
    return f"{document_id}::{index}"


class VectorStoreService:
    """Persists and retrieves embedded chunks via ChromaDB."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the client and ensure the collection exists.

        Args:
            settings: Application configuration. Reads chroma_persist_dir,
                chroma_collection_name, and embedding_dimension (for
                metadata consistency).

        Raises:
            ChromaDBError: If the persist directory cannot be created
                or the ChromaDB client/collection fails to initialize.
        """
        self._persist_dir: Path = Path(settings.chroma_persist_dir)
        self._collection_name: str = settings.chroma_collection_name
        self._dimension: int = settings.embedding_dimension

        try:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ChromaDBError(
                f"Cannot create ChromaDB persist directory "
                f"{self._persist_dir!s}: {exc}"
            ) from exc

        try:
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=ChromaClientSettings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Failed to initialize ChromaDB PersistentClient at "
                f"{self._persist_dir!s}: {exc}"
            ) from exc

        try:
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_dimension": self._dimension,
                },
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Failed to get or create collection "
                f"{self._collection_name!r}: {exc}"
            ) from exc

        logger.info(
            "VectorStoreService ready: persist_dir=%s, collection=%s, dim=%d",
            self._persist_dir,
            self._collection_name,
            self._dimension,
        )

    # ------------------------------------------------------------------ #
    # Write path
    # ------------------------------------------------------------------ #

    def upsert_chunks(self, chunks: Sequence[EmbeddedChunk]) -> int:
        """Persist embedded chunks, overwriting any existing entries.

        Each chunk is keyed by f"{document_id}::{index}", so calling
        this twice for the same document replaces the prior chunks
        rather than duplicating them.

        Args:
            chunks: Non-empty sequence of chunks ready for storage.

        Returns:
            The number of chunks upserted.

        Raises:
            ChromaDBError: If the input is empty, embedding dimensions
                are inconsistent, or the underlying ChromaDB call fails.
        """
        if not chunks:
            raise ChromaDBError(
                "upsert_chunks called with empty input. The pipeline "
                "should never produce zero chunks for a non-empty document."
            )

        # Defensive: catch dimension drift before ChromaDB does.
        # If an EmbeddedChunk with the wrong dimension reaches storage,
        # the bug is somewhere upstream and we want the loud failure here.
        for chunk in chunks:
            if len(chunk.embedding) != self._dimension:
                raise ChromaDBError(
                    f"Chunk embedding dimension {len(chunk.embedding)} does "
                    f"not match collection dimension {self._dimension}. "
                    f"Document id={chunk.document_id}, index={chunk.index}."
                )

        ids = [_make_chunk_id(c.document_id, c.index) for c in chunks]
        embeddings = [c.embedding for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": str(c.document_id),
                "index": c.index,
                "char_count": c.char_count,
                "model_name": c.model_name,
            }
            for c in chunks
        ]

        try:
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Upsert of {len(chunks)} chunks failed: {exc}"
            ) from exc

        document_id = chunks[0].document_id
        logger.info(
            "Upserted %d chunks for document id=%s",
            len(chunks),
            document_id,
        )
        return len(chunks)

    # ------------------------------------------------------------------ #
    # Read path
    # ------------------------------------------------------------------ #

    def get_chunks_for_document(self, document_id: UUID) -> list[StoredChunk]:
        """Return all chunks stored for a given document, in index order.

        Args:
            document_id: UUID of the source document.

        Returns:
            A list of StoredChunk objects sorted by index ascending.
            Empty list if the document has no chunks stored.

        Raises:
            ChromaDBError: If the underlying query fails.
        """
        try:
            result = self._collection.get(
                where={"document_id": str(document_id)},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Query for document id={document_id} failed: {exc}"
            ) from exc

        ids: list[str] = result.get("ids") or []
        documents: list[str] = result.get("documents") or []
        metadatas: list[dict] = result.get("metadatas") or []

        chunks = [
            StoredChunk(
                chunk_id=cid,
                document_id=UUID(meta["document_id"]),
                index=int(meta["index"]),
                content=doc,
                char_count=int(meta["char_count"]),
                model_name=str(meta["model_name"]),
            )
            for cid, doc, meta in zip(ids, documents, metadatas)
        ]

        # ChromaDB does not guarantee ordering on `get()`. Sort by index
        # so callers receive chunks in their original document order.
        chunks.sort(key=lambda c: c.index)
        return chunks

    def document_exists(self, document_id: UUID) -> bool:
        """Check whether any chunks are stored for a document.

        Cheaper than get_chunks_for_document when the caller only needs
        a yes/no answer (e.g., for a 404 vs 200 routing decision).
        """
        try:
            result = self._collection.get(
                where={"document_id": str(document_id)},
                limit=1,
                include=[],
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Existence check for document id={document_id} failed: {exc}"
            ) from exc

        return bool(result.get("ids"))

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def delete_document(self, document_id: UUID) -> int:
        """Remove all chunks belonging to a document.

        Returns:
            The number of chunks deleted (best-effort; ChromaDB does
            not report a count, so this is the count observed before
            deletion).

        Raises:
            ChromaDBError: If the deletion fails.
        """
        try:
            before = self._collection.get(
                where={"document_id": str(document_id)},
                include=[],
            )
            count = len(before.get("ids") or [])

            if count == 0:
                return 0

            self._collection.delete(
                where={"document_id": str(document_id)},
            )
        except Exception as exc:
            raise ChromaDBError(
                f"Deletion for document id={document_id} failed: {exc}"
            ) from exc

        logger.info(
            "Deleted %d chunks for document id=%s",
            count,
            document_id,
        )
        return count

    @property
    def collection_name(self) -> str:
        """The name of the ChromaDB collection backing this service."""
        return self._collection_name

    @property
    def total_chunks(self) -> int:
        """Total number of chunks across all documents in the collection.

        Useful for diagnostics and dashboards. Not called per-request.
        """
        return self._collection.count()


# ---------------------------------------------------------------------- #
# Dependency-injection provider
# ---------------------------------------------------------------------- #

_vector_store_singleton: VectorStoreService | None = None


def get_vector_store_service() -> VectorStoreService:
    """Return the process-wide singleton VectorStoreService.

    Lazily constructed on first call. Use via FastAPI's Depends()
    in route handlers (Step 6+).
    """
    global _vector_store_singleton
    if _vector_store_singleton is None:
        _vector_store_singleton = VectorStoreService(get_settings())
    return _vector_store_singleton
