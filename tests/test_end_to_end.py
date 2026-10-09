import io
import pytest
from core.pdf_builder import build_clinical_pdf
from app import build_docx_report


@pytest.fixture
def mock_payload():
    practitioner = {
        "name": "Dr. J. Doe",
        "designation": "Registered Counsellor (HPCSA)",
        "address": "Suite 4, Mediclinic Building, Sandton",
        "practice_number": "PR 0810001",
    }
    patient = {
        "patient_name": "Jane Citizen",
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
    content_data = {
        "trajectory": "Client shows consistent engagement.",
        "adherence": "High attendance compliance.",
        "barriers": "Situational workplace strain.",
        "goals": "Reduce affective distress.",
        "interventions": "Psycho-education and behavioural activation.",
        "outcomes": "Reduction in depressive markers.",
        "requested_sessions": 6,
        "sessions": [
            {
                "num": 1,
                "date": "2026-09-01",
                "symptom_target": "Intake",
                "content": "Intake baseline.",
            },
            {
                "num": 2,
                "date": "2026-09-08",
                "symptom_target": "Sleep",
                "content": "Sleep hygiene protocol.",
            },
        ],
    }
    sticker_data = {
        "scheme": "Discovery Health",
        "membership_no": "902148291",
        "dependant_code": "00",
        "main_member": "Jane Citizen (Self)",
        "is_pmb": False,
        "pre_auth": "AUTH-12345",
    }
    return practitioner, patient, billing, content_data, sticker_data


@pytest.mark.parametrize("report_type", [
    "Clinical Progress Report",
    "Treatment Plan / Authorisation Request",
    "Clinical Summary / Discharge Note"
])
def test_pdf_generation_all_report_types(report_type, mock_payload):
    practitioner, patient, billing, content_data, sticker_data = mock_payload

    pdf_buffer = build_clinical_pdf(
        report_type=report_type,
        practitioner=practitioner,
        patient=patient,
        billing=billing,
        content_data=content_data,
        sticker_data=sticker_data,
    )

    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 0
    # PDF binary header check
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.parametrize("report_type", [
    "Clinical Progress Report",
    "Treatment Plan / Authorisation Request",
    "Clinical Summary / Discharge Note"
])
def test_docx_generation_all_report_types(report_type, mock_payload):
    practitioner, patient, billing, content_data, sticker_data = mock_payload

    docx_buffer = build_docx_report(
        report_type=report_type,
        practitioner=practitioner,
        patient=patient,
        billing=billing,
        content_data=content_data,
        sticker_data=sticker_data,
    )

    assert isinstance(docx_buffer, io.BytesIO)
    docx_bytes = docx_buffer.getvalue()
    assert len(docx_bytes) > 0
    # ZIP / DOCX magic bytes check (PK\x03\x04)
    assert docx_bytes.startswith(b"PK\x03\x04")