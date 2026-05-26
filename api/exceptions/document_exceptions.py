"""Custom exceptions for document upload and management.

Following the same pattern as ollama_exceptions: domain-specific
exceptions that the route layer translates into appropriate HTTP
status codes. This keeps business logic decoupled from HTTP concerns.
"""


class DocumentError(Exception):
    """Base exception for all document-related errors.

    Catching this in route handlers catches every document failure mode
    at once, while still allowing specific subclasses to be caught first
    for more granular HTTP responses.
    """


class DocumentValidationError(DocumentError):
    """Raised when an uploaded file fails validation.

    Examples:
        - Unsupported extension (e.g., .exe, .docx)
        - File exceeds maximum size
        - Empty file (zero bytes)
        - Filename contains illegal characters

    Maps to HTTP 422 Unprocessable Entity in the route layer.
    """


class DocumentStorageError(DocumentError):
    """Raised when persisting an uploaded file to disk fails.

    Examples:
        - Disk full / write permission denied
        - Upload directory missing or corrupted
        - I/O error during streaming write

    Maps to HTTP 500 Internal Server Error in the route layer.
    Unlike validation errors, this is a server-side failure the
    client cannot fix by changing their request.
    """