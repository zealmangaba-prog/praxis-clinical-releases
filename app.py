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
# 1. WORD (.DOCX) STYLING ENGINE
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

    # =========================================================================
    # 👇 STEP 2 GOES HERE (REPLACE OLD DEMOGRAPHICS BLOCK / TABLE WITH THIS):
    # =========================================================================
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
    # =========================================================================

    # Optional Medical Aid Claim Voucher follows immediately below:
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
        # Clinical Trajectory
        h2 = doc.add_paragraph()
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(2)
        h2.add_run("2. Clinical Trajectory & Progress Evaluation").bold = True
        
        p_traj = doc.add_paragraph()
        p_traj.paragraph_format.space_after = Pt(6)
        p_traj.add_run(content_data.get("trajectory", "")).font.size = Pt(9.5)

        # Medical Aid Compliance: Adherence & Barriers
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

        col_widths = [Inches(0.5), Inches(1.0), Inches(0.8), Inches(1.8), Inches(2.7)]
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
            vals = [str(s["num"]), s["date"], billing["tariff_code"], s["symptom_target"], s["content"]]
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

    # 3. Overall Recommendation & Motivation
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(2)
    h3.add_run("3. Professional Motivation & Authorisation").bold = True

    p_rec = doc.add_paragraph()
    p_rec.paragraph_format.space_after = Pt(24)
    p_rec.add_run(
        f"In accordance with clinical protocol under {practitioner['designation']}, "
        f"therapeutic services under tariff {billing['tariff_code']} are motivated "
        f"to maintain psychosocial stability, develop resilience, and prevent regression."
    ).font.size = Pt(9.5)

    # Practitioner Signature Block
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
# 2. STREAMLIT UI DASHBOARD
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

    st.markdown("**Electronic Signature:**")
    sig_file = st.file_uploader("Upload Signature (PNG / JPG):", type=["png", "jpg", "jpeg"])
    sig_bytes = sig_file.read() if sig_file else None
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
    "practice_number": practitioner_pr
}

# --- TWO COLUMN CLINICAL WORKSPACE ---
col_left, col_right = st.columns([1, 1.1])

