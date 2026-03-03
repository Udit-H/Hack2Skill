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

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

# Internal imports
from models.session import SessionState, AgentType, AgentActionType
from core.memory import MemoryManager
from core.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# In-memory session store (SQLite migration later)
# ---------------------------------------------------------------------------
sessions: dict[str, dict] = {}


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

# CORS for local dev (Vite proxy handles it, but this is a safety net)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def create_session():
    """Create a new session and return its ID."""
    session_id = f"s-{uuid.uuid4().hex[:12]}"
    sess = get_or_create_session(session_id)

    return SessionResponse(
        session_id=session_id,
        active_agent=sess["state"].active_agent.value,
        workflow_status="triage_pending",
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
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
async def chat(req: ChatRequest):
    """Process a user message through the orchestrator."""
    sess = get_or_create_session(req.session_id)
    state = sess["state"]
    memory = sess["memory"]
    orchestrator = sess["orchestrator"]

    try:
        # Route through orchestrator — it handles triage, shelter, legal, drafting
        reply = await orchestrator.handle_turn(
            session=state,
            memory_manager=memory,
            user_message=req.message,
        )

        # Update memory
        memory.add_turn(user_message=req.message, ai_message=reply)

        return ChatResponse(
            reply=reply,
            agent_info={
                "activeAgent": state.active_agent.value,
                "workflowStatus": _get_workflow_status(state),
            },
        )

    except Exception as e:
        print(f"❌ Chat error for session {req.session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload a document for OCR processing."""
    sess = get_or_create_session(session_id)
    state = sess["state"]
    memory = sess["memory"]
    orchestrator = sess["orchestrator"]

    # Save file temporarily
    upload_dir = "/tmp/sahayak_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{session_id}_{file.filename}")

    contents = await file.read()
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
    """Download a generated PDF draft."""
    draft_path = os.path.join("/tmp/sahayak_drafts", session_id, filename)
    
    if not os.path.exists(draft_path):
        raise HTTPException(status_code=404, detail="Draft not found")

    return FileResponse(
        path=draft_path,
        media_type="application/pdf",
        filename=filename,
    )


@app.post("/api/panic")
async def panic_wipe(req: PanicRequest):
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
async def health_check():
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
