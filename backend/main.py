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
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Internal imports
from models.session import SessionState, AgentType, AgentActionType
from models.legal import LegalAgentState
from core.memory import MemoryManager
from core.orchestrator import Orchestrator
from services.chat_storage_service import ChatStorageService
from services.draft_storage_service import DraftStorageService
from services.ocr_service import DocumentIntelligenceService

logger = logging.getLogger(__name__)

# Configure logging to show INFO level for our modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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

# CORS Configuration (allow all origins)
print("🌐 CORS enabled for all origins (*)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
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
    user_id: str


class SessionListRequest(BaseModel):
    user_id: str  # Email or phone number


class LoadSessionRequest(BaseModel):
    session_id: str
    user_id: str


async def _assert_session_owner(session_id: str, user_id: str) -> None:
    """Ensure the caller owns the session before exposing or mutating data."""
    if not user_id:
        raise HTTPException(status_code=401, detail="user_id is required")

    # First trust active in-memory owner binding
    if session_id in sessions:
        sess = sessions[session_id]
        state = sess["state"]

        # Bind owner lazily if session was created without user_id
        if not state.user_phone:
            state.user_phone = user_id
            return

        if state.user_phone != user_id:
            raise HTTPException(status_code=403, detail="Access denied for this session")
        return

    # Fallback to persisted chat ownership check for restored sessions
    owns_session = await chat_storage.is_session_owned_by_user(session_id, user_id)
    if not owns_session:
        raise HTTPException(status_code=403, detail="Access denied for this session")


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

    # -------------------------------------------------------------------------
    # STEP 1: Run OCR HERE in the upload endpoint (before any agent)
    # -------------------------------------------------------------------------
    ocr_text = None
    ocr_error = None
    try:
        logger.info(f"📄 OCR START: file={file.filename}, size={file_size} bytes, "
                     f"ext={file_extension}, mime={file.content_type}, session={session_id}")
        logger.info(f"📄 OCR INPUT: file_path={file_path}, exists={os.path.exists(file_path)}, "
                     f"file_size_on_disk={os.path.getsize(file_path)} bytes")
        
        ocr_service = DocumentIntelligenceService()
        ocr_result = await ocr_service.analyze(source=file_path)
        
        ocr_status = ocr_result.get("status", "unknown")
        ocr_text = ocr_result.get("content", "")
        page_count = ocr_result.get("page_count", 0)
        confidence = ocr_result.get("confidence_avg", 0)
        
        logger.info(f"📄 OCR RESULT: status={ocr_status}, pages={page_count}, "
                     f"confidence={confidence:.2f}, text_length={len(ocr_text)} chars")
        
        if ocr_text:
            preview = ocr_text[:300].replace('\n', ' ')
            logger.info(f"📄 OCR PREVIEW: {preview}...")
        else:
            logger.warning(f"⚠️ OCR returned EMPTY text for {file.filename} "
                          f"(status={ocr_status}, pages={page_count})")
            ocr_error = "Textract returned empty text"
            
    except Exception as e:
        ocr_error = str(e)
        logger.error(f"❌ OCR FAILED for {file.filename}: {type(e).__name__}: {e}", exc_info=True)
        logger.error(f"❌ OCR DEBUG: region={os.environ.get('AWS_REGION', 'not set')}, "
                     f"s3_bucket={os.environ.get('S3_BUCKET_NAME', 'not set')}, "
                     f"aws_key_set={bool(os.environ.get('AWS_ACCESS_KEY_ID'))}")

    # -------------------------------------------------------------------------
    # STEP 2: Store extracted text on session state (so agents can use it)
    # -------------------------------------------------------------------------
    if ocr_text:
        # Ensure legal state exists to store the OCR data
        if not state.legal:
            state.legal = LegalAgentState()
        state.legal.extracted_doc_data = ocr_text
        logger.info(f"✅ Stored OCR text on session.legal.extracted_doc_data ({len(ocr_text)} chars)")

    # -------------------------------------------------------------------------
    # STEP 3: Build the user message to send to the agent
    # Include extracted text so the LLM MUST acknowledge it
    # -------------------------------------------------------------------------
    if ocr_text:
        # Include first 2000 chars of extracted text in the user message
        # so the active agent (even triage) sees the document content
        text_preview = ocr_text[:2000]
        user_message = (
            f"I am uploading my document: {file.filename}\n\n"
            f"--- EXTRACTED DOCUMENT TEXT ---\n{text_preview}\n--- END OF EXTRACTED TEXT ---\n\n"
            f"Please summarize what this document says and tell me what information you still need."
        )
    elif ocr_error:
        user_message = (
            f"I am uploading my document: {file.filename}\n\n"
            f"Note: Document text extraction encountered an issue: {ocr_error}. "
            f"Please ask me to describe the document contents."
        )
    else:
        user_message = f"I am uploading my document: {file.filename}"

    try:
        # Route through orchestrator with document
        reply = await orchestrator.handle_turn(
            session=state,
            memory_manager=memory,
            user_message=user_message,
            document_path=file_path,
        )

        logger.info(f"📄 AGENT REPLY (first 200 chars): {reply[:200] if reply else 'None'}...")

        # If OCR succeeded but agent reply doesn't mention document content,
        # prepend extraction summary so user knows it worked
        if ocr_text:
            doc_keywords = ["document", "agreement", "extracted", "uploaded", "can see",
                            "rental", "contract", "notice", "i've read", "i can see",
                            "this appears", "this is a", "the document"]
            if not any(kw in reply.lower() for kw in doc_keywords):
                reply = (
                    f"📄 I've successfully extracted text from **{file.filename}** "
                    f"({len(ocr_text):,} characters). I'm now analyzing the contents.\n\n{reply}"
                )

        # If OCR failed entirely, warn the user
        if ocr_error and "extraction" not in reply.lower():
            reply = (
                f"⚠️ I had trouble reading **{file.filename}** automatically "
                f"(Error: {ocr_error}). Could you briefly describe what the document says?\n\n{reply}"
            )

        memory.add_turn(
            user_message=f"Uploaded document: {file.filename}",
            ai_message=reply,
        )

        return {
            "reply": reply,
            "filename": file.filename,
            "ocr_preview": (ocr_text[:300] + "...") if ocr_text and len(ocr_text) > 300 else ocr_text,
            "ocr_length": len(ocr_text) if ocr_text else 0,
            "ocr_error": ocr_error,
            "agent_info": {
                "activeAgent": state.active_agent.value,
                "workflowStatus": _get_workflow_status(state),
            },
        }

    except Exception as e:
        logger.error(f"❌ Upload processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload processing error: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/api/drafts/{session_id}/{filename}")
async def download_draft(session_id: str, filename: str):
    """Download a generated PDF draft — streams content directly (no redirect)."""
    # Prefer S3 storage: download bytes and stream back to client
    try:
        if draft_storage.object_exists(session_id, filename):
            content = draft_storage.download_draft_bytes(session_id, filename)
            return Response(
                content=content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
    except Exception as e:
        print(f"⚠️  S3 draft download failed for {session_id}/{filename}: {e}")

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
async def get_chat_history(request: Request, session_id: str, user_id: str, limit: int = 50):
    """Retrieve chat history from DynamoDB for a session."""
    try:
        await _assert_session_owner(session_id, user_id)
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
        await _assert_session_owner(req.session_id, req.user_id)

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
    await _assert_session_owner(req.session_id, req.user_id)

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
