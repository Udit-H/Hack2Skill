"""
Sahayak Form Drafting Agent
----------------------------
Generates legal PDFs from data collected by Legal/Shelter agents.
Hybrid approach: WeasyPrint for legal drafts, pypdf for official forms.
"""

import os
import logging
from datetime import datetime
from typing import Optional

import jinja2
from weasyprint import HTML

from models.session import SessionState, AgentResponse, AgentActionType, AgentType
from models.legal import DraftType, LegalDraftPayload
from models.drafting import DraftingAgentState, DraftingWorkflowStatus, GeneratedDraft

logging.basicConfig(level=logging.INFO)

# Map DraftType → Jinja2 HTML template filename
TEMPLATE_MAP = {
    # Eviction
    DraftType.POLICE_INTIMATION: "police_initimation.html.j2",  # existing template (note typo kept)
    DraftType.CIVIL_INJUNCTION_PETITION: "civil_injunction_petition.html.j2",
    DraftType.INTERIM_RELIEF_APPLICATION: "interim_relief_application.html.j2",
    # Domestic Violence
    DraftType.DIR_FORM_1: "dir_form_1.html.j2",                # Placeholder — will use pypdf later
    DraftType.SECTION_12_PETITION: "section_12_petition.html.j2",
    # Shelter
    DraftType.SHELTER_REFERRAL: "shelter_referral.html.j2",
    DraftType.BBMP_SHELTER_REQUEST: "bbmp_shelter_request.html.j2",
    DraftType.NGO_REFERRAL: "ngo_referral.html.j2",
    # Senior Citizen
    DraftType.SENIOR_CITIZEN_TRIBUNAL: "senior_citizen_tribunal.html.j2",
    # Legal Aid
    DraftType.KSLSA_LEGAL_AID: "kslsa_legal_aid.html.j2",
}

# Human-readable titles for each draft type
DRAFT_TITLES = {
    DraftType.POLICE_INTIMATION: "Police Complaint (BNS 126)",
    DraftType.CIVIL_INJUNCTION_PETITION: "Civil Injunction Petition",
    DraftType.INTERIM_RELIEF_APPLICATION: "Interim Relief Application",
    DraftType.DIR_FORM_1: "Domestic Incident Report (DIR)",
    DraftType.SECTION_12_PETITION: "Section 12 Petition (DV Act)",
    DraftType.SHELTER_REFERRAL: "Shelter Referral Letter",
    DraftType.BBMP_SHELTER_REQUEST: "BBMP Shelter Request",
    DraftType.NGO_REFERRAL: "NGO Referral Letter",
    DraftType.SENIOR_CITIZEN_TRIBUNAL: "Senior Citizen Tribunal Complaint",
    DraftType.KSLSA_LEGAL_AID: "KSLSA Legal Aid Application",
}


