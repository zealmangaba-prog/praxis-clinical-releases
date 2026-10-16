"""
core/pdf_builder.py
Dynamic, Locked PDF Builder using ReportLab.
Supports:
  - Clinical Progress Report (with up to 20-session table, adherence, barriers)
  - Treatment Plan / Authorisation Request (goals, interventions, outcomes)
  - Clinical Summary / Discharge Note
  - Always-present patient demographics table
  - Optional Medical Aid Claim Voucher
"""

import io
import datetime
from reportlab.platypus import Image 
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def build_clinical_pdf(
    report_type: str,
    practitioner: dict,
    patient: dict,
    billing: dict,
    content_data: dict,
    sticker_data: dict = None
) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=2
    )

    sub_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8
    )

    sec_header_style = ParagraphStyle(
        "SecHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    cell_bold_style = ParagraphStyle(
        "CellTextBold",
        parent=cell_style,
        fontName="Helvetica-Bold"
    )

    story = []

    # 1. Professional Header & Letterhead
    # Format title cleanly without duplicate 'CLINICAL' prefix
    clean_title = report_type.upper().strip()
    if not clean_title.startswith('CLINICAL'):
        clean_title = f'CLINICAL {clean_title}'
    story.append(Paragraph(clean_title, title_style))
    story.append(Spacer(1, 4))

    # Structured Practitioner Letterhead Block
    prac_html = (
        f"<b><font size='10.5'>{practitioner.get('name', '')}</font></b> | "
        f"<font color='#444444'>{practitioner.get('designation', '')}</font><br/>"
        f"<b>BHF Practice No:</b> {practitioner.get('practice_number', 'N/A')} &nbsp;|&nbsp; "
        f"<b>Tel:</b> {practitioner.get('phone', 'N/A')} &nbsp;|&nbsp; "
        f"<b>Email:</b> {practitioner.get('email', 'N/A')}<br/>"
        f"<b>Rooms:</b> {practitioner.get('address', 'N/A')}"
    )
    story.append(Paragraph(prac_html, sub_style))
    story.append(Spacer(1, 10))

    # 2. ALWAYS-PRESENT: Patient Demographics Block (Single Column, No Table)
    doctor_ref_str = patient.get('doctor', 'N/A')
    if patient.get('doctor_pr'):
        doctor_ref_str += f" (BHF: {patient['doctor_pr']})"

    # Format Admission and Discharge Dates
    adm_val = patient.get('admission_date')
    if hasattr(adm_val, 'strftime'):
        adm_date_str = adm_val.strftime("%Y-%m-%d")
    else:
        adm_date_str = str(adm_val) if adm_val else "N/A"

    dis_val = patient.get('discharge_date')
    if hasattr(dis_val, 'strftime'):
        dis_date_str = dis_val.strftime("%Y-%m-%d")
    elif dis_val:
        dis_date_str = str(dis_val)
    else:
        dis_date_str = "Ongoing / Active Impatient" 
        
    demo_lines = [
        f"<b>Patient Name / ID:</b> {patient['patient_name']} ({patient['case_number']})",
        f"<b>Referring Doctor:</b> {doctor_ref_str}",
        f"<b>Admission Date:</b> {adm_date_str}",
        f"<b>Discharge Date:</b> {dis_date_str}",
        f"<b>Medical Scheme:</b> {patient.get('scheme', 'N/A')}",
        f"<b>Membership Number:</b> {patient.get('membership_no', 'N/A')}",
        f"<b>Dependant Code:</b> {patient.get('dependant_code', '00')}"
    ]
    if patient.get('care_programme'):
        demo_lines.append(f"<b>Care Programme Routing:</b> {patient['care_programme']}")

    for line in demo_lines:
        story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 6))

    # 3. Dedicated Medical Aid Claim Voucher (Reserved for the Sticker Only)
    if sticker_data:
        pmb_flag = "YES (PMB Statutory Benefit)" if sticker_data.get("is_pmb") else "NO (Standard Scheme Benefit)"
        auth_str = f" | Pre-Auth: {sticker_data.get('pre_auth', '')}" if sticker_data.get("pre_auth") else ""
        sess_quoted = len(content_data.get("sessions", [])) if "sessions" in content_data else content_data.get("requested_sessions", "N/A")

        sticker_rows = [
            [
                Paragraph("<b>MEDICAL AID CLAIM VOUCHER / AUTHORISATION SUMMARY</b>", ParagraphStyle("WhiteHdr", parent=cell_bold_style, textColor=colors.white)),
                ""
            ],
            [
                Paragraph(f"<b>SCHEME:</b> {sticker_data['scheme']}<br/><b>MEMBERSHIP NO:</b> {sticker_data['membership_no']}", cell_style),
                Paragraph(f"<b>MAIN MEMBER:</b> {sticker_data['main_member']}<br/><b>DEP CODE:</b> {sticker_data['dependant_code']}", cell_style)
            ],
            [
                Paragraph(f"<b>ICD-10 PRIMARY:</b> {billing['icd10']}", cell_style),
                Paragraph(f"<b>PMB STATUS:</b> {pmb_flag}{auth_str}", cell_style)
            ],
            [
                Paragraph(f"<b>TARIFF:</b> {billing['tariff_code']} - {billing['tariff_desc']}", cell_style),
                Paragraph(f"<b>SESSIONS QUOTED / COMPLETED:</b> {sess_quoted}", cell_style)
            ]
        ]
        t_stk = Table(sticker_rows, colWidths=[260, 260])
        t_stk.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#1E293B")),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
            ('BACKGROUND', (0, 2), (-1, 2), colors.white),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_stk)
        story.append(Spacer(1, 8))

    # 4. Clinical Presentation
    story.append(Paragraph("1. Clinical Formulation & Presentation", sec_header_style))
    pres_text = (
        f"<b>Primary Diagnostic Code (ICD-10):</b> {billing['icd10']}<br/>"
        f"<b>Target Symptoms / Presentation:</b> {', '.join(patient['symptoms'])}<br/>"
        f"<b>Therapeutic Modality:</b> {patient['modality']}"
    )
    story.append(Paragraph(pres_text, body_style))
    story.append(Spacer(1, 4))

    # 5. Dynamic Section Based on Report Type
    if report_type == "Clinical Progress Report":
        story.append(Paragraph("2. Clinical Trajectory & Progress Evaluation", sec_header_style))
        story.append(Paragraph(content_data.get("trajectory", ""), body_style))
        story.append(Spacer(1, 4))

        adh_text = f"<b>Treatment Adherence & Engagement:</b> {content_data.get('adherence', '')}"
        barr_text = f"<b>Ongoing Challenges & Barriers:</b> {content_data.get('barriers', '')}"
        story.append(Paragraph(adh_text, body_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(barr_text, body_style))
        story.append(Spacer(1, 6))

        # Session table
        sessions = content_data.get("sessions", [])
        if sessions:
            story.append(Paragraph("Service Dates & Symptom-Linked Progress Log", sec_header_style))
            sess_table_data = [
                [
                    Paragraph("<b>#</b>", cell_bold_style),
                    Paragraph("<b>Date</b>", cell_bold_style),
                    Paragraph("<b>Tariff</b>", cell_bold_style),
                    Paragraph("<b>Symptom Focus</b>", cell_bold_style),
                    Paragraph("<b>Clinical Observations & Content</b>", cell_bold_style)
                ]
            ]
            for s in sessions:
                sess_table_data.append([
                    Paragraph(str(s["num"]), cell_style),
                    Paragraph(s["date"], cell_style),
                    Paragraph(billing["tariff_code"], cell_style),
                    Paragraph(s["symptom_target"], cell_style),
                    Paragraph(s["content"], cell_style)
                ])

            t_sess = Table(sess_table_data, colWidths=[20, 55, 45, 130, 270])
            t_sess.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_sess)

    elif report_type == "Treatment Plan / Authorisation Request":
        story.append(Paragraph("2. Treatment Goals, Clinical Interventions & Expected Outcomes", sec_header_style))
        
        tp_text = (
            f"<b>Goals of Sessions:</b><br/>{content_data.get('goals', '').replace(chr(10), '<br/>')}<br/><br/>"
            f"<b>Specific Therapeutic Interventions:</b><br/>{content_data.get('interventions', '').replace(chr(10), '<br/>')}<br/><br/>"
            f"<b>Expected Measurable Outcomes:</b><br/>{content_data.get('outcomes', '').replace(chr(10), '<br/>')}<br/><br/>"
            f"<b>Sessions Requested for Authorisation:</b> {content_data.get('requested_sessions', 6)} sessions under tariff {billing['tariff_code']}."
        )
        story.append(Paragraph(tp_text, body_style))

    else:  # Clinical Summary / Discharge Note
        story.append(Paragraph("2. Treatment Summary & Discharge Evaluation", sec_header_style))
        sum_text = (
            f"<b>Course of Treatment & Clinical Outcomes:</b><br/>{content_data.get('summary_text', '').replace(chr(10), '<br/>')}<br/><br/>"
            f"<b>Discharge Recommendations & Relapse Prevention:</b><br/>{content_data.get('discharge_plan', '').replace(chr(10), '<br/>')}"
        )
        story.append(Paragraph(sum_text, body_style))

    story.append(Spacer(1, 6))

    # 6. Recommendation & Motivation
    story.append(Paragraph("3. Professional Motivation & Authorisation", sec_header_style))
    rec_text = (
        f"In accordance with clinical protocol under {practitioner['designation']}, "
        f"therapeutic services under tariff {billing['tariff_code']} are motivated "
        f"to maintain psychosocial stability, consolidate treatment gains, and prevent symptom regression."
    )
    story.append(Paragraph(rec_text, body_style))
    story.append(Spacer(1, 14))

    # 7. Signature Block
    from PIL import Image as PILImage
    from reportlab.platypus import Image as RLImage

    sig_block = []
    sig_data = practitioner.get("signature")

    if sig_data:
        try:
            pil_img = PILImage.open(io.BytesIO(sig_data))
            if pil_img.mode in ("RGBA", "LA", "P"):
                pil_img = pil_img.convert("RGBA")
                bg = PILImage.new("RGB", pil_img.size, (255, 255, 255))
                bg.paste(pil_img, mask=pil_img.split()[3])
                pil_img = bg
            else:
                pil_img = pil_img.convert("RGB")

            img_buf = io.BytesIO()
            pil_img.save(img_buf, format="PNG")
            img_buf.seek(0)

            sig_img = RLImage(img_buf, width=130, height=45)
            sig_img.hAlign = "LEFT"
            sig_block.append(sig_img)
            sig_block.append(Spacer(1, 4))
        except Exception as e:
            print(f"Signature error: {e}")
            sig_block.append(Paragraph("________________________________________", body_style))
    else:
        sig_block.append(Paragraph("________________________________________", body_style))

    sig_block.extend([
        Paragraph(f"<b>{practitioner.get('name', '')}</b>", body_style),
        Paragraph(practitioner.get('designation', ''), body_style),
        Paragraph(f"BHF Practice No: {practitioner.get('practice_number', '')}", body_style)
    ])
    story.append(KeepTogether(sig_block))

    doc.build(story)
    buffer.seek(0)
    return buffer