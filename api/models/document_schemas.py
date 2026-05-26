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
    """Public response schema returned after a successful document upload.

    Note:
        The internal storage path is intentionally NOT exposed.
        Clients reference documents by their ``id`` only.
    """

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

    id: UUID = Field(
        ...,
        description="UUID4 assigned to the document on upload.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename as provided by the client.",
    )
    file_size: int = Field(
        ...,
        gt=0,
        description="Size of the uploaded file in bytes.",
    )
    content_type: str = Field(
        ...,
        description="MIME type of the uploaded file.",
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.UPLOADED,
        description="Current lifecycle status of the document.",
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the upload completed.",
    )