import io
import datetime
import pytest
from core.pdf_builder import build_clinical_pdf
from core.clinical_logic import calculate_session_dates


def test_pdf_rendering_structure():
    practitioner = {
        "name": "Dr. J. Doe",
        "designation": "Registered Counsellor (HPCSA)",
        "address": "Suite 4, Mediclinic Building, Sandton",
        "practice_number": "PR 0810001",
    }
    patient = {
        "patient_name": "Test Client",
        "case_number": "CLIN-2026-TEST",
        "doctor": "Dr. M. Peterson",
        "scheme": "Discovery Health",
        "membership_no": "902148291",
        "dependant_code": "00",
        "admission_date": "2026-09-01",
        "discharge_date": "N/A",
        "modality": "Cognitive Behavioural Framework",
        "symptoms": ["Persistent low mood", "Sleep disruption / Insomnia"],
    }
    billing = {
        "icd10": "F32.0 - Mild Depressive Episode",
        "tariff_code": "81305",
        "tariff_desc": "Individual Supportive Session",
    }
    dates = calculate_session_dates(datetime.date(2026, 9, 1), 3)
    content_data = {
        "trajectory": "Client shows consistent engagement and progress.",
        "adherence": "High attendance compliance.",
        "barriers": "Situational workplace strain.",
        "sessions": [
            {
                "num": idx + 1,
                "date": d.strftime("%Y-%m-%d"),
                "symptom_target": "Symptom Focus",
                "content": "Clinical observations and progress recorded.",
            }
            for idx, d in enumerate(dates)
        ],
    }

    pdf_buffer = build_clinical_pdf(
        report_type="Clinical Progress Report",
        practitioner=practitioner,
        patient=patient,
        billing=billing,
        content_data=content_data,
        sticker_data=None,
    )

    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")