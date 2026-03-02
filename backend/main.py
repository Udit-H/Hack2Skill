"""
Sahayak FastAPI Backend
-----------------------
REST API for the Last Mile Justice Navigator.
Connects the React frontend to the multi-agent orchestrator.
"""

import uuid
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pydantic import BaseModel
from typing import Optional

# Internal imports
from models.session import SessionState, AgentType, AgentActionType
from models.triage import TriageState
from models.legal import LegalAgentState, WorkflowStatus
from models.enums import CrisisCategory
from core.memory import MemoryManager
from agents.legal_agent import LegalAgent

# ---------------------------------------------------------------------------
# Rate Limiter Configuration
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# In-memory session store (SQLite migration later)
# ---------------------------------------------------------------------------
sessions: dict[str, dict] = {}


def get_or_create_session(session_id: str) -> dict:
    """Get or lazily create session components."""
    if session_id not in sessions:
        # Initialize a fresh session with mocked triage (eviction focus)
        memory = MemoryManager(session_id)
        legal_agent = LegalAgent()

        session_state = SessionState(
            session_id=session_id,
            user_phone=None,
            active_agent=AgentType.LEGAL,
            triage=TriageState(
                category=CrisisCategory.ILLEGAL_EVICTION,
                urgency_level=4,
                needs_immediate_shelter=False,
                physical_danger_present=False,
                incident_summary="User is seeking help with an eviction-related issue.",
                has_ownership_claim=False,
                is_financially_destitute=False,
            ),
            legal=LegalAgentState(
                workflow_status=WorkflowStatus.AWAITING_USER_INFO,
                drafts_to_generate=[],
            ),
        )

        sessions[session_id] = {
            "state": session_state,
            "memory": memory,
            "legal_agent": legal_agent,
        }

    return sessions[session_id]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Sahayak backend starting...")
    yield
    print("🛑 Sahayak backend shutting down...")
    sessions.clear()


app = FastAPI(
    title="Sahayak API",
    description="Last Mile Justice Navigator — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add rate limiter state to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: {
    "detail": "Rate limit exceeded. Please try again later."
})

# CORS Configuration (improved for production and local dev)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Configurable via environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: str = "en"


class ChatResponse(BaseModel):
    reply: str
    agent_info: dict


class SessionResponse(BaseModel):
    session_id: str
    active_agent: str
    workflow_status: str


class PanicRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/session", response_model=SessionResponse)
@limiter.limit("10/minute")
async def create_session(request: Request):
    """Create a new session and return its ID."""
    session_id = f"s-{uuid.uuid4().hex[:12]}"
    sess = get_or_create_session(session_id)

    return SessionResponse(
        session_id=session_id,
        active_agent=sess["state"].active_agent.value,
        workflow_status=sess["state"].legal.workflow_status.value
        if sess["state"].legal
        else "unknown",
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
@limiter.limit("30/minute")
async def get_session(request: Request, session_id: str):
    """Get current session state."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    sess = sessions[session_id]
    return SessionResponse(
        session_id=session_id,
        active_agent=sess["state"].active_agent.value,
        workflow_status=sess["state"].legal.workflow_status.value
        if sess["state"].legal
        else "unknown",
    )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    """Process a user message through the active agent."""
    sess = get_or_create_session(req.session_id)
    state = sess["state"]
    memory = sess["memory"]
    legal_agent = sess["legal_agent"]

    try:
        # Route to the active agent
        if state.active_agent == AgentType.LEGAL:
            response = await legal_agent.process_turn(
                session=state,
                user_message=req.message,
                memory_manager=memory,
                language=req.language,
            )

            reply = response.reply_message or "I'm processing your request."

            # Update memory
            memory.add_turn(user_message=req.message, ai_message=reply)

            return ChatResponse(
                reply=reply,
                agent_info={
                    "activeAgent": state.active_agent.value,
                    "workflowStatus": state.legal.workflow_status.value
                    if state.legal
                    else "unknown",
                    "switchTriggered": response.action_type
                    == AgentActionType.SWITCH_AGENT,
                },
            )
        else:
            # Fallback for agents not yet implemented
            return ChatResponse(
                reply="This agent is not yet available. Currently, only the Legal Agent is active.",
                agent_info={
                    "activeAgent": state.active_agent.value,
                    "workflowStatus": "unavailable",
                },
            )

    except Exception as e:
        print(f"❌ Chat error for session {req.session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/upload")
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload a document for OCR processing."""
    
    # Define allowed file types and their max sizes (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_PDF_SIZE = 15 * 1024 * 1024    # 15MB
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    }
    
    # Validate file extension
    file_name_lower = file.filename.lower()
    file_extension = "." + file_name_lower.split(".")[-1] if "." in file_name_lower else ""
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_extension}'. Only PDF, JPG, PNG, and TIFF files are allowed."
        )
    
    # Validate file MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type '{file.content_type}'. Only image and PDF files are allowed."
        )
    
    # Read file and validate size
    contents = await file.read()
    file_size = len(contents)
    
    is_pdf = file_extension == ".pdf"
    max_size = MAX_PDF_SIZE if is_pdf else MAX_IMAGE_SIZE
    max_size_mb = 15 if is_pdf else 10
    
    if file_size > max_size:
        file_size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. {'PDFs' if is_pdf else 'Images'} must be under {max_size_mb}MB. Your file is {file_size_mb:.1f}MB."
        )
    
    sess = get_or_create_session(session_id)
    state = sess["state"]
    memory = sess["memory"]
    legal_agent = sess["legal_agent"]

    # Save file temporarily
    upload_dir = "/tmp/sahayak_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{session_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        # Process through legal agent with document
        response = await legal_agent.process_turn(
            session=state,
            user_message=f"I am uploading my document: {file.filename}",
            document_path=file_path,
            memory_manager=memory,
        )

        # Log OCR result so we can verify it worked
        ocr_text = state.legal.extracted_doc_data if state.legal else None
        if ocr_text:
            preview = ocr_text[:500]
            print(f"\n📄 OCR RESULT for {file.filename}:")
            print(f"   Length: {len(ocr_text)} chars")
            print(f"   Preview: {preview}...\n")

        reply = response.reply_message or "Document received and being analyzed."
        memory.add_turn(
            user_message=f"Uploaded document: {file.filename}",
            ai_message=reply,
        )

        return {
            "reply": reply,
            "filename": file.filename,
            "ocr_preview": (ocr_text[:300] + "...") if ocr_text and len(ocr_text) > 300 else ocr_text,
            "ocr_length": len(ocr_text) if ocr_text else 0,
            "agent_info": {
                "activeAgent": state.active_agent.value,
                "workflowStatus": state.legal.workflow_status.value
                if state.legal
                else "unknown",
            },
        }

    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload processing error: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/api/panic")
@limiter.limit("1/minute")
async def panic_wipe(request: Request, req: PanicRequest):
    """Emergency session wipe — delete all data for this session."""
    if req.session_id in sessions:
        sess = sessions.pop(req.session_id)

        # Clear Redis memory too
        try:
            memory = sess["memory"]
            memory.redis_client.delete(memory.working_memory_key)
            memory.redis_client.delete(memory.episodic_memory_key)
        except Exception:
            pass  # Best-effort cleanup

    return {"status": "wiped", "message": "All session data has been permanently deleted."}


@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {"status": "ok", "service": "sahayak-api"}
