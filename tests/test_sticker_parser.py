from core.sticker_parser import parse_patient_sticker_text

def test_parse_standard_sa_sticker():
    sample_ocr = """
    NETCARE SUNNINGHILL HOSPITAL
    DOE, JANE
    ID: 9201010000080
    MEM NO: 123456789 DEP: 01
    ADM: 30/03/2026
    REF DR: MOKWATSI
    """
    result = parse_patient_sticker_text(sample_ocr)

    assert result["patient_id"] == "9201010000080"
    assert result["membership_number"] == "123456789"
    assert result["dependant_code"] == "01"
    assert result["admission_date"] == "30/03/2026"
    assert "MOKWATSI" in result["referring_dr"].upper()