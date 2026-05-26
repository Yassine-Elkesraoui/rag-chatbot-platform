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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.exceptions.document_exceptions import (
    DocumentStorageError,
    DocumentValidationError,
)
from api.models.document_schemas import DocumentResponse
from api.services.document_service import DocumentService, get_document_service
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
        stages (Days 10–14).
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