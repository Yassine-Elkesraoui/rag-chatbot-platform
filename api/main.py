"""
Entry point of the RAG Chatbot API.

This module is intentionally minimal. Its only responsibilities are:
    1. Create the FastAPI application instance with metadata
    2. Register all routers (chat, future routes for documents, admin, etc.)
    3. Define a root endpoint and a health check endpoint

Business logic lives in dedicated modules under api/routes/.
Data schemas live under api/models/.
Utility functions (logging, config) live under api/utils/.

This separation of concerns keeps the codebase scalable and maintainable.
"""

from fastapi import FastAPI

from api.routes import chat
from api.utils.logger import logger


# Create the FastAPI application instance with descriptive metadata.
# This metadata appears automatically in the Swagger UI at /docs.
app = FastAPI(
    title="RAG Chatbot Platform",
    description="Master's Thesis Project — Mohamed Yassine El kesraoui, ISLA Gaia",
    version="0.3.0"
)


# Register the chat router. All endpoints defined in api/routes/chat.py
# are now exposed under the main application.
app.include_router(chat.router)


# Log the application startup. This message appears in the console
# every time Uvicorn starts or reloads the server.
logger.info("RAG Chatbot API initialized — version 0.3.0")


@app.get("/", tags=["General"])
def read_root() -> dict:
    """
    Root endpoint of the API.

    Returns a welcome message and basic metadata about the running service.
    Useful as a quick sanity check that the server is reachable.

    Returns:
        A dictionary containing the welcome message, status, and version.
    """
    return {
        "message": "Welcome to the RAG Chatbot API",
        "status": "running",
        "version": "0.3.0"
    }


@app.get("/health", tags=["General"])
def health_check() -> dict:
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint is intentionally lightweight (no database calls,
    no external services) so it can be called frequently without
    impacting performance. It is the standard pattern used by
    Kubernetes, Docker, and cloud platforms to verify a service is alive.

    Returns:
        A dictionary indicating the service is healthy.
    """
    return {"status": "healthy"}