from fastapi import FastAPI
from pydantic import BaseModel

# Create the FastAPI application instance
app = FastAPI(
    title="RAG Chatbot Platform",
    description="Master's Thesis Project — Yassine Elkesraoui, ISLA Gaia",
    version="0.2.0"
)

# ----------------------------
# Pydantic models (data schemas)
# ----------------------------

class ChatRequest(BaseModel):
    """What the client must send to /chat"""
    question: str

class ChatResponse(BaseModel):
    """What the server returns from /chat"""
    question: str
    answer: str
    status: str

# ----------------------------
# Endpoints
# ----------------------------

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the RAG Chatbot API",
        "status": "running",
        "version": "0.2.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Receives a user question and returns a (fake) answer.
    The real RAG pipeline will be plugged in here later.
    """
    # For now, we return a hardcoded fake response
    fake_answer = f"You asked: '{request.question}'. Real AI coming soon!"

    return ChatResponse(
        question=request.question,
        answer=fake_answer,
        status="success"
    )