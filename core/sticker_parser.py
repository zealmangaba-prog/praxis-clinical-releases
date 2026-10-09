"""
Heuristic and regular expression parsing for patient sticker demographic fields.
Designed specifically for South African clinical formats.
"""
import re
from typing import Dict, Any

def parse_patient_sticker_text(raw_text: str) -> Dict[str, Any]:
    """
    Parses unstructured text extracted from a hospital/clinic sticker.
    Extracts Full Name, 13-digit ID, Medical Aid/Member No, Dependant Code,
    Dates, and Doctor references.
    """
    parsed = {
        "patient_name": "",
        "patient_id": "",
        "membership_number": "",
        "dependant_code": "00",
        "admission_date": "",
        "referring_dr": "",
    }

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # 1. South African 13-digit National ID (YYMMDDSSSSCAZ)
    id_match = re.search(r'\b(\d{13})\b', raw_text)
    if id_match:
        parsed["patient_id"] = id_match.group(1)

    # 2. Medical Aid Membership Number / Policy Number
    mem_match = re.search(
        r'(?:MEM(?:BERSHIP)?(?:\s+NO)?|MED\s*AID|POL(?:ICY)?)\s*[:#\-]?\s*([A-Z0-9]{5,12})',
        raw_text,
        re.IGNORECASE,
    )
    if mem_match:
        parsed["membership_number"] = mem_match.group(1).strip()

    # 3. Dependant Code (e.g., 00, 01, 02)
    dep_match = re.search(
        r'(?:DEP(?:ENDANT)?(?:\s+CODE)?)\s*[:#\-]?\s*(\d{2})',
        raw_text,
        re.IGNORECASE,
    )
    if dep_match:
        parsed["dependant_code"] = dep_match.group(1).strip()

    # 4. Dates (DD/MM/YYYY or YYYY-MM-DD or DD-MM-YYYY)
    date_match = re.search(
        r'\b(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b',
        raw_text,
    )
    if date_match:
        raw_date = date_match.group(1).replace("-", "/")
        parts = raw_date.split("/")
        if len(parts[0]) == 4:
            parsed["admission_date"] = f"{parts[2]}/{parts[1]}/{parts[0]}"
        else:
            parsed["admission_date"] = raw_date

    # 5. Referring Doctor (handles "REF DR: MOKWATSI", "DOCTOR SMITH", "DR. J. MOKWATSI")
    dr_match = re.search(
        r'(?:REF(?:ERRING)?\s*(?:DR|DOCTOR)?\s*[:\-]?\s*|DR\.?\s+|DOCTOR\s+)(?:DR\.?\s*)?([A-Za-z]+(?:\s+[A-Za-z]+)?)',
        raw_text,
        re.IGNORECASE,
    )
    if dr_match:
        dr_name = dr_match.group(1).strip()
        # Clean out any stray punctuation or prefixes
        dr_name = re.sub(r'^(?:DR\.?|DOCTOR)\s*', '', dr_name, flags=re.IGNORECASE).strip()
        if dr_name:
            parsed["referring_dr"] = f"Dr {dr_name.title()}"

    # 6. Patient Name Heuristic
    name_match = re.search(
        r'(?:PATIENT|NAME|PT)\s*[:#\-]?\s*([A-Za-z\s,]{3,35})',
        raw_text,
        re.IGNORECASE,
    )
    if name_match:
        candidate_name = name_match.group(1).strip()
        parsed["patient_name"] = re.sub(r'\d+', '', candidate_name).strip()
    elif lines:
        for line in lines[:3]:
            cleaned_line = line.strip()
            if (
                re.match(r'^[A-Za-z\s,]{4,}$', cleaned_line)
                and not any(
                    kw in cleaned_line.upper()
                    for kw in ["HOSPITAL", "CLINIC", "WARD", "ADMISSION", "MEMBER", "NETCARE"]
                )
            ):
                parsed["patient_name"] = cleaned_line
                break

    return parsed