"""
Sahayak — Offline CLI Test: Legal + Shelter + Drafting Pipeline
----------------------------------------------------------------
Bypasses ALL external services (LLM, Redis, Supabase).
Pre-fills realistic session state and runs the Drafting Agent 
to generate actual PDFs you can open.

Usage:
    cd backend
    python playground/test_drafting_cli.py
"""

import asyncio
import sys
import os

# Ensure backend/ is on the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.session import SessionState, AgentType
from models.triage import TriageState, TriageWorkflowStatus
from models.legal import (
    LegalAgentState,
    WorkflowStatus as LegalWorkflowStatus,
    LegalDraftPayload,
    DraftType,
)
from models.shelter import ShelterAgentState, ShelterWorkflowStatus, ShelterProfile
from models.drafting import DraftingAgentState, DraftingWorkflowStatus
from models.enums import CrisisCategory
from agents.drafting_agent import DraftingAgent


# ── Fake Memory Manager (no Redis needed) ─────────────────────────
class MockMemoryManager:
    """Stub that satisfies the memory_manager interface without Redis."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def get_memory_context(self) -> str:
        return "<long_term_summary>Mock test session — no real memory.</long_term_summary>"

    def add_turn(self, user_message: str, ai_message: str):
        pass  # no-op


# ── Build a fully-populated session ────────────────────────────────

def build_mock_session() -> SessionState:
    """
    Simulates the state AFTER Triage + Legal + Shelter agents have 
    finished their conversational work. All fields pre-filled.
    """
    session_id = "test-draft-offline-001"

    # ─── 1. TRIAGE (Completed) ───
    triage = TriageState(
        workflow_status=TriageWorkflowStatus.COMPLETED,
        category=CrisisCategory.ILLEGAL_EVICTION,
        urgency_level=4,
        incident_summary=(
            "Rajesh Kumar, a tenant in Koramangala, Bengaluru, was illegally locked out "
            "of his rented flat by landlord Suresh Reddy on 28 Feb 2026. The landlord changed "
            "the locks while Rajesh was at work, cut off electricity, and threatened physical harm."
        ),
        victim_name="Rajesh Kumar",
        aggressor_name="Suresh Reddy",
        property_address="Flat 302, Sai Krupa Apartments, 4th Cross, Koramangala 5th Block, Bengaluru 560095",
        eviction_reason="Landlord wants to sell the property; tenant refused to vacate without legal notice.",
        has_ownership_claim=False,
        is_financially_destitute=True,
        needs_immediate_shelter=True,
        needs_legal_action=True,
        next_question_for_user=None,
    )

    # ─── 2. LEGAL AGENT (Ready to Draft) ───
    legal = LegalAgentState(
        workflow_status=LegalWorkflowStatus.READY_TO_DRAFT,
        extracted_doc_data=(
            "RENT AGREEMENT\n"
            "This Agreement is made on 15th March 2024 between Suresh Reddy (Landlord) "
            "and Rajesh Kumar (Tenant) for Flat 302, Sai Krupa Apartments, Koramangala. "
            "Monthly rent: ₹18,000. Lock-in period: 11 months. Security deposit: ₹90,000."
        ),
        retrieved_legal_context=(
            "Karnataka Rent Control Act, 1999 — Section 27: No landlord shall cut off or "
            "withhold essential supply. BNS Section 126(2): Wrongful restraint is punishable. "
            "CPC Order XXXIX: Court may grant temporary injunction to prevent dispossession."
        ),
        next_question_for_user=None,
        user_consent_police=True,
        drafts_to_generate=[
            LegalDraftPayload(
                draft_type=DraftType.POLICE_INTIMATION,
                applicant_name="Rajesh Kumar",
                opponent_name="Suresh Reddy",
                property_address="Flat 302, Sai Krupa Apartments, 4th Cross, Koramangala 5th Block, Bengaluru 560095",
                monthly_income=25000,
                caste_category="General",
                draft_body_summary=(
                    "On 28 February 2026, at approximately 2:00 PM, the landlord Suresh Reddy "
                    "forcibly changed the locks of Flat 302, Sai Krupa Apartments, Koramangala, "
                    "while the tenant Rajesh Kumar was at his workplace. Upon returning at 7:00 PM, "
                    "Rajesh found himself locked out with his belongings still inside. The landlord "
                    "also disconnected the electricity supply. When confronted, the landlord threatened "
                    "physical violence and refused to return the keys. This constitutes wrongful restraint "
                    "under BNS Section 126(2) and criminal intimidation."
                ),
            ),
            LegalDraftPayload(
                draft_type=DraftType.CIVIL_INJUNCTION_PETITION,
                applicant_name="Rajesh Kumar",
                opponent_name="Suresh Reddy",
                property_address="Flat 302, Sai Krupa Apartments, 4th Cross, Koramangala 5th Block, Bengaluru 560095",
                monthly_income=25000,
                caste_category="General",
                draft_body_summary=(
                    "That on 28 February 2026, the Respondent/Landlord without following due process "
                    "of law, forcibly locked out the Applicant from the rented premises by changing the "
                    "door locks and disconnecting electricity, despite the Applicant being a lawful tenant "
                    "under a valid Rent Agreement dated 15 March 2024. The Applicant's personal belongings, "
                    "including essential documents, remain trapped inside the premises."
                ),
            ),
            LegalDraftPayload(
                draft_type=DraftType.KSLSA_LEGAL_AID,
                applicant_name="Rajesh Kumar",
                opponent_name="Suresh Reddy",
                property_address="Flat 302, Sai Krupa Apartments, 4th Cross, Koramangala 5th Block, Bengaluru 560095",
                monthly_income=25000,
                caste_category="General",
                draft_body_summary=(
                    "Application for free legal aid under Section 12 of the Legal Services Authorities Act, 1987. "
                    "The applicant Rajesh Kumar, a salaried individual earning ₹25,000/month, has been illegally "
                    "evicted from his rented premises by the landlord. He is unable to afford private legal counsel "
                    "and seeks assistance from KSLSA for filing a civil suit for injunction and recovery of possession."
                ),
            ),
        ],
    )

    # ─── 3. SHELTER AGENT (Completed with consent) ───
    shelter = ShelterAgentState(
        workflow_status=ShelterWorkflowStatus.COMPLETED,
        user_location_text="Koramangala, Bengaluru",
        user_coordinates={"lat": 12.9352, "lng": 77.6245},
        user_preferences="Men's shelter, safe, close to Koramangala",
        user_consent_to_share=True,
        free_shelter_needed=True,
        selected_shelter_ids=[1],
        matched_shelters=[
            ShelterProfile(
                shelter_id=1,
                name="Bengaluru Urban Night Shelter — Koramangala",
                shelter_type="Government Night Shelter",
                address="Near Forum Mall, Koramangala 7th Block, Bengaluru 560095",
                contact_number="080-2553-1234",
                distance_km=1.2,
                google_maps_url="https://maps.google.com/?q=12.9352,77.6245",
            ),
            ShelterProfile(
                shelter_id=2,
                name="BOSCO Yuvakendra — Men's Emergency Shelter",
                shelter_type="NGO Shelter",
                address="Magadi Road, Bengaluru 560023",
                contact_number="080-2337-5678",
                distance_km=8.5,
                google_maps_url="https://maps.google.com/?q=12.9580,77.5510",
            ),
        ],
        next_question_for_user=None,
    )

    # ─── 4. ASSEMBLE SESSION ───
    session = SessionState(
        session_id=session_id,
        user_phone=None,
        active_agent=AgentType.DRAFTING,
        triage=triage,
        legal=legal,
        shelter=shelter,
        drafting=None,  # Drafting agent will initialize this
    )

    return session


# ── Pretty-print helpers ───────────────────────────────────────────

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[96m"
DIM = "\033[2m"


def print_banner():
    print(f"""
{BOLD}{'='*65}
  ⚖️  SAHAYAK — Offline Agent Pipeline Test
  Tests: Triage ✅ → Legal ✅ → Shelter ✅ → Drafting (LIVE)
  Mode:  No LLM / No Redis / No Supabase
{'='*65}{RESET}
""")


def print_section(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}{RESET}\n")


def print_agent_state(label: str, state_dict: dict, highlights: list[str] = None):
    """Print a subset of agent state fields nicely."""
    print(f"  {BOLD}{label}{RESET}")
    for key, val in state_dict.items():
        if highlights and key in highlights:
            print(f"    {GREEN}✔ {key}: {val}{RESET}")
        else:
            val_str = str(val)
            if len(val_str) > 120:
                val_str = val_str[:120] + "..."
            print(f"    {DIM}{key}: {val_str}{RESET}")
    print()


# ── Main ───────────────────────────────────────────────────────────

async def main():
    print_banner()

    # ── Step 1: Build the pre-filled session ──
    print_section("STEP 1 — Building Mock Session State")

    session = build_mock_session()
    memory = MockMemoryManager(session.session_id)

    # Show Triage summary
    print_agent_state(
        "🔍 TRIAGE AGENT — Completed",
        {
            "status": session.triage.workflow_status.value,
            "category": session.triage.category.value,
            "urgency": f"{session.triage.urgency_level}/5",
            "victim": session.triage.victim_name,
            "aggressor": session.triage.aggressor_name,
            "address": session.triage.property_address,
            "summary": session.triage.incident_summary,
            "needs_shelter": session.triage.needs_immediate_shelter,
            "needs_legal": session.triage.needs_legal_action,
        },
        highlights=["status", "needs_shelter", "needs_legal"],
    )

    # Show Legal summary
    drafts_summary = ", ".join(d.draft_type.value for d in session.legal.drafts_to_generate)
    print_agent_state(
        "📜 LEGAL AGENT — Ready to Draft",
        {
            "status": session.legal.workflow_status.value,
            "ocr_data": session.legal.extracted_doc_data,
            "rag_context": session.legal.retrieved_legal_context,
            "consent_police": session.legal.user_consent_police,
            "drafts_queued": f"{len(session.legal.drafts_to_generate)} → [{drafts_summary}]",
        },
        highlights=["status", "drafts_queued", "consent_police"],
    )

    # Show Shelter summary
    shelters_summary = " | ".join(
        f"{s.name} ({s.distance_km}km)" for s in session.shelter.matched_shelters
    )
    print_agent_state(
        "🏠 SHELTER AGENT — Completed",
        {
            "status": session.shelter.workflow_status.value,
            "location": session.shelter.user_location_text,
            "preferences": session.shelter.user_preferences,
            "consent_to_share": session.shelter.user_consent_to_share,
            "matched_shelters": shelters_summary,
            "selected_ids": session.shelter.selected_shelter_ids,
        },
        highlights=["status", "consent_to_share"],
    )

    # ── Step 2: Run the Drafting Agent ──
    print_section("STEP 2 — Running Drafting Agent (PDF Generation)")

    drafting_agent = DraftingAgent()

    print(f"  {YELLOW}⏳ Rendering templates → PDF via WeasyPrint...{RESET}\n")

    try:
        response = await drafting_agent.process_turn(
            session=session,
            memory_manager=memory,
            user_message=None,
        )
    except Exception as e:
        print(f"  {RED}❌ Drafting Agent crashed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return

    # ── Step 3: Show results ──
    print_section("STEP 3 — Results")

    # Drafting state
    drafting = session.drafting
    print(f"  {BOLD}Drafting Status:{RESET} {drafting.workflow_status.value}")
    print(f"  {BOLD}Documents Generated:{RESET} {len(drafting.generated_drafts)}")
    print(f"  {BOLD}Errors:{RESET} {len(drafting.errors)}")

    if drafting.errors:
        for err in drafting.errors:
            print(f"    {RED}⚠ {err}{RESET}")

    print()

    if drafting.generated_drafts:
        print(f"  {GREEN}{BOLD}✅ Generated Documents:{RESET}\n")
        for i, draft in enumerate(drafting.generated_drafts, 1):
            # Resolve full path
            full_path = os.path.join("/tmp/sahayak_drafts", session.session_id, draft.filename)
            file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            size_kb = f"{file_size / 1024:.1f} KB"

            print(f"    {BOLD}{i}. {draft.title}{RESET}")
            print(f"       Type:     {draft.draft_type}")
            print(f"       Filename: {draft.filename}")
            print(f"       Size:     {size_kb}")
            print(f"       Path:     {GREEN}{full_path}{RESET}")
            print(f"       API URL:  {draft.download_url}")
            print()

    # ── Step 4: Agent reply ──
    print_section("STEP 4 — Agent Reply to User")
    print(f"  {CYAN}{response.reply_message}{RESET}")
    print(f"\n  Action:     {response.action_type.value}")
    print(f"  Next Agent: {response.next_active_agent.value if response.next_active_agent else 'None'}")

    # ── Step 5: Final session JSON ──
    print_section("STEP 5 — Final Session State (JSON)")
    # Print a compact version (exclude large text fields)
    import json
    state_dict = session.model_dump()
    # Truncate long text fields for readability
    if state_dict.get("legal", {}).get("extracted_doc_data"):
        state_dict["legal"]["extracted_doc_data"] = state_dict["legal"]["extracted_doc_data"][:80] + "..."
    if state_dict.get("legal", {}).get("retrieved_legal_context"):
        state_dict["legal"]["retrieved_legal_context"] = state_dict["legal"]["retrieved_legal_context"][:80] + "..."
    for d in state_dict.get("legal", {}).get("drafts_to_generate", []):
        if d.get("draft_body_summary"):
            d["draft_body_summary"] = d["draft_body_summary"][:80] + "..."

    print(json.dumps(state_dict, indent=2, default=str))

    # ── Summary ──
    output_dir = os.path.join("/tmp/sahayak_drafts", session.session_id)
    print(f"""
{BOLD}{'='*65}
  ✅ TEST COMPLETE
  
  PDFs saved to: {output_dir}
  Open them with: xdg-open {output_dir}/*.pdf
{'='*65}{RESET}
""")


if __name__ == "__main__":
    asyncio.run(main())
