"""
Sahayak Form Drafting Agent
----------------------------
Generates legal PDFs from data collected by Legal/Shelter agents.
Uses fpdf2 (pure Python, zero native deps) for HTML→PDF rendering.
"""

import os
import re
import tempfile
import logging
from datetime import datetime
from typing import Optional

import jinja2

from models.session import SessionState, AgentResponse, AgentActionType, AgentType
from models.legal import DraftType, LegalDraftPayload
from models.drafting import DraftingAgentState, DraftingWorkflowStatus, GeneratedDraft
from services.draft_storage_service import DraftStorageService

logging.basicConfig(level=logging.INFO)

PDF_GENERATION_ERROR_MESSAGE = (
    "PDF generation dependency (fpdf2) is not available. "
    "Install it with: pip install fpdf2"
)

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
    # Safety
    DraftType.SAFETY_PLAN: "safety_plan.html.j2",
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
    DraftType.SAFETY_PLAN: "Personal Safety Plan",
    DraftType.KSLSA_LEGAL_AID: "KSLSA Legal Aid Application",
}


class DraftingAgent:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=template_dir)
        )
        self.output_base = os.path.join(tempfile.gettempdir(), "sahayak_drafts")
        self.draft_storage = DraftStorageService()

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
        # Guard: if already completed OR failed, don't re-generate (prevents infinite loop)
        if session.drafting.workflow_status == DraftingWorkflowStatus.COMPLETED and session.drafting.generated_drafts:
            logging.info("Drafting already completed — skipping re-generation.")
            draft_list = "\n".join([
                f"📄 **{d.title}** — [Download]({d.download_url})"
                for d in session.drafting.generated_drafts
            ])
            return AgentResponse(
                action_type=AgentActionType.SWITCH_AGENT,
                next_active_agent=AgentType.COMPLETED,
                reply_message=f"Your documents are ready:\n\n{draft_list}",
            )
        if session.drafting.workflow_status == DraftingWorkflowStatus.FAILED:
            logging.warning("Drafting previously failed — not retrying.")
            error_summary = "; ".join(session.drafting.errors) if session.drafting.errors else "PDF generation failed"
            return AgentResponse(
                action_type=AgentActionType.SWITCH_AGENT,
                next_active_agent=AgentType.COMPLETED,
                reply_message=f"⚠️ Document generation encountered errors: {error_summary}\n\nPlease try again or contact support.",
            )
        # === CRASH GUARD: wraps entire generation in try/except ===
        # Even if something totally unexpected happens, we ALWAYS set
        # workflow_status to FAILED so the orchestrator never re-enters.
        try:
            return await self._do_generate(session)
        except Exception as exc:
            logging.exception(f"Drafting agent crashed: {exc}")
            session.drafting.workflow_status = DraftingWorkflowStatus.FAILED
            session.drafting.errors = [str(exc)]
            return AgentResponse(
                action_type=AgentActionType.SWITCH_AGENT,
                next_active_agent=AgentType.COMPLETED,
                reply_message=f"⚠️ Document generation failed unexpectedly: {str(exc)}",
            )

    async def _do_generate(self, session: SessionState) -> AgentResponse:
        """Inner generation logic — called by process_turn inside crash guard."""
        session.drafting.workflow_status = DraftingWorkflowStatus.GENERATING
        generated = []
        errors = []

        # Initialize progress tracking
        total_tasks = len(session.legal.drafts_to_generate) if session.legal else 0
        total_tasks += 1 if session.shelter and session.shelter.user_consent_to_share and session.shelter.matched_shelters else 0
        completed_tasks = 0

        progress_status = None

        def update_progress():
            nonlocal progress_status
            if total_tasks > 0:
                progress_status = f"Drafting documents... ({completed_tasks}/{total_tasks})"
            else:
                progress_status = "Drafting documents..."

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
                finally:
                    completed_tasks += 1
                    update_progress()

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
            finally:
                completed_tasks += 1
                update_progress()

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

        response.progress_status = progress_status or "Drafting complete"
        response.is_loading = False
        response.error_message = "; ".join(errors) if errors else None
        response.download_urls = [d.download_url for d in generated] if generated else []

        # Hand off to completed
        response.action_type = AgentActionType.SWITCH_AGENT
        response.next_active_agent = AgentType.COMPLETED

        return response

    # ---------------------------------------------------------------
    # PDF Rendering (fpdf2 — pure Python, zero native deps)
    # ---------------------------------------------------------------

    async def _render_legal_draft(
        self, session: SessionState, payload: LegalDraftPayload
    ) -> GeneratedDraft:
        """Render a single legal draft via Jinja2 → fpdf2 → PDF."""
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

        self._write_pdf(html_content, output_path)

        # Push generated file to S3 (best-effort; local file remains fallback)
        try:
            self.draft_storage.upload_draft(output_path, session.session_id, filename)
        except Exception as exc:
            logging.warning(f"S3 upload failed for {filename}: {exc}")

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
            "applicant_age": session.triage.victim_age if session.triage else "",
            "applicant_phone": session.triage.victim_phone if session.triage else "",
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

        self._write_pdf(html_content, output_path)

        # Push generated file to S3 (best-effort; local file remains fallback)
        try:
            self.draft_storage.upload_draft(output_path, session.session_id, filename)
        except Exception as exc:
            logging.warning(f"S3 upload failed for {filename}: {exc}")

        return GeneratedDraft(
            draft_type=DraftType.SHELTER_REFERRAL.value,
            title=DRAFT_TITLES[DraftType.SHELTER_REFERRAL],
            filename=filename,
            download_url=f"/api/drafts/{session.session_id}/{filename}",
        )

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _sanitize_html(html: str) -> str:
        """Convert Jinja2 HTML output to the subset fpdf2.write_html() supports."""
        # Remove document wrapper tags
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html)
        html = re.sub(r'<head>.*?</head>', '', html, flags=re.DOTALL)
        for tag in ('html', 'body'):
            html = re.sub(rf'</?{tag}[^>]*>', '', html)
        # Semantic tag conversions
        html = html.replace('<strong>', '<b>').replace('</strong>', '</b>')
        html = html.replace('<em>', '<i>').replace('</em>', '</i>')
        # Strip CSS-based attributes (fpdf2 ignores them)
        html = re.sub(r'\s+style="[^"]*"', '', html)
        html = re.sub(r'\s+class="[^"]*"', '', html)
        html = re.sub(r'\s+id="[^"]*"', '', html)
        # Convert divs to paragraphs (fpdf2 understands <p> not <div>)
        html = re.sub(r'<div[^>]*>', '<p>', html)
        html = html.replace('</div>', '</p>')
        # Remove xhtml2pdf-specific page tags
        html = re.sub(r'<pdf:[^>]*/?>\s*', '', html)
        # Unicode → ASCII fallbacks (fpdf2 core fonts are latin-1)
        html = html.replace('\u2014', '--').replace('\u2013', '-')
        html = html.replace('\u2018', "'").replace('\u2019', "'")
        html = html.replace('\u201c', '"').replace('\u201d', '"')
        html = html.replace('\u2026', '...').replace('\u20b9', 'Rs.')
        # Collapse excessive breaks
        html = re.sub(r'(<br\s*/?>){3,}', '<br><br>', html)
        return html.strip()

    def _write_pdf(self, html_content: str, output_path: str) -> None:
        """Render HTML to PDF via fpdf2 (pure Python, zero native deps)."""
        try:
            from fpdf import FPDF
        except ImportError as exc:
            raise RuntimeError(PDF_GENERATION_ERROR_MESSAGE) from exc

        clean_html = self._sanitize_html(html_content)

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.add_page()
        pdf.set_font('Helvetica', size=12)
        pdf.write_html(clean_html)
        pdf.output(output_path)

    def _build_template_context(
        self, session: SessionState, payload: LegalDraftPayload
    ) -> dict:
        """Merge payload data + session data into a single template context dict."""
        context = {
            # From payload
            "applicant_name": payload.applicant_name,
            "applicant_age": payload.applicant_age or (session.triage.victim_age if session.triage else ""),
            "applicant_phone": payload.applicant_phone or (session.triage.victim_phone if session.triage else ""),
            "opponent_name": payload.opponent_name or "",
            "property_address": payload.property_address or "",
            "draft_body_summary": payload.draft_body_summary or "",
            "monthly_income": payload.monthly_income,
            "caste_category": payload.caste_category or "",
            "is_property_in_applicant_name": payload.is_property_in_applicant_name,
            # DV-specific fields
            "relationship": payload.relationship_to_respondent or "",
            "violence_types": payload.violence_types or [],
            "children_involved": payload.children_involved or False,
            "number_of_children": payload.number_of_children,
            "marriage_date": payload.marriage_date or "",
            "immediate_danger": payload.immediate_danger or False,
            # Safety plan fields
            "trusted_contact_name": payload.trusted_contact_name or "",
            "trusted_contact_phone": payload.trusted_contact_phone or "",
            "safe_location": payload.safe_location or "",
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

        return context

    def _make_filename(self, draft_type: DraftType, applicant_name: str) -> str:
        """Generate a safe filename like 'police_intimation_john_doe.pdf'."""
        safe_name = "".join(
            c if c.isalnum() else "_" for c in applicant_name.lower()
        ).strip("_")[:30]
        timestamp = datetime.now().strftime("%H%M")
        return f"{draft_type.value}_{safe_name}_{timestamp}.pdf"
