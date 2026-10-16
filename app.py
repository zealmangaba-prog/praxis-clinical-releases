import datetime
import io
import streamlit as st
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from core.medical_aid_presets import SCHEME_PRESETS, get_scheme_preset
from core.clinical_logic import SCOPE_GUIDELINES, get_scope_guidelines, validate_scope, synthesize_clinical_narrative
from core.clinical_copilot import (
    synthesize_treatment_plan,
    synthesize_session_notes,
    synthesize_recommendation,
    _resolve_modality_profile
)
import core.license_guard as license_guard
from core.pdf_builder import build_clinical_pdf

# ==============================================================================
# 0. LICENSE GUARD & ENTRY GATE
# ==============================================================================

st.set_page_config(page_title="Praxis Clinical", page_icon="🔒", layout="wide")

if "license_active" not in st.session_state:
    st.session_state.license_active = False
if "practice_number" not in st.session_state:
    st.session_state.practice_number = "PR #000000"

# Enforce License Gate
if not st.session_state.license_active:
    st.markdown("## 🔒 Praxis Clinical — Practitioner Activation")
    st.caption("Offline Security Verification | Local Token Authentication")
    
    col_l1, col_l2 = st.columns([1, 1.2])
    with col_l1:
        entered_pr = st.text_input("BHF Practice Number / Identifier:", placeholder="e.g. 0810012345")
        entered_key = st.text_input("Offline License Key / Token:", type="password")
        
        if st.button("Activate License & Login", type="primary"):
            is_valid, msg = license_guard.verify_license(entered_pr, entered_key) if hasattr(license_guard, "verify_license") else (True, "Active")
            if is_valid:
                st.session_state.license_active = True
                st.session_state.practice_number = entered_pr if entered_pr else "PR #000000"
                st.rerun()
            else:
                st.error(f"Activation Failed: {msg}")
    st.stop()

# ==============================================================================
# 1. HELPER FOR DYNAMIC TREATMENT PLAN TEXT
# ==============================================================================

def _build_dynamic_treatment_plan_fields(modality: str, symptoms: list, req_sessions: int) -> dict:
    """
    Uses clinical_copilot's modality engine to build modality-specific
    Treatment Plan goals, interventions, and measurable outcomes.
    """
    plan_steps = synthesize_treatment_plan(modality, symptoms, total_sessions=req_sessions)
    profile = _resolve_modality_profile(modality)
    
    # Extract unique phase goals across the requested sessions
    goal_lines = []
    for step in plan_steps:
        line = f"Session {step['session_num']} ({step['phase']}): {step['session_goal']}"
        goal_lines.append(line)
    
    # Extract distinct modality-specific outcomes
    unique_outcomes = []
    for step in plan_steps:
        if step["expected_outcome"] not in unique_outcomes:
            unique_outcomes.append(f"• {step['expected_outcome']}")

    interventions_summary = (
        f"• Primary Theoretical Framework: {profile['framework']}\n"
        f"• Intake & Baseline Protocol: {profile['intake_goal']}\n"
        f"• Core Therapeutic Mechanisms: {'; '.join(g.format(symptom=symptoms[0] if symptoms else 'presenting distress') for g in profile['session_goals'][:3])}\n"
        f"• Relapse Prevention & Termination: {profile['termination_goal']}"
    )

    return {
        "goals": "\n".join(goal_lines),
        "interventions": interventions_summary,
        "outcomes": "\n".join(unique_outcomes)
    }

# ==============================================================================
# 2. WORD (.DOCX) STYLING ENGINE
# ==============================================================================

def _set_cell_background(cell, hex_color: str):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def _set_table_borders(table, border_color: str = "CBD5E1", border_sz: str = "4"):
    tblPr = table._tbl.tblPr
    borders_elm = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'  <w:bottom w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'  <w:left w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'  <w:right w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'  <w:insideH w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'  <w:insideV w:val="single" w:sz="{border_sz}" w:space="0" w:color="{border_color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders_elm)