# === COLUMN 1: DIAGNOSTIC & SYMPTOM MATRIX ===
with col_left:
    st.subheader("1. Diagnostic & Symptom Cluster Matrix")

    icd10 = st.selectbox(
        
        "Diagnostic Category (ICD-10 Primary):",
        [
            # Bereavement, Loss & Grief Reactions
            "Z63.4 - Disappearance and death of family member (Uncomplicated Bereavement)",
            "F43.8 - Other reactions to severe stress (Prolonged Grief Reaction)",
            "F43.21 - Adjustment Disorder with Depressed Mood secondary to Loss",
            "F43.22 - Adjustment Disorder with Anxious Mood secondary to Loss",
            "F43.23 - Adjustment Disorder with Mixed Anxiety and Depressed Mood",

            # Trauma & Stressor-Related Disorders
            "F43.10 - Post-Traumatic Stress Disorder (PTSD - PMB Eligible)",
            "F43.0 - Acute Stress Reaction",

            # Mood & Depressive Spectrum Disorders
            "F32.0 - Mild Depressive Episode",
            "F32.1 - Moderate Depressive Episode (PMB Eligible)",
            "F32.2 - Severe Depressive Episode without Psychotic Symptoms (PMB Eligible)",
            "F33.1 - Recurrent Depressive Disorder, Current Episode Moderate (PMB Eligible)",
            "F34.1 - Dysthymia / Persistent Depressive Disorder",
            "F31.9 - Bipolar Affective Disorder, Unspecified (PMB Eligible)",

            # Anxiety, Phobic & Somatoform Presentations
            "F41.1 - Generalized Anxiety Disorder (GAD)",
            "F41.0 - Panic Disorder without Agoraphobia",
            "F40.1 - Social Phobia / Social Anxiety Disorder",
            "F42.2 - Mixed Obsessional Thoughts and Acts (OCD - PMB Eligible)",
            "F45.0 - Somatization Disorder / Persistent Somatoform Pain Disorder",

            # Neurodevelopmental, Child & Educational Presentations
            "F90.0 - Attention-Deficit Hyperactivity Disorder (ADHD, Inattentive Type)",
            "F90.2 - Attention-Deficit Hyperactivity Disorder (ADHD, Combined Type)",
            "F81.0 - Specific Reading Disorder (Dyslexia)",
            "F91.3 - Oppositional Defiant Disorder (ODD)",
            "F93.0 - Separation Anxiety Disorder of Childhood",

            # Psychosocial, Relational & Workplace Factors (V / Z Codes)
            "Z63.0 - Problems in Relationship with Spouse or Partner",
            "Z63.8 - Other Specified Problems Related to Primary Support Group (Family Conflict)",
            "Z73.0 - Burn-out / State of Vital Exhaustion",
            "Z56.6 - Other Physical and Mental Strain Related to Work",
            "Z55.9 - Problems Related to Education and Literacy, Unspecified"
        ]
    )
    

    is_pmb_default = "PMB Eligible" in icd10
    if is_pmb_default:
        st.info("💡 **Prescribed Minimum Benefit (PMB):** Statutory coverage applies under Medical Schemes Act diagnostic treatment pairs.")

    st.markdown("**Observed Clinical Symptom Clusters (Tick all present):**")
    sc1, sc2, sc3 = st.columns(3)
    
    selected_symptoms = []

    with sc1:
        st.caption("Affective & Psychological")
        if st.checkbox("Persistent low mood / Dysphoria", value=True):
            selected_symptoms.append("Persistent low mood")
        if st.checkbox("Separation distress / Intense yearning", value=True):
            selected_symptoms.append("Separation distress & yearning")
        if st.checkbox("Anhedonia / Loss of pleasure or motivation"):
            selected_symptoms.append("Anhedonia / Loss of pleasure")
        if st.checkbox("Excessive guilt / Feelings of worthlessness"):
            selected_symptoms.append("Excessive guilt & worthlessness")
        if st.checkbox("Emotional numbness / Dissociative detachment"):
            selected_symptoms.append("Emotional numbness & detachment")
        if st.checkbox("Preoccupation with loss / Rumination"):
            selected_symptoms.append("Loss-related rumination")

    with sc2:
        st.caption("Somatic & Vegetative")
        if st.checkbox("Sleep disruption (Initial/Terminal insomnia)", value=True):
            selected_symptoms.append("Sleep disruption / Insomnia")
        if st.checkbox("Chronic fatigue / Loss of physical energy"):
            selected_symptoms.append("Chronic fatigue / Energy loss")
        if st.checkbox("Muscle tension / Tension headaches / Body aches"):
            selected_symptoms.append("Somatic muscle tension & headaches")
        if st.checkbox("Autonomic arousal (Palpitations / Dyspnea / Tremors)"):
            selected_symptoms.append("Autonomic anxiety arousal")
        if st.checkbox("Gastrointestinal distress / Appetite alterations"):
            selected_symptoms.append("Gastrointestinal / Appetite changes")
        if st.checkbox("Psychomotor agitation or retardation"):
            selected_symptoms.append("Psychomotor changes")

    with sc3:
        st.caption("Neurocognitive & Trauma/Functional")
        if st.checkbox("Executive dysfunction / Brain fog / Focus lapses"):
            selected_symptoms.append("Concentration & executive lapses")
        if st.checkbox("Working memory deficits / Forgetfulness"):
            selected_symptoms.append("Working memory deficits")
        if st.checkbox("Hyperarousal / Hypervigilance / Panic reactivity"):
            selected_symptoms.append("Hyperarousal & hypervigilance")
        if st.checkbox("Avoidance behaviour (Reminders / Situations / People)"):
            selected_symptoms.append("Active avoidance behaviour")
        if st.checkbox("Intrusive memories / Traumatic flashbacks"):
            selected_symptoms.append("Intrusive recollections")
        if st.checkbox("Occupational / Academic / Relational impairment"):
            selected_symptoms.append("Functional occupational/relational impairment")

    if not selected_symptoms:
        selected_symptoms = ["Bereavement-related adjustment difficulties"]

    st.markdown("---")
    st.markdown("**Therapeutic Modality & Billing Tariff:**")
    modality = st.selectbox("Primary Therapeutic Modality:", scope_info.get("modalities", ["Cognitive Behavioural Framework"]))
    
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
        # Resolve variables safely if defined earlier, otherwise provide clean defaults
        _default_scheme = locals().get("scheme_name") or st.session_state.get("scheme_name", "")
        _default_mem_no = locals().get("membership_no") or st.session_state.get("membership_no", "")
        _default_dep = locals().get("dependant_code") or st.session_state.get("dependant_code", "00")
        _default_patient = locals().get("patient_name") or st.session_state.get("patient_name", "")
        _default_is_pmb = locals().get("is_pmb_default", True)
        _default_pre_auth = locals().get("pre_auth") or st.session_state.get("pre_auth", "")

        with st.container(border=True):
            st.markdown("##### 📋 Medical Aid Claim Voucher Sticker")
            stk_c1, stk_c2 = st.columns(2)
            with stk_c1:
                stk_scheme = st.text_input("Scheme Name", value=_default_scheme)
                stk_mem_no = st.text_input("Membership Number", value=_default_mem_no)
                stk_dep = st.text_input("Dependant Code", value=_default_dep)
            with stk_c2:
                main_member_val = f"{_default_patient} (Self)" if _default_patient else ""
                main_member = st.text_input("Main Member Initial/Surname", value=main_member_val)
                pre_auth = st.text_input("Pre-Authorisation Number (if issued)", value=_default_pre_auth)
                is_pmb = st.checkbox("Prescribed Minimum Benefit (PMB)", value=_default_is_pmb)

        sticker_data = {
            "scheme": stk_scheme,
            "membership_no": stk_mem_no,
            "dependant_code": stk_dep,
            "main_member": main_member,
            "pre_auth": pre_auth,
            "is_pmb": is_pmb
        }

