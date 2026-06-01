"""Pydantic schemas for document upload and management endpoints.

These models define the request/response contracts for the documents API.
Internal storage details (e.g., absolute file paths) are deliberately
excluded from response models to prevent information disclosure.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    """Lifecycle states of an uploaded document.

    Attributes:
        UPLOADED: File saved to disk, awaiting processing.
        PROCESSING: Document is being parsed, chunked, and embedded.
        INDEXED: Chunks are stored in the vector DB and queryable.
        FAILED: Processing failed; see logs for details.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentResponse(BaseModel):
    """Public response schema returned after a successful document upload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "research_paper.pdf",
                "file_size": 245678,
                "content_type": "application/pdf",
                "status": "uploaded",
                "uploaded_at": "2026-05-26T14:32:00Z",
            }
        }
    )

    id: UUID = Field(..., description="UUID4 assigned to the document on upload.")
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename as provided by the client.")
    file_size: int = Field(..., gt=0, description="Size of the uploaded file in bytes.")
    content_type: str = Field(..., description="MIME type of the uploaded file.")
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED, description="Current lifecycle status of the document.")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of when the upload completed.")


class DocumentChunk(BaseModel):
    """A single text chunk extracted from a document.

    Chunks are the unit of indexing and retrieval in the RAG pipeline.
    Each chunk carries enough metadata to be traced back to its source
    document and position, which is essential for citation in answers
    and for debugging retrieval quality.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "index": 0,
                "content": "This is the first chunk of the document...",
                "char_count": 1000,
            }
        }
    )

    document_id: UUID = Field(..., description="UUID of the source document this chunk was extracted from.")
    index: int = Field(..., ge=0, description="Zero-based position of this chunk within the source document.")
    content: str = Field(..., min_length=1, description="The raw text content of the chunk.")
    char_count: int = Field(..., gt=0, description="Length of the chunk content in characters.")


class ProcessedDocumentResponse(BaseModel):
    """Response returned after a document has been parsed, chunked, embedded, and persisted.

    Returned by POST /documents/{document_id}/process. Carries summary
    statistics plus the chunks themselves (without embedding vectors,
    which are too large for verbose JSON responses).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_chars": 12450,
                "chunk_count": 14,
                "persisted": True,
                "chunks": [],
            }
        }
    )

    document_id: UUID = Field(..., description="UUID of the processed document.")
    total_chars: int = Field(..., ge=0, description="Total characters of extracted text across all chunks (approximate).")
    chunk_count: int = Field(..., ge=0, description="Number of chunks produced.")
    persisted: bool = Field(default=True, description="Whether chunks were successfully written to the vector store.")
    chunks: list[DocumentChunk] = Field(..., description="Ordered list of chunks, indexed from 0. Embedding vectors omitted for response size.")


class EmbeddedChunk(BaseModel):
    """A document chunk with its embedding vector attached.

    Distinct from DocumentChunk to keep the embedding step explicit in
    type signatures. Code that operates on pre-embedding chunks takes
    DocumentChunk; code that operates on chunks ready for retrieval
    takes EmbeddedChunk.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "index": 0,
                "content": "First chunk of the document...",
                "char_count": 1000,
                "embedding": [0.123, -0.456, 0.789],
                "embedding_dimension": 384,
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            }
        }
    )

    document_id: UUID = Field(..., description="UUID of the source document.")
    index: int = Field(..., ge=0, description="Zero-based position of this chunk within the source document.")
    content: str = Field(..., min_length=1, description="The raw text content of the chunk.")
    char_count: int = Field(..., gt=0, description="Length of the chunk content in characters.")
    embedding: list[float] = Field(..., description="The dense vector representation of the chunk content.")
    embedding_dimension: int = Field(..., gt=0, description="Dimensionality of the embedding vector.")
    model_name: str = Field(..., description="HuggingFace identifier of the embedding model used.")


class StoredChunk(BaseModel):
    """A chunk as stored in (and retrieved from) the vector store.

    Differs from EmbeddedChunk in two ways:
    - Carries a stable chunk_id ("{document_id}::{index}") used as the
      ChromaDB record key, enabling idempotent upserts.
    - Does NOT carry the embedding vector. Retrieving N stored chunks
      should not return N*384 floats by default; consumers who need
      the vector can call the vector store directly.

    This is the schema returned by GET /documents/{id}/chunks.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000::0",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "index": 0,
                "content": "First chunk of the document...",
                "char_count": 1000,
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            }
        }
    )

    chunk_id: str = Field(..., min_length=1, description="Stable identifier in the form '{document_id}::{index}'. Used as the ChromaDB record key.")
    document_id: UUID = Field(..., description="UUID of the source document.")
    index: int = Field(..., ge=0, description="Zero-based position within the source document.")
    content: str = Field(..., min_length=1, description="The raw text content of the chunk.")
    char_count: int = Field(..., gt=0, description="Length of the chunk content in characters.")
    model_name: str = Field(..., description="HuggingFace identifier of the embedding model used to embed this chunk.")
