"""
core/medical_aid_presets.py
Medical Scheme Specific Compliance Rules, Routing Protocols & Submission Endpoints
for South African Mental Health Service Authorizations.
"""

SCHEME_PRESETS = {
    "Discovery Health": {
        "admin_name": "Discovery Health Medical Scheme (DHMS)",
        "email_portal": "mentalhealth@discovery.co.za / Discovery Provider Portal",
        "default_batch_limit": 6,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Application motivated under Prescribed Minimum Benefit (PMB) Code 907T / DTP pairing. "
            "Evidence of functional impairment and formal multidisciplinary referral supplied."
        ),
        "requires_referring_pr": True,
        "care_programme": "Mental Health Care Programme (MHCP)",
        "guidance_note": (
            "Discovery requires the Referring Medical Practitioner's BHF Practice Number. "
            "For PMB claims, ensure primary diagnostic formulation meets DTP criteria. "
            "Uncomplicated Z-codes will debit Day-to-Day / Savings accounts only."
        ),
        "submission_subject": "AUTHORISATION REQUEST: {membership_no} - {patient_name} - {tariff_code}",
    },
    "GEMS (Government Employees)": {
        "admin_name": "GEMS Managed Care",
        "email_portal": "enquiries@gems.gov.za / Prime Cure Managed Healthcare",
        "default_batch_limit": 6,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Outpatient psychotherapy/counselling motivation for GEMS PMB review. "
            "Demonstrates symptom severity and structured treatment intervention milestones."
        ),
        "requires_referring_pr": True,
        "care_programme": "GEMS Managed Mental Healthcare Programme",
        "guidance_note": (
            "GEMS restricts initial outpatient psychotherapy and supportive counselling to batches of 6 sessions. "
            "Progress reviews must explicitly highlight functional scores and symptom reduction to grant extensions."
        ),
        "submission_subject": "GEMS MENTAL HEALTH AUTHORISATION: {membership_no} ({dependant_code})",
    },
    "Medscheme (Bonitas / Polmed / Fedhealth / Nedgroup)": {
        "admin_name": "Medscheme Managed Healthcare",
        "email_portal": "psychauth@medscheme.co.za",
        "default_batch_limit": 8,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Clinical motivation for Medscheme mental health benefit basket and step-down management. "
            "Focused on objective barrier reduction and symptom stabilization."
        ),
        "requires_referring_pr": False,
        "care_programme": "Medscheme Mental Health Programme",
        "guidance_note": (
            "Medscheme evaluates applications on functional impairment and structured step-down planning. "
            "Ensure concrete maintenance strategies and measurable milestones are specified."
        ),
        "submission_subject": "AUTH SUBMISSION: Medscheme Mental Health - {membership_no}",
    },
    "Momentum Health": {
        "admin_name": "Momentum Health Solutions",
        "email_portal": "mentalhealth@momentum.co.za",
        "default_batch_limit": 6,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Pre-authorisation motivation adhering to Momentum dedicated mental health network criteria. "
            "Documented clinical evaluation and risk containment strategy included."
        ),
        "requires_referring_pr": False,
        "care_programme": "Momentum Mental Health Dedicated Programme",
        "guidance_note": (
            "Verify whether member plan utilizes the Associated or Any Provider Network. "
            "Out-of-network claims may result in member co-payments unless PMB exemption applies."
        ),
        "submission_subject": "MOMENTUM PRE-AUTH: {membership_no} - {patient_name}",
    },
    "Bestmed": {
        "admin_name": "Bestmed Medical Scheme",
        "email_portal": "precert@bestmed.co.za",
        "default_batch_limit": 6,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Outpatient psychotherapy motivation submitted for Bestmed chronic mental health benefit review. "
            "Treating practitioner progress evaluation and DSM-5 alignment verified."
        ),
        "requires_referring_pr": False,
        "care_programme": "Bestmed Managed Care Programme",
        "guidance_note": (
            "Include primary and secondary ICD-10 diagnostic codes. "
            "Standard psychotherapy entitlements are scheme-option dependent."
        ),
        "submission_subject": "BESTMED PRE-AUTHORISATION: {membership_no}",
    },
    "Other / Private Rate": {
        "admin_name": "Independent Medical Scheme / Private Healthcare",
        "email_portal": "Direct Member Submission / Portal",
        "default_batch_limit": 6,
        "default_tariff": "81305",
        "max_pmb_sessions": 15,
        "pmb_motivation_note": (
            "Standard clinical PMB motivation and statutory diagnostic treatment plan. "
            "Compliant with Council for Medical Schemes (CMS) guidelines."
        ),
        "requires_referring_pr": False,
        "care_programme": "General Outpatient Mental Health",
        "guidance_note": "Standard HPCSA/SACSSP compliant clinical billing formulation applies.",
        "submission_subject": "CLINICAL TREATMENT PLAN & CLAIM MOTIVATION: {patient_name}",
    },
}


def get_scheme_preset(scheme_name: str) -> dict:
    """Returns compliance settings for the given scheme, with a safe fallback."""
    for key, val in SCHEME_PRESETS.items():
        if scheme_name.lower() in key.lower():
            return val
    return SCHEME_PRESETS["Other / Private Rate"]


COMMON_ICD10_CODES = [
    {"code": "Z63.4", "desc": "Disappearance and death of family member (Uncomplicated Bereavement)"},
    {"code": "F43.8", "desc": "Other reactions to severe stress (Prolonged Grief Reaction)"},
    {"code": "F43.21", "desc": "Adjustment disorder with depressed mood"},
    {"code": "F43.22", "desc": "Adjustment disorder with anxiety"},
    {"code": "F43.23", "desc": "Adjustment disorder with mixed anxiety and depressed mood"},
    {"code": "F43.10", "desc": "Post-traumatic stress disorder, unspecified"},
    {"code": "F43.0", "desc": "Acute stress reaction"},
    {"code": "F32.0", "desc": "Mild depressive episode"},
    {"code": "F32.1", "desc": "Moderate depressive episode"},
    {"code": "F32.2", "desc": "Severe depressive episode without psychotic symptoms"},
    {"code": "F33.1", "desc": "Recurrent depressive disorder, current episode moderate"},
    {"code": "F34.1", "desc": "Dysthymia / Persistent Depressive Disorder"},
    {"code": "F31.9", "desc": "Bipolar affective disorder, unspecified"},
    {"code": "F41.1", "desc": "Generalized anxiety disorder"},
    {"code": "F41.0", "desc": "Panic disorder"},
    {"code": "F40.1", "desc": "Social phobia"},
    {"code": "F42.2", "desc": "Mixed obsessional thoughts and acts (OCD)"},
    {"code": "F45.0", "desc": "Somatization disorder"},
    {"code": "F90.0", "desc": "Disturbance of activity and attention (ADHD)"},
    {"code": "F90.2", "desc": "Combined type ADHD"},
    {"code": "F81.0", "desc": "Specific reading disorder / Dyslexia"},
    {"code": "F91.3", "desc": "Oppositional defiant disorder"},
    {"code": "F93.0", "desc": "Separation anxiety disorder of childhood"},
    {"code": "Z63.0", "desc": "Problems in relationship with spouse or partner"},
    {"code": "Z63.8", "desc": "Other specified problems related to primary support group"},
    {"code": "Z73.0", "desc": "Burn-out / State of vital exhaustion"},
    {"code": "Z56.6", "desc": "Other physical and mental strain related to work"},
    {"code": "Z55.9", "desc": "Problems related to education and literacy, unspecified"},
]