"""
Chat endpoint for the RAG Chatbot API.

This module defines all routes related to the chat functionality.
For now, it contains a single POST /chat endpoint that returns
a placeholder response. Later, this endpoint will be connected
to the real RAG pipeline (LangChain + ChromaDB + OpenAI).

Architecture note:
    This module uses FastAPI's APIRouter to keep chat-related logic
    isolated from the main application file. The router is registered
    in api/main.py via app.include_router().
"""

from fastapi import APIRouter

from api.models.schemas import ChatRequest, ChatResponse
from api.utils.logger import logger


# Create a router instance specific to this module.
# The 'tags' parameter groups all endpoints from this router under "Chat"
# in the Swagger UI, making the documentation cleaner.
router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Handle a chat request and return an answer.

    For now, the answer is a hardcoded placeholder. In future iterations,
    this function will:
        1. Convert the question into an embedding vector
        2. Retrieve relevant document chunks from ChromaDB
        3. Build a prompt with the retrieved context
        4. Call the LLM (OpenAI) to generate a grounded answer
        5. Return the final answer with source citations

    Args:
        request: A ChatRequest object containing the user's question.
                 Validated automatically by FastAPI/Pydantic.

    Returns:
        A ChatResponse object containing the original question,
        the generated answer, and a status flag.

    Raises:
        422 Unprocessable Entity: Automatically raised by FastAPI
            if the request body doesn't match the ChatRequest schema.
    """
    # Log the incoming question for traceability.
    # In production, this helps debug user-reported issues.
    logger.info(f"Received chat request: '{request.question}'")

    # Placeholder logic — to be replaced by the real RAG pipeline
    fake_answer = (
        f"You asked: '{request.question}'. "
        f"The real AI is coming soon!"
    )

    # Log the generated answer for audit purposes
    logger.info(f"Generated answer: '{fake_answer}'")

    # Build and return the structured response.
    # Returning a Pydantic object (rather than a plain dict) ensures
    # the response is validated against the ChatResponse schema.
    return ChatResponse(
        question=request.question,
        answer=fake_answer,
        status="success"
    )