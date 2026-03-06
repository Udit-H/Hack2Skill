"""
Sahayak FastAPI Backend
-----------------------
REST API for the Last Mile Justice Navigator.
Connects the React frontend to the multi-agent orchestrator.
"""

import uuid
import os
import tempfile
import asyncio
from contextlib import asynccontextmanager

# ─── MSYS2 DLL Setup for WeasyPrint on Windows ──────────────────
# Must happen BEFORE any weasyprint imports
msys_path = r"C:\msys64\ucrt64\bin"
if os.path.exists(msys_path):
    os.add_dll_directory(msys_path)
    print(f"✅ MSYS2 DLL directory added: {msys_path}")
else:
    print(f"⚠️  MSYS2 path not found — WebAssembly PDF generation may fail on Windows.")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Internal imports
from models.session import SessionState, AgentType, AgentActionType
from core.memory import MemoryManager
from core.orchestrator import Orchestrator
from services.chat_storage_service import ChatStorageService
from services.draft_storage_service import DraftStorageService

# ---------------------------------------------------------------------------
# Rate Limiter Configuration
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# In-memory session store (SQLite migration later)
# ---------------------------------------------------------------------------
sessions: dict[str, dict] = {}

# Global chat storage service
chat_storage = ChatStorageService()
draft_storage = DraftStorageService()


def get_or_create_session(session_id: str) -> dict:
    """Get or lazily create session components."""
    if session_id not in sessions:
        memory = MemoryManager(session_id)
        orchestrator = Orchestrator()

        # Session starts at ORCHESTRATOR — triage agent takes over first
        session_state = SessionState(
            session_id=session_id,
            user_phone=None,
            active_agent=AgentType.ORCHESTRATOR,
        )

        sessions[session_id] = {
            "state": session_state,
            "memory": memory,
            "orchestrator": orchestrator,
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
    version="0.2.0",
    lifespan=lifespan,
)

# Add rate limiter state to app
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )
)

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_id: Optional[str] = None  # User email/phone for session tracking


class ChatResponse(BaseModel):
    reply: str
    agent_info: dict
    progress_status: Optional[str] = None  # Agent operation status (searching, drafting, etc)
    is_loading: bool = False  # True when agent is actively processing
    error_message: Optional[str] = None  # Error details for UI display
    download_urls: Optional[list] = None  # List of downloadable document URLs


class SessionResponse(BaseModel):
    session_id: str
    active_agent: str
    workflow_status: str


class PanicRequest(BaseModel):
    session_id: str


class SessionListRequest(BaseModel):
    user_id: str  # Email or phone number


class LoadSessionRequest(BaseModel):
    session_id: str
    user_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/session", response_model=SessionResponse)
