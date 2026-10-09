import datetime
import pytest
from core.clinical_logic import (
    SCOPE_GUIDELINES,
    get_scope_guidelines,
    validate_scope,
    synthesize_clinical_narrative,
)


def test_all_five_disciplines_exist():
    expected_disciplines = [
        "Registered Counsellor (HPCSA)",
        "Social Worker (SACSSP)",
        "Educational Psychologist (HPCSA)",
        "Counselling Psychologist (HPCSA)",
        "Clinical Psychologist (HPCSA)",
    ]
    for disc in expected_disciplines:
        assert disc in SCOPE_GUIDELINES
        info = get_scope_guidelines(disc)
        assert "allowed_tariffs" in info
        assert "modalities" in info
        assert "council" in info


def test_scope_validation_catches_unauthorized_terms():
    # Registered Counsellors should not perform formal psychiatric formulations or personality disorder diagnoses
    rc_text = "Conducted a formal psychiatric formulation and completed a personality disorder diagnosis."
    flags = validate_scope("Registered Counsellor (HPCSA)", rc_text)
    assert "formal psychiatric formulation" in flags
    assert "personality disorder diagnosis" in flags

    # Social Workers should not perform psychometric evaluations
    sw_text = "Administered formal psychometric assessment and formal IQ evaluation."
    sw_flags = validate_scope("Social Worker (SACSSP)", sw_text)
    assert "psychometric assessment" in sw_flags
    assert "formal iq evaluation" in sw_flags


def test_scope_validation_passes_clean_narrative():
    safe_text = "Provided supportive counselling, grief psycho-education, and structured behavioral activation."
    flags = validate_scope("Registered Counsellor (HPCSA)", safe_text)
    assert len(flags) == 0


def test_bereavement_narrative_generation():
    dates = [
        datetime.date.today() - datetime.timedelta(days=7 * i)
        for i in reversed(range(4))
    ]
    symptoms = [
        "Separation distress & yearning",
        "Persistent low mood",
        "Sleep disruption / Insomnia",
    ]

    # Test Registered Counsellor grief narrative
    rc_result = synthesize_clinical_narrative(
        designation="Registered Counsellor (HPCSA)",
        icd10="Z63.4 - Disappearance and death of family member (Uncomplicated Bereavement)",
        modality="Person-Centred Supportive Counselling",
        symptoms=symptoms,
        session_count=4,
        dates=dates,
    )

    assert "bereavement-related distress" in rc_result["trajectory"].lower()
    assert "adherence" in rc_result
    assert "barriers" in rc_result
    assert len(rc_result["sessions"]) == 4

    # Test Clinical Psychologist prolonged grief narrative
    cp_result = synthesize_clinical_narrative(
        designation="Clinical Psychologist (HPCSA)",
        icd10="F43.8 - Other reactions to severe stress (Prolonged Grief Reaction)",
        modality="Complicated Grief Therapy (CGT)",
        symptoms=symptoms,
        session_count=4,
        dates=dates,
    )
    assert "prolonged grief" in cp_result["trajectory"].lower() or "psychopathology" in cp_result["trajectory"].lower()