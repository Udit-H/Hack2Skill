"""
🏠 SHELTER AGENT - FASTAPI SERVER
Simple server for testing the shelter agent via Postman

Run: uvicorn main:app --reload
Then open http://localhost:8000/docs for Swagger UI
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio
from datetime import datetime

from models.session import SessionState, AgentType, AgentResponse, AgentActionType
from models.shelter import ShelterAgentState
from models.triage import TriageState
from models.enums import CrisisCategory
from core.memory import MemoryManager
from agents.shelter_agent import ShelterAgent


app = FastAPI(
    title="Last Mile Justice Navigator - Shelter Agent",
    description="Emergency shelter discovery and dispatch service",
    version="1.0.0"
)

# Global agent instance (thread-safe)
shelter_agent = ShelterAgent()

# In-memory session storage (for demo; use Redis in production)
sessions = {}


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ShelterAgentRequest(BaseModel):
    """User message sent to shelter agent"""
    user_id: str
    message: str
    user_phone: Optional[str] = "+919999999999"


class ShelterAgentResponse(BaseModel):
    """Agent response to user"""
    user_id: str
    reply_message: str
    action_type: str
    next_active_agent: Optional[str]
    workflow_status: str
    matched_shelters_count: int
    timestamp: str


class SessionInfoResponse(BaseModel):
    """Current session state"""
    user_id: str
    workflow_status: str
    user_location: Optional[dict]
    user_profile: Optional[dict]
    matched_shelters_count: int
    selected_shelter: Optional[dict]
    conversation_turns: int


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Shelter Agent API",
        "endpoints": {
            "chat": "POST /chat",
            "session": "GET /session/{user_id}",
            "new_session": "POST /session/new",
            "docs": "GET /docs"
        }
    }


@app.post("/session/new", response_model=dict, tags=["Session Management"])
async def create_new_session(user_id: str, user_phone: str = "+919999999999"):
    """
    Create a new session for a user
    
    Example:
    ```
    POST /session/new?user_id=user-123&user_phone=%2B919999999999
    ```
    """
    if user_id in sessions:
        return {"error": "Session already exists", "user_id": user_id}
    
    session = SessionState(
        session_id=user_id,
        user_phone=user_phone,
        active_agent=AgentType.SHELTER,
        triage=TriageState(
            category=CrisisCategory.ILLEGAL_EVICTION,
            urgency_level=5,
            incident_summary="User needs emergency shelter",
            has_ownership_claim=False,
            is_financially_destitute=True,
            needs_immediate_shelter=True,
            physical_danger_present=False
        ),
        shelter=ShelterAgentState()
    )
    
    sessions[user_id] = {
        "session": session,
        "memory": MemoryManager(user_id),
        "turns": 0
    }
    
    return {
        "status": "session_created",
        "user_id": user_id,
        "user_phone": user_phone,
        "workflow_status": str(session.shelter.workflow_status),
        "message": "Session ready. Send your first message to /chat"
    }


@app.get("/session/{user_id}", response_model=SessionInfoResponse, tags=["Session Management"])
async def get_session_info(user_id: str):
    """Get current session state"""
    if user_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[user_id]
    session = session_data["session"]
    
    user_location = None
    if session.shelter.user_location:
        user_location = {
            "latitude": session.shelter.user_location.latitude,
            "longitude": session.shelter.user_location.longitude
        }
    
    user_profile = None
    if session.shelter.user_profile:
        user_profile = {
            "gender": session.shelter.user_profile.gender,
            "age_group": session.shelter.user_profile.age_group,
            "has_children": session.shelter.user_profile.has_children,
            "medical_needs": session.shelter.user_profile.medical_needs
        }
    
    selected_shelter = None
    if session.shelter.selected_shelter:
        selected_shelter = {
            "name": session.shelter.selected_shelter.name,
            "address": session.shelter.selected_shelter.address,
            "contact": session.shelter.selected_shelter.contact_number,
            "distance_km": session.shelter.selected_shelter.distance_km
        }
    
    return SessionInfoResponse(
        user_id=user_id,
        workflow_status=str(session.shelter.workflow_status),
        user_location=user_location,
        user_profile=user_profile,
        matched_shelters_count=len(session.shelter.matched_shelters),
        selected_shelter=selected_shelter,
        conversation_turns=session_data["turns"]
    )


@app.post("/chat", response_model=ShelterAgentResponse, tags=["Chat"])
async def chat(request: ShelterAgentRequest):
    """
    Send a message to the shelter agent
    
    Example:
    ```json
    {
        "user_id": "user-123",
        "message": "I need emergency shelter! I'm locked out!",
        "user_phone": "+919999999999"
    }
    ```
    """
    
    # Auto-create session if doesn't exist
    if request.user_id not in sessions:
        await create_new_session(request.user_id, request.user_phone)
    
    session_data = sessions[request.user_id]
    session = session_data["session"]
    memory = session_data["memory"]
    
    try:
        # Call the shelter agent
        response = await shelter_agent.process_turn(
            session=session,
            user_message=request.message,
            memory_manager=memory
        )
        
        session_data["turns"] += 1
        
        return ShelterAgentResponse(
            user_id=request.user_id,
            reply_message=response.reply_message,
            action_type=str(response.action_type),
            next_active_agent=str(response.next_active_agent) if response.next_active_agent else None,
            workflow_status=str(session.shelter.workflow_status),
            matched_shelters_count=len(session.shelter.matched_shelters),
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.delete("/session/{user_id}", tags=["Session Management"])
async def delete_session(user_id: str):
    """Delete a session (end conversation)"""
    if user_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[user_id]
    return {"status": "session_deleted", "user_id": user_id}


# ============================================================================
# EXAMPLE CONVERSATION FLOW (FOR TESTING)
# ============================================================================

@app.get("/example-flow", tags=["Testing"])
async def example_flow():
    """
    Run a complete example conversation
    Shows the full workflow in action
    """
    user_id = "example-001"
    
    # Create session
    await create_new_session(user_id)
    
    # Turn 1
    response1 = await chat(ShelterAgentRequest(
        user_id=user_id,
        message="Help! I've been locked out and need a place to sleep tonight!"
    ))
    
    # Turn 2
    response2 = await chat(ShelterAgentRequest(
        user_id=user_id,
        message="I'm near Kashmere Gate in Delhi. I'm a woman with a daughter."
    ))
    
    # Turn 3
    session_info = await get_session_info(user_id)
    
    return {
        "conversation": [
            {"turn": 1, "agent": response1.reply_message},
            {"turn": 2, "agent": response2.reply_message},
        ],
        "session_status": {
            "workflow_status": session_info.workflow_status,
            "matched_shelters": session_info.matched_shelters_count,
            "user_location": session_info.user_location,
            "user_profile": session_info.user_profile
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
