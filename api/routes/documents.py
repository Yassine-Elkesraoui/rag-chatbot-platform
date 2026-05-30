"""HTTP routes for document upload and management.

This module is the HTTP boundary for the documents domain. It owns:
  - Translating multipart/form-data into a service-layer call
  - Mapping domain exceptions to HTTP status codes
  - Declaring the response contract via Pydantic

It does NOT own:
  - File validation rules (lives in DocumentService)
  - Storage strategy (lives in DocumentService)
  - Business invariants (lives in DocumentService)

Keeping this separation means we can later add a CLI uploader, a
batch importer, or a worker queue consumer — all reusing
DocumentService — without duplicating logic.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.exceptions.document_exceptions import (
    DocumentNotFoundError,
    DocumentParsingError,
    DocumentStorageError,
    DocumentValidationError,
)
from api.models.document_schemas import DocumentResponse, ProcessedDocumentResponse
from api.services.chunking_service import ChunkingService, get_chunking_service
from api.services.document_service import DocumentService, get_document_service
from api.services.parsing_service import ParsingService, get_parsing_service
from api.utils.logger import logger


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for indexing",
    responses={
        201: {"description": "Document uploaded and saved to disk."},
        422: {"description": "File failed validation (type, size, or empty)."},
        500: {"description": "Storage failure on the server."},
    },
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="The document to upload. Allowed: .pdf, .txt, .md. Max 10 MB.",
    ),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Upload and persist a document.

    The document is validated, assigned a UUID, and stored on local disk
    under the configured upload directory. The response contains the
    UUID needed to reference the document in subsequent API calls.

    Note:
        This endpoint only stores the file. Parsing, chunking, and
        embedding into the vector database happen in later pipeline
        stages.
    """
    try:
        return await service.save_upload(file)
    except DocumentValidationError as exc:
        logger.warning("Document validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DocumentStorageError as exc:
        logger.error("Document storage failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the uploaded file. Please try again.",
        ) from exc


@router.post(
    "/{document_id}/process",
    response_model=ProcessedDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse and chunk an uploaded document",
    responses={
        200: {"description": "Document parsed and chunked successfully."},
        404: {"description": "No document found with the given UUID."},
        422: {"description": "Document content could not be parsed."},
    },
)
async def process_document(
    document_id: UUID,
    parsing_service: ParsingService = Depends(get_parsing_service),
    chunking_service: ChunkingService = Depends(get_chunking_service),
) -> ProcessedDocumentResponse:
    """Parse a previously uploaded document and split it into chunks.

    This endpoint orchestrates the two stages of document preparation:
      1. Resolve the file on disk by UUID and extract its text content.
      2. Split the text into overlapping chunks for embedding.

    The endpoint is idempotent: calling it twice for the same document
    produces the same chunks (modulo configuration changes). No state
    is persisted yet — chunks are returned in the response only.
    Day 12 will add ChromaDB persistence.

    Args:
        document_id: UUID of a previously uploaded document.

    Returns:
        ProcessedDocumentResponse with the chunks plus summary stats.

    Raises:
        HTTPException: 404 if the document UUID is unknown.
        HTTPException: 422 if the document content cannot be parsed.
    """
    try:
        text = parsing_service.parse(document_id)
        chunks = chunking_service.chunk(document_id, text)
    except DocumentNotFoundError as exc:
        logger.warning("Document not found: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentParsingError as exc:
        logger.warning("Document parsing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    total_chars = sum(c.char_count for c in chunks)
    return ProcessedDocumentResponse(
        document_id=document_id,
        total_chars=total_chars,
        chunk_count=len(chunks),
        chunks=chunks,
    ) 