def _set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for edge, val in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        node = OxmlElement(f'w:{edge}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def build_docx_report(
    report_type: str,
    practitioner: dict,
    patient: dict,
    billing: dict,
    content_data: dict,
    sticker_data: dict = None
) -> io.BytesIO:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Header
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run(f"CLINICAL {report_type.upper()}")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(15)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(10)
    r_sub = p_sub.add_run(
        f"{practitioner['name']} | {practitioner['designation']}\n"
        f"Practice No (BHF): {practitioner['practice_number']} | {practitioner['address']}"
    )
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Patient Demographics Block
    doc_ref_str = patient.get('doctor', 'N/A')
    if patient.get('doctor_pr'):
        doc_ref_str += f" (BHF: {patient['doctor_pr']})"

    care_prog_line = f"Care Programme Routing: {patient.get('care_programme', 'N/A')}\n" if patient.get('care_programme') else ""

    p_info = doc.add_paragraph()
    p_info.paragraph_format.space_after = Pt(8)
    p_info.paragraph_format.line_spacing = 1.15
    p_info.add_run(
        f"Patient Name / ID: {patient['patient_name']} ({patient['case_number']})\n"
        f"Referring Doctor: {doc_ref_str}\n"
        f"Admission Date: {patient.get('admission_date', 'N/A')}\n"
        f"Discharge Date: {patient.get('discharge_date', 'N/A')}\n"
        f"Medical Scheme: {patient.get('scheme', 'N/A')}\n"
        f"Membership Number: {patient.get('membership_no', 'N/A')}\n"
        f"Dependant Code: {patient.get('dependant_code', '00')}\n"
        f"{care_prog_line}"
    ).font.size = Pt(9)

    # Optional Medical Aid Claim Voucher
    if sticker_data:
        tbl_stk = doc.add_table(rows=4, cols=2)
        tbl_stk.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_stk.autofit = False
        _set_table_borders(tbl_stk, border_color="94A3B8", border_sz="6")

        for row in tbl_stk.rows:
            for idx, cell in enumerate(row.cells):
                cell.width = [Inches(3.4), Inches(3.4)][idx]
                _set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

        h_cell = tbl_stk.cell(0, 0)
        h_cell.merge(tbl_stk.cell(0, 1))
        _set_cell_background(h_cell, "1E293B")
        r_hdr = h_cell.paragraphs[0].add_run("MEDICAL AID CLAIM VOUCHER / AUTHORISATION SUMMARY")
        r_hdr.bold = True
        r_hdr.font.size = Pt(8.5)
        r_hdr.font.color.rgb = RGBColor(255, 255, 255)

        _set_cell_background(tbl_stk.cell(1, 0), "F8FAFC")
        _set_cell_background(tbl_stk.cell(1, 1), "F8FAFC")
        tbl_stk.cell(1, 0).paragraphs[0].add_run(f"SCHEME: {sticker_data['scheme']}\nMEMBERSHIP NO: {sticker_data['membership_no']}").font.size = Pt(8.5)
        tbl_stk.cell(1, 1).paragraphs[0].add_run(f"MAIN MEMBER: {sticker_data['main_member']}\nDEP CODE: {sticker_data['dependant_code']}").font.size = Pt(8.5)

        _set_cell_background(tbl_stk.cell(2, 0), "FFFFFF")
        _set_cell_background(tbl_stk.cell(2, 1), "FFFFFF")
        pmb_flag_str = "YES (Prescribed Minimum Benefit)" if sticker_data['is_pmb'] else "NO (Standard Scheme Benefit)"
        auth_str = f" | Pre-Auth: {sticker_data['pre_auth']}" if sticker_data['pre_auth'] else ""
        tbl_stk.cell(2, 0).paragraphs[0].add_run(f"ICD-10 PRIMARY: {billing['icd10']}").font.size = Pt(8.5)
        tbl_stk.cell(2, 1).paragraphs[0].add_run(f"PMB STATUS: {pmb_flag_str}{auth_str}").font.size = Pt(8.5)

        _set_cell_background(tbl_stk.cell(3, 0), "F8FAFC")
        _set_cell_background(tbl_stk.cell(3, 1), "F8FAFC")
        tbl_stk.cell(3, 0).paragraphs[0].add_run(f"TARIFF CODE: {billing['tariff_code']} - {billing['tariff_desc']}").font.size = Pt(8.5)
        sess_count = len(content_data.get("sessions", [])) if "sessions" in content_data else content_data.get("requested_sessions", "N/A")
        tbl_stk.cell(3, 1).paragraphs[0].add_run(f"SESSIONS QUOTED / COMPLETED: {sess_count}").font.size = Pt(8.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 1. Clinical Presentation
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(2)
    h1.add_run("1. Clinical Formulation & Presentation").bold = True

    p_dem = doc.add_paragraph()
    p_dem.paragraph_format.space_after = Pt(8)
    p_dem.add_run(
        f"Primary ICD-10 Diagnosis: {billing['icd10']}\n"
        f"Target Symptoms / Indicators: {', '.join(patient['symptoms'])}\n"
        f"Therapeutic Framework: {patient['modality']}"
    ).font.size = Pt(9.5)

    # 2. Section Based on Report Type
    if report_type == "Clinical Progress Report":
        h2 = doc.add_paragraph()
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(2)
        h2.add_run("2. Clinical Trajectory & Progress Evaluation").bold = True
        
        p_traj = doc.add_paragraph()
        p_traj.paragraph_format.space_after = Pt(6)
        p_traj.add_run(content_data.get("trajectory", "")).font.size = Pt(9.5)

        p_adh = doc.add_paragraph()
        p_adh.paragraph_format.space_after = Pt(4)
        r_adh_label = p_adh.add_run("Treatment Adherence & Engagement: ")
        r_adh_label.bold = True
        p_adh.add_run(content_data.get("adherence", "Consistent attendance and active therapeutic engagement.")).font.size = Pt(9.5)

        p_barr = doc.add_paragraph()
        p_barr.paragraph_format.space_after = Pt(8)
        r_barr_label = p_barr.add_run("Ongoing Challenges & Barriers: ")
        r_barr_label.bold = True
        p_barr.add_run(content_data.get("barriers", "Environmental and situational stressors; ongoing emotional regulation work required.")).font.size = Pt(9.5)

        # Session Progression Table
        sessions = content_data.get("sessions", [])
        h2_sess = doc.add_paragraph()
        h2_sess.paragraph_format.space_before = Pt(6)
        h2_sess.paragraph_format.space_after = Pt(2)
        h2_sess.add_run("Service Dates & Symptom-Linked Progress Log").bold = True

        tbl_sess = doc.add_table(rows=1 + len(sessions), cols=5)
        tbl_sess.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_sess.autofit = False
        _set_table_borders(tbl_sess, border_color="CBD5E1", border_sz="4")

        col_widths = [Inches(0.45), Inches(0.95), Inches(0.75), Inches(1.65), Inches(3.0)]
        headers = ["#", "Date", "Tariff", "Symptom Target", "Clinical Observations & Content"]

        for idx, name in enumerate(headers):
            cell = tbl_sess.cell(0, idx)
            cell.width = col_widths[idx]
            _set_cell_background(cell, "F1F5F9")
            _set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx < 3 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(name)
            r.bold = True
            r.font.size = Pt(8)

        for r_idx, s in enumerate(sessions, start=1):
            row = tbl_sess.rows[r_idx]
            vals = [str(s["num"]), str(s["date"]), billing["tariff_code"], s["symptom_target"], s["content"]]
            for c_idx, val in enumerate(vals):
                cell = row.cells[c_idx]
                cell.width = col_widths[c_idx]
                _set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx < 3 else WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                r.font.size = Pt(8)

    elif report_type == "Treatment Plan / Authorisation Request":
        h2 = doc.add_paragraph()
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(2)
        h2.add_run("2. Treatment Goals, Clinical Interventions & Expected Outcomes").bold = True

        p_tp = doc.add_paragraph()
        p_tp.paragraph_format.space_after = Pt(8)
        p_tp.add_run(
            f"Goals of Treatment:\n{content_data.get('goals', '')}\n\n"
            f"Specific Therapeutic Interventions:\n{content_data.get('interventions', '')}\n\n"
            f"Expected Measurable Outcomes:\n{content_data.get('outcomes', '')}\n\n"
            f"Sessions Requested: {content_data.get('requested_sessions', 6)} sessions under tariff {billing['tariff_code']}."
        ).font.size = Pt(9.5)

    else:  # Clinical Summary / Discharge Note
        h2 = doc.add_paragraph()
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(2)
        h2.add_run("2. Treatment Summary & Discharge Evaluation").bold = True

        p_sum = doc.add_paragraph()
        p_sum.paragraph_format.space_after = Pt(8)
        p_sum.add_run(
            f"Clinical Course & Outcomes:\n{content_data.get('summary_text', '')}\n\n"
            f"Discharge Recommendations:\n{content_data.get('discharge_plan', '')}"
        ).font.size = Pt(9.5)

    # 3. Overall Recommendation & Motivation (Powered by clinical_copilot)
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(2)
    h3.add_run("3. Professional Motivation & Authorisation").bold = True

    dynamic_rec = synthesize_recommendation(
        discipline=practitioner['designation'],
        modality=patient['modality'],
        symptoms=patient['symptoms'],
        tariff_code=billing['tariff_code']
    )

    p_rec = doc.add_paragraph()
    p_rec.paragraph_format.space_after = Pt(24)
    p_rec.add_run(dynamic_rec).font.size = Pt(9.5)

    # Practitioner Signature Block
    sig_data = practitioner.get("signature")
    if sig_data:
        try:
            doc.add_picture(io.BytesIO(sig_data), width=Inches(1.8))
            p_sig = doc.add_paragraph()
            p_sig.add_run(
                f"{practitioner['name']}\n"
                f"{practitioner['designation']}\n"
                f"BHF Practice No: {practitioner['practice_number']}"
            ).font.size = Pt(9.5)
        except Exception as e:
            print(f"Word signature error: {e}")
            p_sig = doc.add_paragraph()
            p_sig.add_run(
                f"____________________________________\n"
                f"{practitioner['name']}\n"
                f"{practitioner['designation']}\n"
                f"BHF Practice No: {practitioner['practice_number']}"
            ).font.size = Pt(9.5)
    else:
        p_sig = doc.add_paragraph()
        p_sig.add_run(
            f"____________________________________\n"
            f"{practitioner['name']}\n"
            f"{practitioner['designation']}\n"
            f"BHF Practice No: {practitioner['practice_number']}"
        ).font.size = Pt(9.5)

    target_io = io.BytesIO()
    doc.save(target_io)
    target_io.seek(0)
    return target_io

# ==============================================================================
# 3. STREAMLIT UI DASHBOARD
# ==============================================================================

st.markdown("### 🔒 Praxis Clinical")

# Report Mode Switcher
report_type = st.radio(
    "Select Document Type to Generate:",
    options=[
        "Clinical Progress Report",
        "Treatment Plan / Authorisation Request",
        "Clinical Summary / Discharge Note"
    ],
    horizontal=True
)

st.divider()

# Patient Core Demographics Header Row
hdr_c1, hdr_c2, hdr_c3 = st.columns(3)
with hdr_c1:
    patient_name = st.text_input("Patient Full Name / Reference:", value="John Doe")
    case_number = st.text_input("Case / File Number:", value="CLIN-2026-004")
    referring_doctor = st.text_input("Referring Medical Practitioner:", value="Dr. M. Peterson")
    
with hdr_c2:
    scheme_choice = st.selectbox("Medical Scheme Administrator:", options=list(SCHEME_PRESETS.keys()), index=0)
    preset_info = get_scheme_preset(scheme_choice)
    membership_no = st.text_input("Membership Number:", value="902148291")
    dependant_code = st.text_input("Dependant Code:", value="00")

with hdr_c3:
    referring_doctor_pr = st.text_input(
        "Referring Doctor BHF Practice No:", 
        value="0140023" if preset_info.get("requires_referring_pr") else "",
        placeholder="Mandatory for Discovery / GEMS" if preset_info.get("requires_referring_pr") else "Optional"
    )
    admission_date = st.date_input("Date of Admission / Intake:", datetime.date.today() - datetime.timedelta(days=30))
    discharge_date = st.text_input("Discharge Date (if applicable):", value="N/A")

# Contextual Scheme Guidance Alert
st.info(f"📋 **{preset_info['admin_name']} Protocol:** {preset_info['guidance_note']}")

# --- SIDEBAR: PRACTITIONER PROFILE ---
with st.sidebar:
    st.success(f"License Active ({st.session_state.practice_number})")
    if st.button("Lock Application"):
        st.session_state.license_active = False
        st.rerun()

    st.markdown("---")
    st.subheader("Practitioner Profile")

    designation = st.selectbox(
        "Professional Registration Category:",
        options=list(SCOPE_GUIDELINES.keys()),
        index=0
    )
    scope_info = get_scope_guidelines(designation)
    st.info(f"**Scope Note:** {scope_info.get('scope_note', 'Practitioner in good standing.')}")

    practitioner_name = st.text_input("Practitioner Full Name:", value="Dr. J. Doe")
    practitioner_address = st.text_area("Physical / Practice Address:", value="Suite 4, Mediclinic Building, Sandton", height=70)
    practitioner_pr = st.text_input("Practice Number (BHF):", value=st.session_state.practice_number)
    practice_phone = st.text_input("Practice Contact Number:", value="+27 11 123 4567")
    practice_email = st.text_input("Practice Email Address:", value="practitioner@practice.com")


    st.markdown("**Electronic Signature:**")
    sig_file = st.file_uploader("Upload Signature (PNG / JPG):", type=["png", "jpg", "jpeg"])
    sig_bytes = sig_file.getvalue() if sig_file is not None else None
    if sig_bytes:
        st.image(sig_bytes, width=150, caption="Loaded Signature")

    st.markdown("---")
    st.caption(
        """
        **Clinical Treatment Plan & Report Generator**  
        © 2026 Zeal Katlego Mangaba. All Rights Reserved.  
        Local-first, zero-cloud architecture in accordance with POPIA.
        """
    )

practitioner_info = {
    "name": practitioner_name,
    "designation": designation,
    "address": practitioner_address,
    "practice_number": practitioner_pr,
    "phone": practice_phone,
    "email": practice_email,
    "signature": sig_bytes,
}

# --- TWO COLUMN CLINICAL WORKSPACE ---
col_left, col_right = st.columns([1, 1.1])

# === COLUMN 1: DIAGNOSTIC & SYMPTOM MATRIX ===
with col_left:
    st.subheader("1. Diagnostic & Symptom Cluster Matrix")

    icd10 = st.selectbox(
        "Diagnostic Category (ICD-10 Primary - SA MIT Standard):",
        [
            # Substance Use, Abuse & Dependence Disorders
            "F10.1 - Harmful Use of Alcohol",
            "F10.2 - Alcohol Dependence Syndrome",
            "F11.1 - Harmful Use of Opioids",
            "F11.2 - Opioid Dependence Syndrome",
            "F12.1 - Harmful Use of Cannabis",
            "F12.2 - Cannabis Dependence Syndrome",
            "F13.1 - Harmful Use of Sedatives or Hypnotics",
            "F13.2 - Sedative or Hypnotic Dependence Syndrome",
            "F14.1 - Harmful Use of Cocaine",
            "F14.2 - Cocaine Dependence Syndrome",
            "F15.1 - Harmful Use of Stimulants (Amphetamines, etc.)",
            "F15.2 - Stimulant Dependence Syndrome",
            "F16.1 - Harmful Use of Hallucinogens",
            "F17.1 - Harmful Use of Nicotine",
            "F18.1 - Harmful Use of Volatile Solvents",
            "F19.1 - Harmful Use of Multiple Substances",
            "F19.2 - Dependence Syndrome due to Multiple Substances",
            
            # Bereavement, Loss & Adjustment Reactions (SA 4-Character Standard)
            "F43.2 - Adjustment Disorder: Depressed Mood Secondary to Loss",
            "F43.2 - Adjustment Disorder: Anxious Mood Secondary to Stress/Loss",
            "F43.2 - Adjustment Disorder: Mixed Anxiety and Depressed Mood",
            "F43.2 - Adjustment Disorder: Mixed Disturbance of Emotions and Conduct",
            "F43.8 - Other Reactions to Severe Stress (Prolonged Grief Reaction)",
            "Z63.4 - Disappearance and Death of Family Member (Uncomplicated Bereavement)",

            # Trauma & Acute Stressor-Related Disorders
            "F43.1 - Post-Traumatic Stress Disorder (PTSD - PMB Eligible)",
            "F43.0 - Acute Stress Reaction (PMB Eligible)",
            "F43.2 - Adjustment Disorder with Mixed Anxiety and Depressed Mood (PMB Eligible)",
            "F43.8 - Other Specified Reactions to Severe Stress (PMB Eligible)",
            "F43.9 - Reaction to Severe Stress, Unspecified (PMB Eligible)",

            # Mood, Depressive & Bipolar Spectrum Disorders
            "F32.0 - Mild Depressive Episode",
            "F32.1 - Moderate Depressive Episode (PMB Eligible)",
            "F32.2 - Severe Depressive Episode without Psychotic Symptoms (PMB Eligible)",
            "F33.1 - Recurrent Depressive Disorder, Current Episode Moderate (PMB Eligible)",
            "F33.2 - Recurrent Depressive Disorder, Current Episode Severe without Psychotic Symptoms (PMB Eligible)",
            "F34.1 - Dysthymia / Persistent Depressive Disorder",
            "F31.3 - Bipolar Affective Disorder, Current Episode Mild or Moderate Depression (PMB Eligible)",
            "F31.4 - Bipolar Affective Disorder, Current Episode Severe Depression without Psychotic Symptoms (PMB Eligible)",
            "F31.6 - Bipolar Affective Disorder, Current Episode Mixed (PMB Eligible)",
            "F31.9 - Bipolar Affective Disorder, Unspecified (PMB Eligible)",

            # Anxiety, Phobic, Obsessive & Somatoform Presentations
            "F41.1 - Generalized Anxiety Disorder (GAD)",
            "F41.0 - Panic Disorder [Episodic Paroxysmal Anxiety]",
            "F40.1 - Social Phobia / Social Anxiety Disorder",
            "F40.2 - Specific (Isolated) Phobias",
            "F41.2 - Mixed Anxiety and Depressive Disorder",
            "F41.8 - Other Specified Anxiety Disorders",
            "F41.9 - Anxiety Disorder, Unspecified",
            "F42.2 - Mixed Obsessional Thoughts and Acts (OCD - PMB Eligible)",
            "F45.0 - Somatization Disorder",
            "F45.1 - Undifferentiated Somatoform Disorder",
            "F45.2 - Hypochondriacal Disorder",
            "F45.3 - Somatoform Autonomic Dysfunction",
            "F45.4 - Persistent Somatoform Pain Disorder",
            "F45.8 - Other Somatoform Disorders",
            "F45.9 - Somatoform Disorder, Unspecified",
            "F50.0 - Anorexia Nervosa",
            "F50.2 - Bulimia Nervosa",
            "F50.8 - Other Eating Disorders",
            "F50.9 - Eating Disorder, Unspecified",
            "F51.0 - Nonorganic Insomnia",
            "F51.1 - Nonorganic Hypersomnia",

            # Neurodevelopmental, Child & Educational Presentations
            "F90.0 - Disturbance of Activity and Attention (ADHD, Inattentive/Combined)",
            "F90.1 - Hyperkinetic Conduct Disorder (ADHD with Conduct Disturbance)",
            "F80.0 - Specific Speech Articulation Disorder",
            "F81.0 - Specific Reading Disorder (Dyslexia)",
            "F81.2 - Specific Disorder of Arithmetical Skills (Dyscalculia)",
            "F91.3 - Oppositional Defiant Disorder (ODD)",
            "F93.0 - Separation Anxiety Disorder of Childhood",
            "F95.1 - Chronic Motor or Vocal Tic Disorder",
            "F95.2 - Combined Vocal and Multiple Motor Tic Disorder [Tourette]",
            "F98.8 - Other Specified Behavioural and Emotional Disorders with Onset in Childhood",
            

            # Psychosocial, Relational & Workplace Factors (Z-Codes / Non-PMB)
            "Z73.0 - Burn-out / State of Vital Exhaustion (Non-PMB)",
            "Z56.6 - Other Physical and Mental Strain Related to Work (Non-PMB)",
            "Z63.0 - Problems in Relationship with Spouse or Partner (Non-PMB)",
            "Z63.1 - Problems in Relationship with Parents and In-Laws (Non-PMB)",
            "Z63.2 - Inadequate Family Support / Household Isolation (Non-PMB)",
            "Z63.3 - Absence of Family Member (Stressful Household Event - Non-PMB)",
            "Z63.5 - Disruption of Family by Separation and Divorce (Non-PMB)",
            "Z63.8 - Other Specified Problems Related to Primary Support Group (Non-PMB)",
            "Z55.9 - Problems Related to Education and Literacy, Unspecified (Non-PMB)"
        ]
    )


    is_pmb_default = "PMB Eligible" in icd10
    if is_pmb_default:
        st.info("💡 **Prescribed Minimum Benefit (PMB):** Statutory coverage applies under Medical Schemes Act diagnostic treatment pairs.")

    st.markdown("**Observed Clinical Symptom Clusters (Tick all present):**")
    sc1, sc2, sc3 = st.columns(3)
    
    selected_symptoms = []

with sc1:
    st.caption("Affective, Mood & Risk")
    if st.checkbox("Persistent low mood / Dysphoria"):
        selected_symptoms.append("Persistent low mood / Dysphoria")
    if st.checkbox("Anhedonia / Loss of pleasure or motivation"):
        selected_symptoms.append("Anhedonia & loss of motivation")
    if st.checkbox("Elevated / Expansive mood / Racing thoughts"):
        selected_symptoms.append("Elevated mood / Flight of ideas")
    if st.checkbox("Excessive guilt / Feelings of worthlessness"):
        selected_symptoms.append("Excessive guilt & worthlessness")
    if st.checkbox("Separation distress / Intense yearning"):
        selected_symptoms.append("Separation distress & grief yearning")
    if st.checkbox("Preoccupation with loss / Rumination"):
        selected_symptoms.append("Loss-related rumination")
    if st.checkbox("Irritability / Anger outbursts / Frustration"):
        selected_symptoms.append("Irritability & anger outbursts")
    if st.checkbox("Emotional numbness / Dissociative detachment"):
        selected_symptoms.append("Emotional numbness & detachment")
    if st.checkbox("Hopelessness / Helplessness / Pessimism"):
        selected_symptoms.append("Hopelessness & helplessness")
    if st.checkbox("Self-criticism / Self-blame / Self-punishment"):
        selected_symptoms.append("Self-criticism & self-blame")
    if st.checkbox("Ruminative worry / Catastrophizing / Overthinking"):
        selected_symptoms.append("Ruminative worry & catastrophizing")            
    if st.checkbox("Tears, crying spells / Emotional lability"):
        selected_symptoms.append("Tearfulness & emotional lability")
    if st.checkbox("Suicidal ideation / Self-harm thoughts"):
        selected_symptoms.append("Suicidal ideation & self-harm risk")
    if st.checkbox("Homicidal ideation / Violent impulses / Harm to others"):
        selected_symptoms.append("Risk of harm to others / Aggressive impulses")

with sc2:
    st.caption("Somatic, Vegetative & Eating")
    if st.checkbox("Sleep disruption (Initial/Middle/Terminal insomnia)"):
        selected_symptoms.append("Insomnia / Sleep disruption")
    if st.checkbox("Decreased need for sleep (without daytime fatigue)"):
        selected_symptoms.append("Decreased need for sleep (hypomanic marker)")
    if st.checkbox("Chronic fatigue / Loss of physical energy"):
        selected_symptoms.append("Chronic fatigue & anergia")
    if st.checkbox("Panic surges / Sudden peaks of acute terror"):
        selected_symptoms.append("Discrete panic surges")
    if st.checkbox("Autonomic arousal (Palpitations / Dyspnea / Tremors)"):
        selected_symptoms.append("Autonomic anxiety arousal")
    if st.checkbox("Muscle tension / Tension headaches / Body aches"):
        selected_symptoms.append("Somatic muscle tension & headaches")
    if st.checkbox("Appetite / Weight changes (Significant loss or gain)"):
        selected_symptoms.append("Appetite & weight fluctuations")
    if st.checkbox("Binge eating / Purging / Compensatory fasting"):
        selected_symptoms.append("Bingeing/purging compensatory behaviors")
    if st.checkbox("Psychomotor agitation or retardation"):
        selected_symptoms.append("Psychomotor alterations")
    if st.checkbox("Gastrointestinal distress / Somatosensory amplifying"):
        selected_symptoms.append("Gastrointestinal distress & pain amplification")
    if st.checkbox("Sexual dysfunction / Loss of libido"):
        selected_symptoms.append("Sexual dysfunction / Libido loss")

with sc3:
    st.caption("Cognitive, Trauma & Reality Testing")
    if st.checkbox("Executive dysfunction / Brain fog / Focus lapses"):
        selected_symptoms.append("Concentration & executive lapses")
    if st.checkbox("Working memory deficits / Forgetfulness"):
        selected_symptoms.append("Working memory deficits")
    if st.checkbox("Obsessive intrusive thoughts / Compulsive rituals"):
        selected_symptoms.append("Obsessive thoughts & compulsive rituals")
    if st.checkbox("Auditory/Visual hallucinations / Perceptual disturbances"):
        selected_symptoms.append("Perceptual disturbances / Hallucinations")
    if st.checkbox("Paranoid ideation / Delusions / Impaired reality testing"):
        selected_symptoms.append("Paranoid / Delusional ideation")
    if st.checkbox("Hypervigilance / Exaggerated startle response"):
        selected_symptoms.append("Hypervigilance & startle reactivity")
    if st.checkbox("Intrusive traumatic memories / Flashbacks / Nightmares"):
        selected_symptoms.append("Intrusive traumatic recollections & nightmares")
    if st.checkbox("Active avoidance behaviour (Triggers / People / Reminders)"):
        selected_symptoms.append("Active phobic/trauma avoidance")
    if st.checkbox("Functional impairment (Occupational / Academic / Relational)"):
        selected_symptoms.append("Functional impairment across life domains")
    if st.checkbox("Substance use / Alcohol or prescription drug misuse"):
        selected_symptoms.append("Substance / Medication misuse")
    if st.checkbox("Self-neglect / Impaired basic self-care"):
        selected_symptoms.append("Self-neglect & compromised self-care")

    if not selected_symptoms:
        selected_symptoms = ["Bereavement-related adjustment difficulties"]

    st.markdown("---")
    st.markdown("**Therapeutic Modality & Billing Tariff:**")
    
    # Combine scope modalities with core clinical_copilot modalities so all 5 frameworks are accessible
    core_modalities = [
        "Cognitive Behavioral Therapy (CBT)",
        "Acceptance and Commitment Therapy (ACT)",
        "Dialectical Behavior Therapy (DBT)",
        "Psychodynamic Psychotherapy",
        "Solution-Focused Brief Therapy (SFBT)"
    ]
    scope_mods = scope_info.get("modalities", [])
    combined_modalities = core_modalities + [m for m in scope_mods if m not in core_modalities]
    
    modality = st.selectbox("Primary Therapeutic Modality:", combined_modalities)
    
    tariff_choice = st.selectbox(
        "Applicable Billing Tariff:",
        options=list(scope_info.get("allowed_tariffs", {}).keys()),
        format_func=lambda k: f"{k} - {scope_info.get('allowed_tariffs', {})[k]}"
    )
    tariff_desc = scope_info.get("allowed_tariffs", {}).get(tariff_choice, "Clinical Session")

    # Optional Medical Aid Claim Voucher
    st.markdown("---")
    include_sticker = st.checkbox("Include Medical Aid Claim Voucher / Sticker", value=False)
    sticker_data = None

    if include_sticker:
        with st.container(border=True):
            st.markdown("##### 📋 Medical Aid Claim Voucher Sticker")
            stk_c1, stk_c2 = st.columns(2)
            with stk_c1:
                stk_scheme = st.text_input("Scheme Name", value=preset_info["admin_name"])
                stk_mem_no = st.text_input("Membership Number", value=membership_no)
                stk_dep = st.text_input("Dependant Code", value=dependant_code)
            with stk_c2:
                main_member_val = f"{patient_name} (Self)" if patient_name else ""
                main_member = st.text_input("Main Member Initial/Surname", value=main_member_val)
                pre_auth = st.text_input("Pre-Authorisation Number (if issued)", value="")
                is_pmb = st.checkbox("Prescribed Minimum Benefit (PMB)", value=is_pmb_default)

        sticker_data = {
            "scheme": stk_scheme,
            "membership_no": stk_mem_no,
            "dependant_code": stk_dep,
            "main_member": main_member,
            "pre_auth": pre_auth,
            "is_pmb": is_pmb
        }

# === COLUMN 2: REVIEW, CUSTOMIZE & EXPORT ===
# === COLUMN 2: REVIEW, CUSTOMIZE & EXPORT ===
with col_right:
  st.subheader(f"2. {report_type} Content")

  # --- Manual / Non-Sequential Session Date Selector ---
  st.caption("Documented Consultation Dates")

  # Use st.date_input with a list or single date selection
  # Clinicians can either pick dates sequentially or select individual dates
  session_count = st.number_input(
      "Documented Sessions Count", min_value=1, max_value=20, value=4, step=1
  )

  # Let clinician freely pick the dates via an expandable section or dynamic pickers
  session_dates = []
  with st.expander("Edit Consultation Dates", expanded=True):
    date_cols = st.columns(2)
    base_date = datetime.date.today()

    for i in range(int(session_count)):
      col_idx = i % 2
      with date_cols[col_idx]:
        # Defaults each session spaced out, but calendar allows picking ANY arbitrary date
        picked_date = st.date_input(
            f"Session {i+1} Date",
            value=base_date - datetime.timedelta(weeks=(session_count - 1 - i)),
            key=f"session_date_picker_{i}",
            format="YYYY/MM/DD",
        )
        session_dates.append(picked_date.strftime("%Y-%m-%d"))

  # session_dates is now an array of whatever dates the clinician picked:
  # e.g. ['2026-08-03', '2026-08-07', '2026-08-28', '2026-09-15'] 

    # Helper function to synchronize both clinical_logic and clinical_copilot outputs
    def _run_full_synthesis():
        generated = synthesize_clinical_narrative(
            designation=designation,
            icd10=icd10,
            modality=modality,
            symptoms=selected_symptoms,
            session_count=session_count,
            dates=session_dates
        )
        # Override session notes with the rich multi-bullet clinical_copilot engine
        rich_sessions = synthesize_session_notes(
            discipline=designation,
            modality=modality,
            selected_symptoms=selected_symptoms,
            service_dates=session_dates
        )
        st.session_state["dyn_trajectory"] = generated["trajectory"]
        st.session_state["dyn_adherence"] = generated["adherence"]
        st.session_state["dyn_barriers"] = generated["barriers"]
        st.session_state["dyn_sessions"] = rich_sessions

        # Clear cached session widget keys so Streamlit renders the newly synthesized text
        for k in list(st.session_state.keys()):
            if k.startswith("target_") or k.startswith("note_"):
                del st.session_state[k]

        # Update dynamic Treatment Plan fields
        tp_fields = _build_dynamic_treatment_plan_fields(modality, selected_symptoms, session_count)
        st.session_state["tp_goals"] = tp_fields["goals"]
        st.session_state["tp_interventions"] = tp_fields["interventions"]
        st.session_state["tp_outcomes"] = tp_fields["outcomes"]
        st.session_state["last_modality"] = modality

    # Auto-trigger synthesis on initial load OR whenever the user switches modality
    if "dyn_trajectory" not in st.session_state or st.session_state.get("last_modality") != modality:
        _run_full_synthesis()

    # GENERATE / RE-SYNTHESIZE BUTTON
    if st.button("🔄 Generate / Re-synthesize Report Content", type="primary", use_container_width=True):
        _run_full_synthesis()
        st.rerun()

    content_data = {}

    # DYNAMIC CONTENT BUILDER ACCORDING TO REPORT TYPE
    if report_type == "Clinical Progress Report":
        st.markdown("**Clinical Trajectory & Rationale:**")
        traj_input = st.text_area("Trajectory:", value=st.session_state["dyn_trajectory"], height=100, label_visibility="collapsed")

        st.markdown("**Therapy Adherence & Engagement:**")
        adh_input = st.text_area("Adherence:", value=st.session_state["dyn_adherence"], height=65, label_visibility="collapsed")

        st.markdown("**Ongoing Challenges & Clinical Barriers:**")
        barr_input = st.text_area("Barriers:", value=st.session_state["dyn_barriers"], height=65, label_visibility="collapsed")

        st.markdown(f"**Session Progression Log ({len(st.session_state['dyn_sessions'])} Documented Sessions):**")
        sessions_data = []
        with st.expander("📝 Edit Session Progression Records", expanded=True):
            for i, sess in enumerate(st.session_state["dyn_sessions"], start=1):
                s_c1, s_c2 = st.columns([1, 2.5])
                with s_c1:
                    st.markdown(f"**Session {sess['num']}** | `{sess['date']}`")
                    target_str = st.text_input(f"Target (S{i})", value=sess["symptom_target"], key=f"target_{i}")
                with s_c2:
                    content_str = st.text_area(f"Clinical Note (S{i})", value=sess["content"], key=f"note_{i}", height=110)

                scope_violations = validate_scope(designation, content_str)
                if scope_violations:
                    st.warning(f"⚠️ Scope flag for {designation}: Rephrase '{', '.join(scope_violations)}'.")

                sessions_data.append({
                    "num": sess["num"],
                    "date": sess["date"],
                    "symptom_target": target_str,
                    "content": content_str
                })

        content_data = {
            "trajectory": traj_input,
            "adherence": adh_input,
            "barriers": barr_input,
            "sessions": sessions_data
        }

    elif report_type == "Treatment Plan / Authorisation Request":
        st.markdown("---")
        st.markdown("**Treatment Plan & Authorization Parameters:**")
        
        req_sessions = st.number_input("Requested Sessions for Authorization:", min_value=1, max_value=20, value=int(session_count))
        
        # Dynamically rebuild plan if requested session count or symptoms changed
        tp_dynamic = _build_dynamic_treatment_plan_fields(modality, selected_symptoms, req_sessions)

        goals = st.text_area(
            "Goals of Sessions (Modality-Aligned):",
            value=tp_dynamic["goals"],
            height=130
        )
        interventions = st.text_area(
            "Interventions Used / Planned:",
            value=tp_dynamic["interventions"],
            height=115
        )
        outcomes = st.text_area(
            "Expected Measurable Outcomes:",
            value=tp_dynamic["outcomes"],
            height=115
        )
        content_data = {
            "requested_sessions": req_sessions,
            "goals": goals,
            "interventions": interventions,
            "outcomes": outcomes
        }

    else:  # Clinical Summary / Discharge Note
        st.markdown("---")
        st.markdown("**Clinical Summary & Discharge Evaluation:**")
        profile = _resolve_modality_profile(modality)
        summary_text = st.text_area(
            "Course of Treatment & Summary:",
            value=(
                f"Client completed a structured therapeutic cycle under {profile['framework']} targeting {icd10}. "
                f"Observable clinical stabilization achieved across {', '.join(selected_symptoms[:3])}. "
                f"{profile['termination_outcome']}"
            ),
            height=100
        )
        discharge_plan = st.text_area(
            "Discharge Recommendations / Relapse Prevention:",
            value=(
                f"{profile['termination_goal']} Client educated on relapse indicators and self-referral "
                f"protocols should acute stressors or symptom clusters resurface."
            ),
            height=80
        )
        content_data = {
            "summary_text": summary_text,
            "discharge_plan": discharge_plan
        }

    # Export Area
    st.markdown("---")
    st.markdown("**Compile & Export Documents:**")

    patient_payload = {
        "patient_name": patient_name,
        "case_number": case_number,
        "doctor": referring_doctor,
        "doctor_pr": referring_doctor_pr,
        "scheme": preset_info["admin_name"],
        "membership_no": membership_no,
        "dependant_code": dependant_code,
        "admission_date": admission_date.strftime("%Y-%m-%d"),
        "discharge_date": discharge_date,
        "modality": modality,
        "symptoms": selected_symptoms
    }

    billing_payload = {
        "icd10": icd10,
        "tariff_code": tariff_choice,
        "tariff_desc": tariff_desc
    }

    date_str = datetime.date.today().strftime('%Y%m%d')
    file_base = f"{report_type.replace(' ', '_').replace('/', '-')}_{case_number}_{date_str}"

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        doc_buf = build_docx_report(
            report_type=report_type,
            practitioner=practitioner_info,
            patient=patient_payload,
            billing=billing_payload,
            content_data=content_data,
            sticker_data=sticker_data
        )
        st.download_button(
            label="📄 Export Word (.docx)",
            data=doc_buf,
            file_name=f"{file_base}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True
        )

    with exp_col2:
        pdf_buf = build_clinical_pdf(
            report_type=report_type,
            practitioner=practitioner_info,
            patient=patient_payload,
            billing=billing_payload,
            content_data=content_data,
            sticker_data=sticker_data
        )
        st.download_button(
            label="🔒 Export PDF (.pdf)",
            data=pdf_buf,
            file_name=f"{file_base}.pdf",
            mime="application/pdf",
            type="secondary",
            use_container_width=True
        )

    # Scheme-Specific Submission Helper Card
    st.markdown("---")
    with st.expander("✉️ Scheme Submission Instructions & Routing Details", expanded=True):
        subj = preset_info["submission_subject"].format(
            membership_no=membership_no,
            patient_name=patient_name,
            dependant_code=dependant_code,
            tariff_code=tariff_choice
        )
        st.markdown(f"**Target Routing / Email:** `{preset_info['email_portal']}`")
        st.markdown(f"**Recommended Email Subject:** `{subj}`")
        st.caption(f"Attach your exported PDF and ensure the referring doctor's practice number ({referring_doctor_pr or 'N/A'}) is legible.")
