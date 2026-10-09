from core.medical_aid_presets import SCHEME_PRESETS, COMMON_ICD10_CODES

def test_scheme_presets_validity():
    assert "Discovery Health" in SCHEME_PRESETS
    assert "GEMS (Government Employees)" in SCHEME_PRESETS
    
    discovery = SCHEME_PRESETS["Discovery Health"]
    assert discovery["default_tariff"] == "81305"
    assert discovery["max_pmb_sessions"] == 15
    assert len(discovery["pmb_motivation_note"]) > 20

def test_common_icd10_codes_present():
    codes = [item["code"] for item in COMMON_ICD10_CODES]
    assert "F32.2" in codes
    assert "F41.1" in codes
    assert "Z63.4" in codes