@limiter.limit("10/minute")
async def create_session(request: Request, req: Optional[SessionListRequest] = None):
    """Create a new session and return its ID."""
    session_id = f"s-{uuid.uuid4().hex[:12]}"
    sess = get_or_create_session(session_id)
    
    # Store user_id if provided
    if req and req.user_id:
        sess["state"].user_phone = req.user_id

    return SessionResponse(
        session_id=session_id,
        active_agent=sess["state"].active_agent.value,
        workflow_status="triage_pending",
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
@limiter.limit("30/minute")
async def get_session(request: Request, session_id: str):
    """Get current session state."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    sess = sessions[session_id]
    state = sess["state"]
    
    # Determine workflow status from active agent's state
    workflow_status = _get_workflow_status(state)

    return SessionResponse(
        session_id=session_id,
        active_agent=state.active_agent.value,
        workflow_status=workflow_status,
    )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    """Process a user message through the active agent."""
    sess = get_or_create_session(req.session_id)
    state = sess["state"]
    memory = sess["memory"]
    orchestrator = sess["orchestrator"]

    try:
        # Inject GPS coordinates from client location access when provided
        if req.latitude is not None and req.longitude is not None:
            if not state.shelter:
                from models.shelter import ShelterAgentState
                state.shelter = ShelterAgentState()
            state.shelter.user_coordinates = {"lat": req.latitude, "lng": req.longitude}
            if not state.shelter.user_location_text:
                state.shelter.user_location_text = f"{req.latitude},{req.longitude}"
            if not state.shelter.user_preferences:
                state.shelter.user_preferences = "No specific requirements"

        # Route through orchestrator — it handles triage, shelter, legal, drafting
        reply = await orchestrator.handle_turn(
            session=state,
            memory_manager=memory,
            user_message=req.message,
        )

        # Update memory
        memory.add_turn(user_message=req.message, ai_message=reply)
        
        # Persist chat messages to DynamoDB
        user_id = req.user_id or state.user_phone
        await chat_storage.save_message(
            session_id=req.session_id,
            role='user',
            content=req.message,
            agent_type=state.active_agent.value,
            user_id=user_id,
        )
        
        # Save assistant response with metadata
        response_metadata = {}
        if state.last_agent_response:
            response_metadata = {
                'progress_status': state.last_agent_response.get('progress_status'),
                'is_loading': state.last_agent_response.get('is_loading'),
                'error_message': state.last_agent_response.get('error_message'),
                'download_urls': state.last_agent_response.get('download_urls'),
            }
        
        await chat_storage.save_message(
            session_id=req.session_id,
            role='assistant',
            content=reply,
            agent_type=state.active_agent.value,
            metadata=response_metadata if response_metadata else None,
            user_id=user_id,
        )
        
        # Extract progress/error info from cached agent response
        progress_status = None
        is_loading = False
        error_message = None
        download_urls = None
        if state.last_agent_response:
            progress_status = state.last_agent_response.get("progress_status")
            is_loading = state.last_agent_response.get("is_loading", False)
            error_message = state.last_agent_response.get("error_message")
            download_urls = state.last_agent_response.get("download_urls")

        return ChatResponse(
            reply=reply,
            agent_info={
                "activeAgent": state.active_agent.value,
                "workflowStatus": _get_workflow_status(state),
            },
            progress_status=progress_status,
            is_loading=is_loading,
            error_message=error_message,
            download_urls=download_urls,
        )

    except Exception as e:
        print(f"❌ Chat error for session {req.session_id}: {e}")
        import traceback
        traceback.print_exc()
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
    orchestrator = sess["orchestrator"]

    # Save file temporarily
    upload_dir = "/tmp/sahayak_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{session_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        # Route through orchestrator with document
        reply = await orchestrator.handle_turn(
            session=state,
            memory_manager=memory,
            user_message=f"I am uploading my document: {file.filename}",
            document_path=file_path,
        )

        # Log OCR result
        ocr_text = state.legal.extracted_doc_data if state.legal else None
        if ocr_text:
            preview = ocr_text[:500]
            print(f"\n📄 OCR RESULT for {file.filename}:")
            print(f"   Length: {len(ocr_text)} chars")
            print(f"   Preview: {preview}...\n")

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
                "workflowStatus": _get_workflow_status(state),
            },
        }

    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload processing error: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/api/drafts/{session_id}/{filename}")
async def download_draft(session_id: str, filename: str):
    """Download a generated PDF draft from S3 (with local fallback)."""
    # Prefer S3 storage: generate a fresh presigned URL each request
    try:
        if draft_storage.object_exists(session_id, filename):
            presigned_url = draft_storage.generate_presigned_download_url(session_id, filename)
            return RedirectResponse(url=presigned_url, status_code=307)
    except Exception as e:
        print(f"⚠️  S3 draft lookup failed for {session_id}/{filename}: {e}")

    # Backward-compatible fallback to local temp file
    draft_path = os.path.join(tempfile.gettempdir(), "sahayak_drafts", session_id, filename)
    
    if not os.path.exists(draft_path):
        raise HTTPException(status_code=404, detail="Draft not found")

    return FileResponse(
        path=draft_path,
        media_type="application/pdf",
        filename=filename,
    )


@app.get("/api/chat-history/{session_id}")
@limiter.limit("10/minute")
async def get_chat_history(request: Request, session_id: str, limit: int = 50):
    """Retrieve chat history from DynamoDB for a session."""
    try:
        messages = await chat_storage.get_session_history(session_id, limit=limit)
        return {
            "success": True,
            "session_id": session_id,
            "message_count": len(messages),
            "messages": messages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@app.post("/api/sessions/list")
@limiter.limit("10/minute")
async def list_user_sessions(request: Request, req: SessionListRequest):
    """List all chat sessions for a user."""
    try:
        sessions = await chat_storage.list_user_sessions(req.user_id, limit=20)
        return {
            "success": True,
            "user_id": req.user_id,
            "session_count": len(sessions),
            "sessions": sessions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.post("/api/sessions/load")
@limiter.limit("10/minute")
async def load_session(request: Request, req: LoadSessionRequest):
    """Load an existing session with its chat history."""
    try:
        # Get chat history
        messages = await chat_storage.get_session_history(req.session_id, limit=100)
        
        # Get or create session state
        sess = get_or_create_session(req.session_id)
        state = sess["state"]
        state.user_phone = req.user_id
        
        # Return session info with history
        return {
            "success": True,
            "session_id": req.session_id,
            "messages": messages,
            "agent_info": {
                "activeAgent": state.active_agent.value,
                "workflowStatus": _get_workflow_status(state),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load session: {str(e)}")


@app.post("/api/panic")
@limiter.limit("1/minute")
async def panic_wipe(request: Request, req: PanicRequest):
    """Emergency session wipe — delete all data for this session."""
    if req.session_id in sessions:
        sess = sessions.pop(req.session_id)

        # Clear DynamoDB chat history
        await chat_storage.delete_session_history(req.session_id)

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
    return {"status": "ok", "service": "sahayak-api", "version": "0.2.0"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_workflow_status(state: SessionState) -> str:
    """Get a human-readable workflow status from the current session state."""
    agent = state.active_agent
    
    if agent == AgentType.TRIAGE and state.triage:
        return state.triage.workflow_status.value
    elif agent == AgentType.SHELTER and state.shelter:
        return state.shelter.workflow_status.value
    elif agent == AgentType.LEGAL and state.legal:
        return state.legal.workflow_status.value
    elif agent == AgentType.DRAFTING and state.drafting:
        return state.drafting.workflow_status.value
    elif agent == AgentType.COMPLETED:
        return "completed"
    elif agent == AgentType.ORCHESTRATOR:
        return "routing"
    else:
        return "initializing"
