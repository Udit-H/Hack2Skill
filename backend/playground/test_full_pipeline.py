"""
Sahayak — Full Pipeline CLI Test (No API Key Required)
-------------------------------------------------------
Tests the COMPLETE agent pipeline offline:
  1. TRIAGE AGENT   — Pre-filled with user's eviction scenario
  2. LEGAL AGENT    — Pre-filled as if LLM collected all info → ready to draft
  3. SHELTER AGENT  — Pre-filled as if user selected a shelter
  4. DRAFTING AGENT — LIVE execution (WeasyPrint PDF generation)

Also demonstrates pypdf inspection of the DIR form.

Usage:
    cd backend
    python playground/test_full_pipeline.py
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

msys_path = r"C:\msys64\ucrt64\bin"
if os.path.exists(msys_path):
    os.add_dll_directory(msys_path)
    print(f"✅ DLL directory added: {msys_path}")
else:
    print(f"❌ Error: {msys_path} not found. Re-check MSYS2 installation.")

# Now you can import weasyprint
try:
    import weasyprint
    print("🚀 WeasyPrint imported successfully!")
except Exception as e:
    print(f"❌ Still failing: {e}")

from models.session import SessionState, AgentType, AgentResponse, AgentActionType
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


# ── Colors ─────────────────────────────────────────────────────────
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[96m"
DIM = "\033[2m"
MAGENTA = "\033[95m"


def hr(char="─", width=65):
    return f"{char * width}"


def banner(text, emoji=""):
    print(f"\n{BOLD}{CYAN}{hr('═')}")
    print(f"  {emoji}  {text}")
    print(f"{hr('═')}{RESET}\n")


def section(text, emoji="📌"):
    print(f"\n{BOLD}{MAGENTA}{hr()}")
    print(f"  {emoji} {text}")
    print(f"{hr()}{RESET}\n")


def kv(key, val, indent=4, highlight=False):
    """Print a key-value pair."""
    pad = " " * indent
    val_str = str(val)
    if len(val_str) > 140:
        val_str = val_str[:140] + "…"
    if highlight:
        print(f"{pad}{GREEN}✔ {key}: {val_str}{RESET}")
    else:
        print(f"{pad}{DIM}{key}: {val_str}{RESET}")


# ── Fake Memory Manager ───────────────────────────────────────────
class MockMemoryManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._history = []

    def get_memory_context(self) -> str:
        hist = "\n".join(self._history[-10:]) if self._history else "No history yet."
        return f"<long_term_summary>Offline test session.</long_term_summary>\n<recent_chat_history>\n{hist}\n</recent_chat_history>"

    def add_turn(self, user_message: str, ai_message: str):
        self._history.append(f"User: {user_message}")
        self._history.append(f"AI: {ai_message}")


# ══════════════════════════════════════════════════════════════════
#  PHASE 1: TRIAGE AGENT SIMULATION
# ══════════════════════════════════════════════════════════════════

def simulate_triage() -> TriageState:
    """
    Simulates what the Triage Agent would produce after the user says:
    "hello, ive been unlawfully evicted from my house. i am renting it.
     Udit H is the owner my name is Rohith and the address is 405 Sobha
     Palladian, Yemlur, Bengaluru. The reason is because the owner thought
     i was making too much noise when in fact i only made loud music once
     a week for 30 min."
    """
    section("PHASE 1 — TRIAGE AGENT (Simulated)", "🔍")

    print(f"    {YELLOW}User Message:{RESET}")
    print(f'    "Hello, I\'ve been unlawfully evicted from my house. I am renting it.')
    print(f'     Udit H is the owner, my name is Rohith and the address is')
    print(f'     405 Sobha Palladian, Yemlur, Bengaluru. The reason is because the')
    print(f'     owner thought I was making too much noise when in fact I only made')
    print(f'     loud music once a week for 30 min."\n')

    triage = TriageState(
        workflow_status=TriageWorkflowStatus.COMPLETED,
        category=CrisisCategory.ILLEGAL_EVICTION,
        urgency_level=3,
        incident_summary=(
            "Rohith, a tenant at 405 Sobha Palladian, Yemlur, Bengaluru, has been "
            "illegally evicted by landlord Udit H. The landlord claims excessive noise "
            "as the reason, but the tenant only played loud music once a week for 30 minutes. "
            "No legal eviction notice was served."
        ),
        victim_name="Rohith",
        aggressor_name="Udit H",
        property_address="405 Sobha Palladian, Yemlur, Bengaluru",
        eviction_reason="Landlord claims tenant was making too much noise. Tenant states they only played loud music once a week for 30 minutes.",
        has_ownership_claim=False,
        is_financially_destitute=True,
        needs_immediate_shelter=True,
        needs_legal_action=True,
        next_question_for_user=None,
    )

    # Display what Triage Agent extracted
    print(f"    {GREEN}Triage Agent Output:{RESET}")
    kv("Status", triage.workflow_status.value, highlight=True)
    kv("Category", triage.category.value)
    kv("Urgency", f"{triage.urgency_level}/5")
    kv("Victim", triage.victim_name)
    kv("Aggressor", triage.aggressor_name)
    kv("Address", triage.property_address)
    kv("Eviction Reason", triage.eviction_reason)
    kv("Summary", triage.incident_summary)
    kv("Needs Shelter", triage.needs_immediate_shelter, highlight=True)
    kv("Needs Legal Action", triage.needs_legal_action, highlight=True)

    # Simulated agent reply
    reply = (
        "Thank you for sharing, Rohith. I understand you've been illegally evicted from your rented home. "
        "Let me coordinate the next steps — I'll help you find emergency shelter and prepare legal documents "
        "to protect your rights."
    )
    print(f"\n    {CYAN}Triage Agent Reply:{RESET}")
    print(f"    \"{reply}\"\n")
    print(f"    {YELLOW}→ Handoff: TRIAGE → ORCHESTRATOR → SHELTER{RESET}")

    return triage


# ══════════════════════════════════════════════════════════════════
#  PHASE 2: SHELTER AGENT SIMULATION
# ══════════════════════════════════════════════════════════════════

def simulate_shelter() -> ShelterAgentState:
    """
    Simulates the Shelter Agent conversation:
    - Asks for location → gets "Yemlur, Bengaluru"
    - Asks for preferences → gets "Any safe place"
    - Runs DB search (mocked) → shows 3 shelters
    - User selects shelter 1
    - Asks for consent → user says yes
    """
    section("PHASE 2 — SHELTER AGENT (Simulated)", "🏠")

    # Turn 1: Ask location
    print(f"    {CYAN}Shelter Agent:{RESET} I understand you need safe shelter right now.")
    print(f"    Could you share your current area or nearest landmark so I can find options close to you?\n")
    print(f"    {YELLOW}User:{RESET} I'm near Yemlur, Bengaluru\n")

    # Turn 2: Ask preferences
    print(f"    {CYAN}Shelter Agent:{RESET} Got it — Yemlur area. Do you have any preferences?")
    print(f"    For example: men-only shelter, family-friendly, pet-friendly?\n")
    print(f"    {YELLOW}User:{RESET} Any safe place is fine\n")

    # Turn 3: Show results (mocked DB search)
    print(f"    {DIM}[SYSTEM] DB search: lat=12.9569, lng=77.6690, radius=5km → 3 results{RESET}")
    print(f"    {DIM}[SYSTEM] Fallback 15km search not needed{RESET}\n")

    shelters = [
        ShelterProfile(
            shelter_id=101,
            name="Bengaluru Urban Night Shelter — Indiranagar",
            shelter_type="Government Night Shelter",
            address="100 Feet Road, Indiranagar, Bengaluru 560038",
            contact_number="080-2529-1100",
            distance_km=2.8,
            google_maps_url="https://maps.google.com/?q=12.9716,77.6412",
        ),
        ShelterProfile(
            shelter_id=102,
            name="Don Bosco Emergency Shelter",
            shelter_type="NGO Shelter (Men)",
            address="Museum Road, Bengaluru 560001",
            contact_number="080-2558-4304",
            distance_km=5.1,
            google_maps_url="https://maps.google.com/?q=12.9756,77.6060",
        ),
        ShelterProfile(
            shelter_id=103,
            name="Missionaries of Charity — Men's Home",
            shelter_type="Faith-based Shelter",
            address="Ulsoor, Bengaluru 560008",
            contact_number="080-2556-7890",
            distance_km=3.6,
            google_maps_url="https://maps.google.com/?q=12.9810,77.6230",
        ),
    ]

    print(f"    {CYAN}Shelter Agent:{RESET} I found 3 shelters near you:\n")
    for i, s in enumerate(shelters, 1):
        print(f"      {BOLD}{i}. {s.name}{RESET}")
        print(f"         Type: {s.shelter_type} | Distance: {s.distance_km}km")
        print(f"         Address: {s.address}")
        print(f"         Phone: {s.contact_number}")
        print(f"         Map: {s.google_maps_url}\n")

    print(f"    Which one would you prefer?\n")
    print(f"    {YELLOW}User:{RESET} The first one — Indiranagar shelter\n")

    # Turn 4: Ask consent
    print(f"    {CYAN}Shelter Agent:{RESET} Great choice. To reserve a spot, I'll need to share your name")
    print(f"    and basic details with the shelter. May I have your permission to do this?\n")
    print(f"    {YELLOW}User:{RESET} Yes, go ahead\n")

    state = ShelterAgentState(
        workflow_status=ShelterWorkflowStatus.COMPLETED,
        user_location_text="Yemlur, Bengaluru",
        user_coordinates={"lat": 12.9569, "lng": 77.6690},
        user_preferences="Any safe place",
        user_consent_to_share=True,
        free_shelter_needed=True,
        selected_shelter_ids=[101],
        matched_shelters=shelters,
        next_question_for_user=None,
    )

    print(f"    {GREEN}Shelter Agent Output:{RESET}")
    kv("Status", state.workflow_status.value, highlight=True)
    kv("Location", state.user_location_text)
    kv("Consent", state.user_consent_to_share, highlight=True)
    kv("Selected", f"#{state.selected_shelter_ids[0]} — {shelters[0].name}")
    print(f"\n    {YELLOW}→ Handoff: SHELTER → ORCHESTRATOR → LEGAL{RESET}")

    return state


# ══════════════════════════════════════════════════════════════════
#  PHASE 3: LEGAL AGENT SIMULATION
# ══════════════════════════════════════════════════════════════════

def simulate_legal() -> LegalAgentState:
    """
    Simulates the Legal Agent conversation for Rohith's eviction case:
    - Asks for documents → user uploads rent agreement (mocked OCR)
    - Collects additional details
    - Asks for consent for police intimation
    - Reaches READY_TO_DRAFT with 3 legal documents queued
    """
    section("PHASE 3 — LEGAL AGENT (Simulated)", "📜")

    # Turn 1: Ask for documents
    print(f"    {CYAN}Legal Agent:{RESET} I'm now going to help you prepare the legal documents to")
    print(f"    fight this unlawful eviction. First, could you upload your rent agreement")
    print(f"    or any proof of tenancy?\n")
    print(f"    {YELLOW}User:{RESET} 📎 Uploaded: rent_agreement_rohith.pdf\n")

    # OCR Result (mocked)
    ocr_text = (
        "RESIDENTIAL RENTAL AGREEMENT\n"
        "This Agreement is made on 1st June 2025 between:\n"
        "LANDLORD: Mr. Udit H, residing at HSR Layout, Bengaluru\n"
        "TENANT: Mr. Rohith, employed at a private firm\n"
        "PREMISES: Flat No. 405, Sobha Palladian, Yemlur, Bengaluru 560037\n"
        "RENT: ₹22,000/- per month, payable by 5th of each month\n"
        "SECURITY DEPOSIT: ₹1,10,000/- (One Lakh Ten Thousand)\n"
        "LOCK-IN PERIOD: 11 months from date of agreement\n"
        "NOTICE PERIOD: Either party shall give 2 months written notice.\n"
        "MAINTENANCE: ₹3,500/- per month (included in rent)\n"
        "WITNESSES: 1. Ajay Kumar  2. Priya Sharma"
    )
    print(f"    {DIM}[OCR] Extracted {len(ocr_text)} chars from document{RESET}")
    print(f"    {DIM}[RAG] Retrieved Karnataka Rent Control Act context{RESET}\n")

    rag_context = (
        "Karnataka Rent Act, 1999 — Section 27: No landlord shall cut off or withhold any essential "
        "supply or service. Section 106 Transfer of Property Act: Termination of lease requires 15 days "
        "notice for monthly tenancy. BNS Section 126(2): Wrongful restraint is punishable. CPC Order "
        "XXXIX Rules 1 & 2: Court may grant temporary injunction to prevent dispossession."
    )

    # Turn 2: Additional info
    print(f"    {CYAN}Legal Agent:{RESET} I've extracted the details from your rent agreement.")
    print(f"    Your rent is ₹22,000/month with a lock-in period still active.")
    print(f"    The landlord was required to give 2 months written notice — which was not done.\n")
    print(f"    Can you tell me: were you physically present when the locks were changed,")
    print(f"    or did you find out when you returned?\n")
    print(f"    {YELLOW}User:{RESET} I found out when I came back from work. My stuff is still inside.\n")

    # Turn 3: Ask consent
    print(f"    {CYAN}Legal Agent:{RESET} Based on what you've told me, I can prepare three documents:")
    print(f"      1. 🚔 Police Intimation — reporting wrongful restraint (BNS 126)")
    print(f"      2. ⚖️ Civil Injunction Petition — to restrain the landlord from evicting you")
    print(f"      3. 📋 KSLSA Legal Aid Application — for free legal assistance\n")
    print(f"    Filing a police intimation may escalate things with your landlord.")
    print(f"    Do I have your explicit permission to draft the police complaint?\n")
    print(f"    {YELLOW}User:{RESET} Yes, please draft everything. I want all three.\n")

    legal = LegalAgentState(
        workflow_status=LegalWorkflowStatus.READY_TO_DRAFT,
        extracted_doc_data=ocr_text,
        retrieved_legal_context=rag_context,
        next_question_for_user=None,
        user_consent_police=True,
        drafts_to_generate=[
            LegalDraftPayload(
                draft_type=DraftType.POLICE_INTIMATION,
                applicant_name="Rohith",
                opponent_name="Udit H",
                property_address="Flat 405, Sobha Palladian, Yemlur, Bengaluru 560037",
                monthly_income=0,  # financially destitute
                caste_category="General",
                draft_body_summary=(
                    "On 2 March 2026, the landlord Mr. Udit H changed the locks of Flat 405, "
                    "Sobha Palladian, Yemlur, Bengaluru while the tenant Rohith was at his workplace. "
                    "Upon returning in the evening, Rohith found himself locked out with all personal "
                    "belongings still inside the flat. The landlord claims the eviction is due to noise "
                    "complaints, however the tenant only played music once a week for 30 minutes. "
                    "No written eviction notice was served as required under the Karnataka Rent Act, 1999. "
                    "The rent agreement (dated 1 June 2025) has a valid 11-month lock-in period and requires "
                    "2 months written notice for termination. The landlord's action constitutes wrongful "
                    "restraint under BNS Section 126(2) and criminal intimidation."
                ),
            ),
            LegalDraftPayload(
                draft_type=DraftType.CIVIL_INJUNCTION_PETITION,
                applicant_name="Rohith",
                opponent_name="Udit H",
                property_address="Flat 405, Sobha Palladian, Yemlur, Bengaluru 560037",
                monthly_income=0,
                caste_category="General",
                draft_body_summary=(
                    "That on 2 March 2026, the Respondent/Landlord Mr. Udit H, without following due "
                    "process of law and without serving any written notice as mandated under Section 106 "
                    "of the Transfer of Property Act, 1882, forcibly locked out the Applicant from the "
                    "rented premises at Flat 405, Sobha Palladian, Yemlur, Bengaluru by changing the door "
                    "locks while the Applicant was at work. The Applicant's personal belongings, clothing, "
                    "documents, and electronic devices remain trapped inside the flat. The rent agreement "
                    "dated 1 June 2025 stipulates an 11-month lock-in period and a 2-month notice requirement, "
                    "neither of which was honoured by the Respondent."
                ),
            ),
            LegalDraftPayload(
                draft_type=DraftType.KSLSA_LEGAL_AID,
                applicant_name="Rohith",
                opponent_name="Udit H",
                property_address="Flat 405, Sobha Palladian, Yemlur, Bengaluru 560037",
                monthly_income=0,
                caste_category="General",
                draft_body_summary=(
                    "Application for free legal aid under Section 12 of the Legal Services Authorities "
                    "Act, 1987. The applicant Rohith has been illegally evicted from his rented premises "
                    "by landlord Udit H without due process. The applicant is financially destitute and "
                    "unable to afford private legal counsel. He seeks KSLSA assistance for: (1) filing a "
                    "civil suit for temporary injunction and recovery of possession under CPC Order XXXIX, "
                    "(2) recovery of security deposit of ₹1,10,000, and (3) legal representation for "
                    "criminal complaint under BNS Section 126."
                ),
            ),
        ],
    )

    print(f"    {GREEN}Legal Agent Output:{RESET}")
    kv("Status", legal.workflow_status.value, highlight=True)
    kv("OCR Data", f"{len(legal.extracted_doc_data)} chars extracted")
    kv("RAG Context", f"{len(legal.retrieved_legal_context)} chars retrieved")
    kv("Police Consent", legal.user_consent_police, highlight=True)
    kv("Drafts Queued", f"{len(legal.drafts_to_generate)} documents:", highlight=True)
    for i, d in enumerate(legal.drafts_to_generate, 1):
        kv(f"  [{i}]", f"{d.draft_type.value} → {d.applicant_name} vs {d.opponent_name}", indent=6)
    print(f"\n    {YELLOW}→ Handoff: LEGAL → ORCHESTRATOR → DRAFTING{RESET}")

    return legal


# ══════════════════════════════════════════════════════════════════
#  PHASE 4: DRAFTING AGENT (LIVE EXECUTION)
# ══════════════════════════════════════════════════════════════════

async def run_drafting_agent(session: SessionState, memory: MockMemoryManager) -> AgentResponse:
    """
    Actually runs the DraftingAgent to generate real PDFs.
    """
    section("PHASE 4 — DRAFTING AGENT (LIVE PDF Generation)", "📄")

    drafting_agent = DraftingAgent()
    print(f"    {YELLOW}⏳ Rendering Jinja2 templates → WeasyPrint → PDF...{RESET}\n")

    response = await drafting_agent.process_turn(
        session=session,
        memory_manager=memory,
        user_message=None,
    )

    drafting = session.drafting

    print(f"    {GREEN}Drafting Agent Output:{RESET}")
    kv("Status", drafting.workflow_status.value, highlight=True)
    kv("Generated", f"{len(drafting.generated_drafts)} documents")
    kv("Errors", f"{len(drafting.errors)} errors")

    if drafting.errors:
        for err in drafting.errors:
            print(f"      {RED}⚠ {err}{RESET}")

    if drafting.generated_drafts:
        print(f"\n    {GREEN}{BOLD}Generated PDFs:{RESET}\n")
        for i, draft in enumerate(drafting.generated_drafts, 1):
            full_path = os.path.join("/tmp/sahayak_drafts", session.session_id, draft.filename)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            print(f"      {BOLD}{i}. {draft.title}{RESET}")
            print(f"         File:  {draft.filename}")
            print(f"         Size:  {size/1024:.1f} KB")
            print(f"         Path:  {GREEN}{full_path}{RESET}")
            print()

    return response


# ══════════════════════════════════════════════════════════════════
#  PHASE 5: DIR PDF INSPECTION (pypdf)
# ══════════════════════════════════════════════════════════════════

def inspect_dir_pdf():
    """Check the Domestic Incident Report PDF structure with pypdf."""
    section("BONUS — DIR PDF Inspection (pypdf)", "🔬")

    dir_path = os.path.join(os.path.dirname(__file__), "..", "database", "domestic-incident-report-form.pdf")

    if not os.path.exists(dir_path):
        print(f"    {RED}DIR PDF not found at {dir_path}{RESET}")
        return

    import pypdf
    reader = pypdf.PdfReader(dir_path)

    print(f"    File:   domestic-incident-report-form.pdf")
    print(f"    Pages:  {len(reader.pages)}")

    fields = reader.get_fields()
    print(f"    Fillable Form Fields: {len(fields) if fields else 0}")

    if not fields:
        print(f"\n    {YELLOW}⚠ This PDF has NO fillable form fields — it's a flat/scanned document.{RESET}")
        print(f"    {DIM}To make it fillable, you'd need to either:{RESET}")
        print(f"    {DIM}  1. Recreate it as a fillable PDF using Adobe Acrobat / LibreOffice{RESET}")
        print(f"    {DIM}  2. Generate it from your Jinja2 HTML template (recommended){RESET}")
        print(f"    {DIM}  3. Use pypdf to overlay text on specific coordinates (hacky){RESET}")
    else:
        print(f"\n    {GREEN}✔ Found {len(fields)} fillable fields:{RESET}")
        for k, v in list(fields.items())[:20]:
            ft = v.get('/FT', '?')
            print(f"      {k}: type={ft}")

    # Show structure summary
    print(f"\n    {DIM}DIR Form Structure (7 pages):{RESET}")
    print(f"    {DIM}  Page 1: Complainant details, Respondent details, Children details{RESET}")
    print(f"    {DIM}  Page 2-4: Incidents of violence (Physical, Sexual, Verbal, Economic, Dowry){RESET}")
    print(f"    {DIM}  Page 5: Additional info, Document list, Orders requested{RESET}")
    print(f"    {DIM}  Page 6-7: Assistance needed, Instructions for police{RESET}")


# ══════════════════════════════════════════════════════════════════
#  NALSA/LSAMS FORM ANALYSIS
# ══════════════════════════════════════════════════════════════════

def report_lsams_findings():
    """Report findings about the NALSA LSAMS portal and fillable PDFs."""
    section("RESEARCH — NALSA LSAMS & Fillable PDFs for Eviction", "🔎")

    print(f"""    {BOLD}NALSA Legal Aid Portal (scourtapp.nic.in/lsams){RESET}
    {DIM}────────────────────────────────────────────────{RESET}
    The LSAMS portal is a {YELLOW}web-only form{RESET} — there is no downloadable fillable PDF.
    Categories available (from the dropdown):
      • Civic amenities / Quality of service / Compensations / Refunds
      • Counselling and Conciliation
      • Delay in decision / implementation of decision
      • Law & Order
      • {GREEN}Legal Advice{RESET}               ← Relevant for eviction
      • {GREEN}Legal Redress{RESET}              ← Relevant for eviction
      • Panel Lawyer for defending court case
      • {GREEN}Panel Lawyer for filing new case{RESET}  ← Relevant for eviction
      • Requests
      • Retirement dues
      • {GREEN}Revenue / Land / Tax{RESET}        ← Could be relevant
      • Scheduled Castes / STs / Backward Service matters
      • Social Evils
      • State Govt: Miscellaneous
      • {GREEN}To Draft an Application / Representation / Notice / Petition / Reply{RESET}  ← Most relevant!

    {BOLD}Relevant categories for eviction:{RESET}
      ✔ "Legal Redress" — for seeking court intervention against illegal eviction
      ✔ "Panel Lawyer for filing new case" — for civil suit filing
      ✔ "To Draft an Application/Notice/Petition/Reply" — for document preparation

    {BOLD}Fillable PDF Research Results:{RESET}
    {DIM}────────────────────────────────────────────────{RESET}
    ❌ Civil Injunction Petition    — No standard form. Free-form petition on plain paper.
    ❌ Police Complaint / FIR       — Citizen gives written complaint; FIR is police-internal.
    ❌ NALSA Legal Aid Application  — Web portal only (scourtapp.nic.in), or paper at DLSA office.
    ❌ Karnataka Rent Tribunal Form — No statutory form. Application on plain paper.
    ❌ Karnataka Rent Act Form      — No forms prescribed in the Act's schedule.

    {BOLD}{GREEN}Conclusion:{RESET}
    India's legal system uses free-form petitions, not standardized fillable PDFs.
    Your Jinja2 → WeasyPrint approach is actually {GREEN}better than what exists{RESET} —
    you're generating properly formatted legal documents that citizens would
    otherwise need a lawyer to draft.

    The ONLY fillable PDF you have is the DIR form — but it's flat/scanned,
    so you'd need to recreate it as an HTML template (which you already did
    with section_12_petition.html.j2).
