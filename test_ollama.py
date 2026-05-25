"""
test_ollama.py — Day 7 verification script

This script verifies that the Python `ollama` library can successfully
communicate with the locally running Ollama server, and that Phi-3 Mini
returns a meaningful response.

This file is for ONE-TIME validation only. It will be deleted at the
end of Day 7. The proper service module (`ollama_service.py`) will be
built on Day 8 with full type hints, error handling, and integration
into the FastAPI /chat endpoint.

Usage:
    python test_ollama.py
"""

import ollama


def test_phi3_mini() -> None:
    """
    Send a single prompt to Phi-3 Mini and print its response.
    
    Returns:
        None. Prints output directly to the terminal.
    
    Raises:
        ConnectionError: If Ollama background service is not running.
    """
    # Define the user prompt — keep it short for first verification
    user_question: str = "Explain what FastAPI is in 2 sentences."

    print("=" * 60)
    print("Sending test prompt to Phi-3 Mini via Ollama...")
    print(f"Prompt: {user_question}")
    print("=" * 60)

    # Call Ollama's chat API
    # `messages` follows the OpenAI-compatible format that Ollama supports
    response: dict = ollama.chat(
        model="phi3",
        messages=[
            {
                "role": "user",
                "content": user_question
            }
        ]
    )

    # The response dict contains "message" → "content" with the model's reply
    ai_reply: str = response["message"]["content"]

    print("\nPhi-3 Mini Response:")
    print("-" * 60)
    print(ai_reply)
    print("-" * 60)
    print("\n✅ Test successful — Ollama + Python integration is working!")


if __name__ == "__main__":
    test_phi3_mini()