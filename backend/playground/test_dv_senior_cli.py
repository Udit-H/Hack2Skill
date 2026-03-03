"""
Sahayak Offline Test — DV + Senior Citizen Drafting
-----------------------------------------------------
Tests the Drafting Agent with pre-filled DV and Senior Citizen scenarios.
No API keys needed. Runs the full PDF generation pipeline.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + "/..")

from models.session import SessionState, AgentType
from models.triage import TriageState, TriageWorkflowStatus
from models.legal import LegalAgentState, WorkflowStatus, LegalDraftPayload, DraftType
from models.shelter import ShelterAgentState, ShelterWorkflowStatus, ShelterProfile
from models.enums import CrisisCategory
from agents.drafting_agent import DraftingAgent


def build_dv_session() -> SessionState:
    """Pre-fill a Domestic Violence scenario (Priya vs Vikram)."""
    session = SessionState(
        session_id="test-dv-priya",
        user_phone="+91-9876500001",
        active_agent=AgentType.DRAFTING,
    )

    # Triage: DV crisis
    session.triage = TriageState(
        internal_plan=[
            "User Priya reports physical and emotional DV by husband Vikram",
            "Married 5 years, 1 child (age 3), currently staying at parents' home",
            "Urgency 4 — left house last night after being hit, needs legal protection",
        ],
        workflow_status=TriageWorkflowStatus.COMPLETED,
        category=CrisisCategory.DOMESTIC_VIOLENCE,
        urgency_level=4,
        incident_summary="Priya Sharma, 28, has been facing physical and emotional abuse from her husband Vikram Sharma for 3 years. Last night he hit her and she fled to her parents' home with her 3-year-old daughter.",
        victim_name="Priya Sharma",
        aggressor_name="Vikram Sharma",
        property_address="42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041",
        has_ownership_claim=False,
        is_financially_destitute=True,
        needs_immediate_shelter=False,  # Staying at parents'
        needs_legal_action=True,
    )

    # Legal: Ready to draft DV documents
    session.legal = LegalAgentState(
        internal_plan=[
            "All mandatory DV fields collected: relationship (husband), violence (physical+emotional), 1 child",
            "Marriage date, trusted contact, safe location all available",
            "Generate: SAFETY_PLAN, DIR_FORM_1, SECTION_12_PETITION, KSLSA_LEGAL_AID (destitute)",
        ],
        workflow_status=WorkflowStatus.READY_TO_DRAFT,
        extracted_doc_data=None,
        retrieved_legal_context="DV Act 2005 Section 12, DV Rules 2006 Form I, BNS 85-86 for criminal prosecution",
        next_question_for_user=None,
        user_consent_police=True,
        drafts_to_generate=[
            LegalDraftPayload(
                draft_type=DraftType.SAFETY_PLAN,
                applicant_name="Priya Sharma",
                opponent_name="Vikram Sharma",
                property_address="42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041",
                relationship_to_respondent="Husband",
                violence_types=["physical", "emotional"],
                children_involved=True,
                number_of_children=1,
                marriage_date="15/06/2021",
                immediate_danger=False,
                trusted_contact_name="Sunita Sharma (Mother)",
                trusted_contact_phone="+91-9876500002",
                safe_location="Parents' home, 15 MG Road, Bengaluru",
                draft_body_summary="Safety plan for Priya Sharma fleeing domestic violence. Husband Vikram has history of physical violence (hitting, pushing) and emotional abuse (threats, controlling behaviour). One daughter Ananya (age 3).",
            ),
            LegalDraftPayload(
                draft_type=DraftType.DIR_FORM_1,
                applicant_name="Priya Sharma",
                opponent_name="Vikram Sharma",
                property_address="42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041",
                relationship_to_respondent="Husband",
                violence_types=["physical", "emotional"],
                children_involved=True,
                number_of_children=1,
                marriage_date="15/06/2021",
                immediate_danger=False,
                draft_body_summary="The Respondent Vikram Sharma has been physically and emotionally abusing the Aggrieved Person Priya Sharma since approximately 2023. Physical violence includes slapping, hitting with hands, and pushing. Emotional abuse includes constant belittling, threats of harm, controlling movement and finances, and isolating from family. On the night of 2 March 2026, the Respondent struck the Aggrieved Person on her face causing swelling, after which she fled to her parents' residence with her minor daughter Ananya (age 3).",
            ),
            LegalDraftPayload(
                draft_type=DraftType.SECTION_12_PETITION,
                applicant_name="Priya Sharma",
                opponent_name="Vikram Sharma",
                property_address="42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041",
                relationship_to_respondent="Husband",
                violence_types=["physical", "emotional"],
                children_involved=True,
                number_of_children=1,
                marriage_date="15/06/2021",
                draft_body_summary="The Respondent has subjected the Aggrieved Person to persistent domestic violence as defined under Section 3 of the PWDV Act, 2005, including physical violence (slapping, hitting) and emotional abuse (threats, isolation, financial control). The most recent incident occurred on 2 March 2026 when the Respondent struck the Aggrieved Person, forcing her to flee with the minor child. The Aggrieved Person seeks Protection Order, Residence Order, Monetary Relief, Custody Order, and Compensation.",
            ),
            LegalDraftPayload(
                draft_type=DraftType.KSLSA_LEGAL_AID,
                applicant_name="Priya Sharma",
                opponent_name="Vikram Sharma",
                property_address="42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041",
                monthly_income=0,
                caste_category="Women",
                draft_body_summary="Application for free legal aid under Karnataka State Legal Services Authority. Applicant is a woman facing domestic violence with no independent income. Seeks legal representation for filing DIR and Section 12 petition under the PWDV Act, 2005.",
            ),
        ],
    )

    return session


def build_senior_citizen_session() -> SessionState:
    """Pre-fill a Senior Citizen Neglect scenario (Ramaiah vs Suresh)."""
    session = SessionState(
        session_id="test-senior-ramaiah",
        user_phone="+91-9876500003",
        active_agent=AgentType.DRAFTING,
    )

    # Triage: Senior Citizen crisis
    session.triage = TriageState(
        internal_plan=[
            "User Ramaiah (72) being neglected/evicted by son Suresh from own property",
            "Property IS in Ramaiah's name — Section 23 void transfer available",
            "Urgency 3 — not immediately homeless but son threatening to sell property",
        ],
        workflow_status=TriageWorkflowStatus.COMPLETED,
        category=CrisisCategory.SENIOR_CITIZEN_NEGLECT,
        urgency_level=3,
        incident_summary="K. Ramaiah, 72, retired government employee, being threatened with eviction by son Suresh who wants to sell the family home. Property is registered in Ramaiah's name. Son has stopped providing food and medical care.",
        victim_name="K. Ramaiah",
        aggressor_name="Suresh K.",
        property_address="88, 2nd Main, Rajajinagar 1st Block, Bengaluru 560010",
        has_ownership_claim=True,
        is_financially_destitute=True,
        needs_immediate_shelter=False,
        needs_legal_action=True,
    )

    # Legal: Ready to draft Senior Citizen docs
    session.legal = LegalAgentState(
        internal_plan=[
            "Senior citizen case — property in applicant's name, son threatening to sell",
            "Monthly pension ₹8,000 — qualifies for KSLSA legal aid",
            "Generate: SENIOR_CITIZEN_TRIBUNAL, POLICE_INTIMATION (abandonment S.24), KSLSA_LEGAL_AID",
        ],
        workflow_status=WorkflowStatus.READY_TO_DRAFT,
        extracted_doc_data=None,
        retrieved_legal_context="Maintenance and Welfare of Parents and Senior Citizens Act 2007. Section 5 (Tribunal application), Section 23 (void transfer), Section 24 (abandonment punishment 3 months).",
        next_question_for_user=None,
        user_consent_police=True,
        drafts_to_generate=[
            LegalDraftPayload(
                draft_type=DraftType.SENIOR_CITIZEN_TRIBUNAL,
                applicant_name="K. Ramaiah",
                opponent_name="Suresh K.",
                property_address="88, 2nd Main, Rajajinagar 1st Block, Bengaluru 560010",
                is_property_in_applicant_name=True,
                draft_body_summary="The Respondent Suresh K., being the son of the Applicant, has neglected his duty of maintenance under the Act. He has stopped providing food, withheld medical support, and is threatening to sell the family property at 88, 2nd Main, Rajajinagar despite the property being registered in the Applicant's name. The Applicant, aged 72, survives on a pension of ₹8,000/month and is unable to independently maintain himself or contest property disputes.",
            ),
            LegalDraftPayload(
                draft_type=DraftType.POLICE_INTIMATION,
                applicant_name="K. Ramaiah",
                opponent_name="Suresh K.",
                property_address="88, 2nd Main, Rajajinagar 1st Block, Bengaluru 560010",
                draft_body_summary="Police intimation regarding abandonment of senior citizen under Section 24 of the Maintenance and Welfare of Parents and Senior Citizens Act, 2007. The Respondent Suresh K. has abandoned his father K. Ramaiah (72 years) by withholding food, medical care, and threatening to forcibly sell the family residence. Section 24 provides for imprisonment up to 3 months for abandonment of a senior citizen.",
            ),
            LegalDraftPayload(
                draft_type=DraftType.KSLSA_LEGAL_AID,
                applicant_name="K. Ramaiah",
                opponent_name="Suresh K.",
                property_address="88, 2nd Main, Rajajinagar 1st Block, Bengaluru 560010",
                monthly_income=8000,
                caste_category="General",
                draft_body_summary="Application for free legal aid under KSLSA. Applicant is a 72-year-old senior citizen with monthly pension of ₹8,000 facing neglect and threatened eviction by son. Seeks legal representation for Maintenance Tribunal complaint and property protection.",
            ),
        ],
    )

    return session


async def run_test():
    drafting = DraftingAgent()
    
    scenarios = [
        ("🏠 DOMESTIC VIOLENCE", build_dv_session),
        ("👴 SENIOR CITIZEN NEGLECT", build_senior_citizen_session),
    ]

    for label, builder in scenarios:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        
        session = builder()
        response = await drafting.process_turn(session, memory_manager=None, user_message=None)
        
        print(f"\n📄 Generated {len(session.drafting.generated_drafts)} documents:")
        for d in session.drafting.generated_drafts:
            print(f"  ✅ {d.title}")
            print(f"     → {d.download_url}")
        
        if session.drafting.errors:
            print(f"\n⚠️  Errors: {session.drafting.errors}")
        
        # Show the reply
        print(f"\n💬 Agent Reply:\n{response.reply_message[:500]}")

    # Summary
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    
    # List all generated PDFs
    import glob
    pdfs = glob.glob("/tmp/sahayak_drafts/test-*/**.pdf")
    print(f"\n📁 Total PDFs on disk: {len(pdfs)}")
    for pdf in sorted(pdfs):
        size = os.path.getsize(pdf)
        print(f"  📄 {os.path.basename(pdf)} ({size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(run_test())
