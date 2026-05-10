from fastapi import FastAPI

# Create the FastAPI application instance
app = FastAPI(
    title="RAG Chatbot Platform",
    description="Master's Thesis Project — Yassine Elkesraoui, ISLA Gaia",
    version="0.1.0"
)

# First endpoint: root
@app.get("/")
def read_root():
    return {
        "message": "Hello from Yassine's RAG API",
        "status": "running",
        "version": "0.1.0"
    }

# Second endpoint: health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}
