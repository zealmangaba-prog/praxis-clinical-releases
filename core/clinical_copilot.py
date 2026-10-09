"""
core/clinical_copilot.py
Offline Clinical Synthesis & Formulations Engine
Aligns clinical text with HPCSA / SACSSP scopes and medical aid audit expectations.
"""
from typing import List, Dict

def synthesize_session_notes(
    discipline: str,
    modality: str,
    selected_symptoms: List[str],
    service_dates: List[str]
) -> List[Dict[str, str]]:
    """
    Generates structured, symptom-linked session progression notes.
    """
    total = len(service_dates)
    symptom_pool = selected_symptoms if selected_symptoms else ["General Psychosocial Functioning"]
    sessions = []

    for idx, dt_str in enumerate(service_dates, start=1):
        if idx == 1:
            target = "Intake & Baseline Risk Screening"
            content = (
                f"Initial clinical consultation. Baseline screening focused on {', '.join(symptom_pool[:2])}. "
                f"Established therapeutic alliance, informed consent, and initial treatment goals under {modality}."
            )
        elif idx == total:
            target = "Progress Evaluation & Authorization Motivation"
            content = (
                f"Review of treatment milestones targeting {symptom_pool[0]}. "
                f"Evaluated adaptive coping mechanisms and consolidated progress. "
                f"Formulated motivation for ongoing sessions to prevent symptom relapse."
            )
        else:
            active_symptom = symptom_pool[(idx - 2) % len(symptom_pool)]
            target = f"Intervention: {active_symptom}"
            content = (
                f"Targeted clinical intervention addressing {active_symptom}. "
                f"Applied {modality} techniques; observed introspective engagement, "
                f"affective stabilization, and progress toward therapeutic objectives."
            )

        sessions.append({
            "num": idx,
            "date": dt_str,
            "symptom_target": target,
            "content": content
        })

    return sessions


def synthesize_recommendation(discipline: str, modality: str, symptoms: List[str], tariff_code: str) -> str:
    """
    Produces standard medical scheme motivation phrasing tailored to discipline.
    """
    primary_syms = ", ".join(symptoms[:2]) if symptoms else "presenting indicators"
    return (
        f"The client has demonstrated clinical responsiveness to {modality} interventions targeting {primary_syms}. "
        f"In accordance with clinical best practice guidelines, continuation of structured therapeutic support under "
        f"tariff {tariff_code} is respectfully motivated to consolidate psychological equilibrium and ensure long-term stability."
    )