# === COLUMN 2: REVIEW, CUSTOMIZE & EXPORT ===
with col_right:
    st.subheader(f"2. {report_type} Content")

    # Date-stamped Session Progression Log configuration
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        start_date = st.date_input("First Session Date:", datetime.date.today() - datetime.timedelta(days=21))
    with d_col2:
        session_count = st.slider("Documented Sessions (Up to 20):", min_value=1, max_value=20, value=4)

    session_dates = []
    curr_date = start_date
    while len(session_dates) < session_count:
        # If start date falls on a weekend, shift to the upcoming Monday
# Check if start date falls on a weekend, roll forward to Monday
        if curr_date.weekday() >= 5:
            curr_date += datetime.timedelta(days=(7 - curr_date.weekday()))

        session_dates = [
            curr_date + datetime.timedelta(days=7 * i)
            for i in range(int(session_count))
        ]

    # GENERATE / RE-SYNTHESIZE BUTTON
    if st.button("🔄 Generate / Re-synthesize Report Content", type="primary", use_container_width=True):
        generated = synthesize_clinical_narrative(
            designation=designation,
            icd10=icd10,
            modality=modality,
            symptoms=selected_symptoms,
            session_count=session_count,
            dates=session_dates
        )
        st.session_state["dyn_trajectory"] = generated["trajectory"]
        st.session_state["dyn_adherence"] = generated["adherence"]
        st.session_state["dyn_barriers"] = generated["barriers"]
        st.session_state["dyn_sessions"] = generated["sessions"]

    # Initial Fallback State
    if "dyn_trajectory" not in st.session_state:
        init_gen = synthesize_clinical_narrative(
            designation=designation,
            icd10=icd10,
            modality=modality,
            symptoms=selected_symptoms,
            session_count=session_count,
            dates=session_dates
        )
        st.session_state["dyn_trajectory"] = init_gen["trajectory"]
        st.session_state["dyn_adherence"] = init_gen["adherence"]
        st.session_state["dyn_barriers"] = init_gen["barriers"]
        st.session_state["dyn_sessions"] = init_gen["sessions"]

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
                    content_str = st.text_area(f"Clinical Note (S{i})", value=sess["content"], key=f"note_{i}", height=70)

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
        
        req_sessions = st.number_input("Requested Sessions for Authorization:", min_value=1, max_value=20, value=6)
        goals = st.text_area(
            "Goals of Sessions:",
            value=f"1. Symptom reduction targeting {', '.join(selected_symptoms[:2])}.\n2. Development of emotional regulation, meaning reconstruction, and coping resilience.\n3. Restoration of baseline psychosocial functioning.",
            height=80
        )
        interventions = st.text_area(
            "Interventions Used / Planned:",
            value=f"Structured {modality} protocols including psycho-education, cognitive/emotional reappraisal, Dual-Process grief tracking, and coping integration.",
            height=80
        )
        outcomes = st.text_area(
            "Expected Measurable Outcomes:",
            value="Observed reduction on standardized distress markers, improved engagement in daily occupations, and stabilized affect.",
            height=80
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
        summary_text = st.text_area(
            "Course of Treatment & Summary:",
            value=f"Client completed therapeutic cycle targeting {icd10}. Observable stabilization achieved across {', '.join(selected_symptoms[:2])}.",
            height=100
        )
        discharge_plan = st.text_area(
            "Discharge Recommendations / Relapse Prevention:",
            value="Discharged with maintenance coping strategies. Client educated on self-referral procedures should acute bereavement or distress triggers resurface.",
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
    file_base = f"{report_type.replace(' ', '_')}_{case_number}_{date_str}"

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