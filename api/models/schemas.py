"""
Pydantic models for the RAG Chatbot API.

All data shapes (request bodies, response bodies) are defined here.
Centralizing schemas makes them easy to find and reuse across endpoints.
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Data shape for incoming chat requests."""
    question: str


class ChatResponse(BaseModel):
    """Data shape for outgoing chat responses."""
    question: str
    answer: str
    status: str