class DraftingAgent:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=template_dir)
        )
        self.output_base = "/tmp/sahayak_drafts"

    async def process_turn(
        self,
        session: SessionState,
        memory_manager=None,
        user_message: str = None,
    ) -> AgentResponse:
        """
        Generate all pending PDFs from legal and shelter agent data.
        This agent is non-conversational — it generates everything in one shot.
        """
        # Initialize drafting state
        if not session.drafting:
            session.drafting = DraftingAgentState()

        session.drafting.workflow_status = DraftingWorkflowStatus.GENERATING
        generated = []
        errors = []

        # --- 1. LEGAL DRAFTS ---
        if session.legal and session.legal.drafts_to_generate:
            for payload in session.legal.drafts_to_generate:
                try:
                    draft = await self._render_legal_draft(session, payload)
                    generated.append(draft)
                    logging.info(f"✅ Generated: {draft.title} → {draft.filename}")
                except Exception as e:
                    error_msg = f"Failed to generate {payload.draft_type.value}: {str(e)}"
                    errors.append(error_msg)
                    logging.error(f"❌ {error_msg}")

        # --- 2. SHELTER DRAFTS (if shelter completed with consent) ---
        if session.shelter and session.shelter.user_consent_to_share and session.shelter.matched_shelters:
            try:
                shelter_draft = await self._render_shelter_referral(session)
                generated.append(shelter_draft)
                logging.info(f"✅ Generated: {shelter_draft.title} → {shelter_draft.filename}")
            except Exception as e:
                error_msg = f"Failed to generate shelter referral: {str(e)}"
                errors.append(error_msg)
                logging.error(f"❌ {error_msg}")

        # --- 3. UPDATE STATE ---
        session.drafting.generated_drafts = generated
        session.drafting.errors = errors
        session.drafting.workflow_status = (
            DraftingWorkflowStatus.COMPLETED if generated
            else DraftingWorkflowStatus.FAILED
        )

        # --- 4. BUILD RESPONSE ---
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)

        if generated:
            draft_list = "\n".join([
                f"📄 **{d.title}** — [Download]({d.download_url})"
                for d in generated
            ])
            response.reply_message = (
                f"I've generated {len(generated)} document(s) for you:\n\n"
                f"{draft_list}\n\n"
                "Please review these documents carefully before submitting them. "
                "You can download each one using the links above."
            )
        else:
            response.reply_message = (
                "I wasn't able to generate documents at this time. "
                "Please ensure all required information has been provided."
            )

        if errors:
            response.reply_message += f"\n\n⚠️ {len(errors)} document(s) had errors: {'; '.join(errors)}"

        # Hand off to completed
        response.action_type = AgentActionType.SWITCH_AGENT
        response.next_active_agent = AgentType.COMPLETED

        return response

    # ---------------------------------------------------------------
    # WeasyPrint Rendering
    # ---------------------------------------------------------------

    async def _render_legal_draft(
        self, session: SessionState, payload: LegalDraftPayload
    ) -> GeneratedDraft:
        """Render a single legal draft via Jinja2 → WeasyPrint → PDF."""
        template_file = TEMPLATE_MAP.get(payload.draft_type)
        if not template_file:
            raise ValueError(f"No template for draft type: {payload.draft_type.value}")

        # Build template context from payload + session data
        context = self._build_template_context(session, payload)

        # Render HTML
        template = self.template_env.get_template(template_file)
        html_content = template.render(**context)

        # Generate PDF
        filename = self._make_filename(payload.draft_type, payload.applicant_name)
        output_dir = os.path.join(self.output_base, session.session_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        HTML(string=html_content, base_url=os.path.join(
            os.path.dirname(__file__), '..', 'templates'
        )).write_pdf(output_path)

        return GeneratedDraft(
            draft_type=payload.draft_type.value,
            title=DRAFT_TITLES.get(payload.draft_type, payload.draft_type.value),
            filename=filename,
            download_url=f"/api/drafts/{session.session_id}/{filename}",
        )

    async def _render_shelter_referral(self, session: SessionState) -> GeneratedDraft:
        """Generate a shelter referral letter for the selected shelter."""
        shelter = session.shelter
        selected = shelter.matched_shelters[0] if shelter.matched_shelters else None

        if not selected:
            raise ValueError("No shelter selected for referral")

        context = {
            "date_of_draft": datetime.now().strftime("%d/%m/%Y"),
            "applicant_name": session.triage.victim_name if session.triage else "Applicant",
            "applicant_phone": "",
            "shelter_name": selected.name,
            "shelter_address": selected.address,
            "crisis_category": session.triage.category.value if session.triage and session.triage.category else "",
            "urgency_level": str(session.triage.urgency_level) if session.triage else "High",
            "draft_body_summary": session.triage.incident_summary if session.triage else "",
        }

        template = self.template_env.get_template("shelter_referral.html.j2")
        html_content = template.render(**context)

        filename = self._make_filename(DraftType.SHELTER_REFERRAL, context["applicant_name"])
        output_dir = os.path.join(self.output_base, session.session_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        HTML(string=html_content, base_url=os.path.join(
            os.path.dirname(__file__), '..', 'templates'
        )).write_pdf(output_path)

        return GeneratedDraft(
            draft_type=DraftType.SHELTER_REFERRAL.value,
            title=DRAFT_TITLES[DraftType.SHELTER_REFERRAL],
            filename=filename,
            download_url=f"/api/drafts/{session.session_id}/{filename}",
        )

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _build_template_context(
        self, session: SessionState, payload: LegalDraftPayload
    ) -> dict:
        """Merge payload data + session data into a single template context dict."""
        context = {
            # From payload
            "applicant_name": payload.applicant_name,
            "opponent_name": payload.opponent_name or "",
            "property_address": payload.property_address or "",
            "draft_body_summary": payload.draft_body_summary or "",
            "monthly_income": payload.monthly_income,
            "caste_category": payload.caste_category or "",
            "is_property_in_applicant_name": payload.is_property_in_applicant_name,
            # Generated
            "date_of_draft": datetime.now().strftime("%d/%m/%Y"),
            "place": "Bengaluru",
        }

        # Enrich from triage
        if session.triage:
            context["crisis_category"] = (
                session.triage.category.value if session.triage.category else ""
            )
            context["incident_summary"] = session.triage.incident_summary or ""
            context["urgency_level"] = session.triage.urgency_level

        # Police-specific fields (for police_initimation template)
        if payload.draft_type == DraftType.POLICE_INTIMATION:
            context["police_station_name"] = "Local"
            context["applicant_phone"] = ""

        return context

    def _make_filename(self, draft_type: DraftType, applicant_name: str) -> str:
        """Generate a safe filename like 'police_intimation_john_doe.pdf'."""
        safe_name = "".join(
            c if c.isalnum() else "_" for c in applicant_name.lower()
        ).strip("_")[:30]
        timestamp = datetime.now().strftime("%H%M")
        return f"{draft_type.value}_{safe_name}_{timestamp}.pdf"
