import os
import uuid
import random
import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Application metadata and tags for OpenAPI docs
app = FastAPI(
    title="Human Mimicry Chatbot API",
    description=(
        "Backend AI service that mimics human behavior based on provided information "
        "and generates realistic human-like chatbot responses. "
        "Provides REST API endpoints for conversation management and chatting."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Chat", "description": "Send and receive human-like chat messages."},
        {"name": "Health", "description": "Health check and meta endpoints."},
    ],
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit this to the frontend host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Data Models
# ========================

class Message(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Sender role: 'user' or 'bot'")
    content: str = Field(..., description="Message content as plain text.")
    timestamp: datetime.datetime = Field(..., description="UTC timestamp when message was sent.")

class ChatRequest(BaseModel):
    """Chat message sent from the frontend to receive a bot response."""
    message: str = Field(..., description="User message input to the chatbot.")
    session_id: Optional[str] = Field(
        None, description="Unique session identifier for conversation continuity. Provide if continuing a conversation."
    )

class ChatResponse(BaseModel):
    """Chatbot response with message(s) and session tracking."""
    session_id: str = Field(..., description="Session identifier for conversation context.")
    messages: List[Message] = Field(..., description="List of new messages in response to the user input.")

# ========================
# In-Memory Session Store (simple; use DB/cache for production)
# ========================
SESSION_STORE: Dict[str, List[Message]] = {}

# ========================
# Human-Like Behavior Logic
# ========================

def generate_humanlike_response(user_message: str, context: List[Message]) -> str:
    """
    Generate a human-like response to the user's message, adapting to context.
    Mimics conversational quirks, small talk, and emotional tone.
    """
    # Simulated behavioral quirks
    greetings = [
        "Hi there!", "Hello! How's it going?", "Hey!", "Good to see you.", "What's up?"
    ]
    farewells = [
        "Bye!", "Take care.", "See you later!", "Catch you next time.", "Goodbye!"
    ]
    small_talk_starters = [
        "By the way, have you done anything fun recently?",
        "Sometimes I wonder about random things. You?",
        "This might sound silly, but do you prefer coffee or tea?",
        "Ever have days that feel unusually long?",
    ]
    empathic_responses = [
        "I get how you feel.",
        "That sounds tough.",
        "I'm here to listen if you want to talk more.",
        "Yeah, that makes sense.",
    ]

    # Lowercase for simple keyword search
    m = user_message.strip().lower()
    resp = None

    # Some simple human-like "intents"
    if any(word in m for word in ["hello", "hi", "hey", "morning", "good afternoon"]):
        resp = random.choice(greetings)
    elif any(word in m for word in ["bye", "goodbye", "see you", "later"]):
        resp = random.choice(farewells)
    elif "how are you" in m or "how's it going" in m:
        resp = random.choice([
            "I'm good, thanks! How are you?",
            "Doing well! What's new with you?",
            "I'm just a program, but I'm feeling very... digital today.",
        ])
    elif "?" in m:
        resp = random.choice([
            "That's an interesting question.",
            "Let me think about that a moment...",
            "Hmm, I'd love to hear your thoughts too!",
        ])
    elif any(word in m for word in ["sad", "bad", "upset", "angry", "annoyed", "tired"]):
        resp = random.choice(empathic_responses)
    elif len(m) <= 4:
        resp = "Could you tell me a bit more?"
    elif random.random() < 0.1:
        # Occasionally inject small talk, like a real person
        resp = random.choice(small_talk_starters)

    # If not matched, slightly rephrase/repeat back, or use generic friendly response
    if resp is None:
        personality = [
            "Hmm, that's interesting.",
            "Tell me more about that.",
            "Why do you say that?",
            "Haha, okay!",
            "Can you elaborate?",
            f"You said: '{user_message}'. Can you expand on that?",
            "I see. What else?",
        ]
        # Occasionally misunderstand for realism
        if random.random() < 0.08:
            resp = "Sorry, can you clarify what you mean?"
        else:
            resp = random.choice(personality)

    # Human-like delay simulation: pretend to "think"
    if random.random() < 0.15:
        resp = resp + " (Sorry, took a second to think.)"

    return resp

# ========================
# Routes
# ========================

# PUBLIC_INTERFACE
@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"], summary="Send message, receive human-like chatbot reply")
async def chat_endpoint(payload: ChatRequest):
    """
    Send a message to the chatbot and receive a human-like response. Supports conversation sessions to enable context-aware replies.
    
    - **message:** The user's chat message.
    - **session_id (optional):** Provide to continue a conversation; otherwise, a new session is created.
    Returns a session_id (persist it for future requests) and message(s).
    """
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty message not allowed.")

    # Session management
    session_id = payload.session_id or str(uuid.uuid4())
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []
    context = SESSION_STORE[session_id]

    # Register user message
    msg_obj = Message(role="user", content=user_msg, timestamp=datetime.datetime.utcnow())
    context.append(msg_obj)

    # Generate bot's human-mimic response
    bot_text = generate_humanlike_response(user_msg, context)
    bot_obj = Message(role="bot", content=bot_text, timestamp=datetime.datetime.utcnow())
    context.append(bot_obj)

    # Output all messages in this session.
    return ChatResponse(session_id=session_id, messages=[msg_obj, bot_obj])


# PUBLIC_INTERFACE
@app.get("/api/history/{session_id}", response_model=List[Message], tags=["Chat"], summary="Get conversation history by session")
async def conversation_history(session_id: str):
    """
    Get all the messages in the specified chat session.
    - **session_id:** Identifier for conversation/session.
    Returns the entire chronologically-ordered message history for the session.
    """
    history = SESSION_STORE.get(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return history

# PUBLIC_INTERFACE
@app.delete("/api/history/{session_id}", tags=["Chat"], summary="Delete conversation session and memory")
async def delete_conversation(session_id: str):
    """
    Delete an existing chat session and all associated messages.
    Returns confirmation on success, or error if session is not found.
    """
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
        return {"detail": f"Session {session_id} deleted."}
    raise HTTPException(status_code=404, detail="Session not found.")


# Health check endpoint
# PUBLIC_INTERFACE
@app.get("/api/health", tags=["Health"], summary="Backend health check")
def health_check():
    """Returns 'ok' to indicate the backend is running."""
    return {"status": "ok", "service": "backend_chatbot", "timestamp": datetime.datetime.utcnow().isoformat()}


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="API root/info")
def root_info():
    """Returns basic info and docs link."""
    return {
        "api": "Human Mimicry Chatbot Backend",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": [
            "/api/chat (POST)",
            "/api/history/{session_id} (GET)",
            "/api/history/{session_id} (DELETE)",
            "/api/health (GET)"
        ]
    }

# ==== Entry Point ====
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    # Direct reload from within main.py causes infinite reload loops.
    # For auto-reload, run: uvicorn main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=port)