""")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

async def main():
    banner("SAHAYAK — Full Agent Pipeline Test", "⚖️")
    print(f"    Scenario: Rohith evicted by Udit H from 405 Sobha Palladian, Yemlur")
    print(f"    Mode:     Offline (no LLM / Redis / Supabase)")
    print(f"    Time:     {datetime.now().strftime('%d %b %Y, %H:%M')}")
    print(f"    Pipeline: Triage → Shelter → Legal → Drafting (live)\n")

    session_id = "test-rohith-eviction-001"
    memory = MockMemoryManager(session_id)

    # ── Phase 1: Triage ──
    triage = simulate_triage()

    # ── Phase 2: Shelter ──
    shelter = simulate_shelter()

    # ── Phase 3: Legal ──
    legal = simulate_legal()

    # ── Assemble Session ──
    session = SessionState(
        session_id=session_id,
        user_phone=None,
        active_agent=AgentType.DRAFTING,
        triage=triage,
        legal=legal,
        shelter=shelter,
        drafting=None,
    )

    # ── Phase 4: Drafting (LIVE) ──
    try:
        response = await run_drafting_agent(session, memory)
    except Exception as e:
        print(f"\n    {RED}❌ Drafting failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return

    # ── Phase 5: DIR PDF Inspection ──
    inspect_dir_pdf()

    # ── Phase 6: LSAMS Research ──
    report_lsams_findings()

    # ── Final Summary ──
    banner("PIPELINE COMPLETE", "✅")

    output_dir = os.path.join("/tmp/sahayak_drafts", session_id)
    drafting = session.drafting

    print(f"    {BOLD}Session ID:{RESET}  {session_id}")
    print(f"    {BOLD}Agents Run:{RESET}  Triage ✔ → Shelter ✔ → Legal ✔ → Drafting ✔")
    print(f"    {BOLD}PDFs:{RESET}        {len(drafting.generated_drafts)} generated, {len(drafting.errors)} errors")
    print(f"    {BOLD}Output Dir:{RESET}  {output_dir}")
    print()

    if drafting.generated_drafts:
        print(f"    📄 Documents:")
        for d in drafting.generated_drafts:
            full_path = os.path.join(output_dir, d.filename)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            print(f"       • {d.title} ({size/1024:.1f} KB)")

    print(f"\n    {BOLD}Open PDFs:{RESET}")
    print(f"    xdg-open {output_dir}")
    print(f"\n    {BOLD}Agent's Final Reply:{RESET}")
    print(f"    {CYAN}{response.reply_message[:200]}...{RESET}" if len(response.reply_message) > 200 else f"    {CYAN}{response.reply_message}{RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
