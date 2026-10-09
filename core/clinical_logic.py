"""
core/clinical_logic.py
Unified Clinical Registry, Scope Logic & Narrative Synthesizer
Covering HPCSA & SACSSP statutory frameworks, grief/bereavement clusters,
therapy adherence, ongoing clinical barriers, and session-by-session generation.
"""
import datetime


SCOPE_GUIDELINES = {
    "Registered Counsellor (HPCSA)": {
        "council": "HPCSA",
        "reg_prefix": "PRC",
        "bhf_prefix": "081",
        "scope_note": "Primary mental health screening, basic supportive counselling, psycho-education, grief, and functional containment under HPCSA regulations.",
        "allowed_tariffs": {
            "81301": "Initial Assessment / Intake Consultation (51-60 min)",
            "81305": "Individual Supportive / Psycho-educational Session (51-60 min)",
            "81307": "Couples / Family Supportive Consultation (51-60 min)",
            "81315": "Multi-disciplinary Case Liaison"
        },
        "modalities": [
            "Cognitive Behavioural Framework",
            "Solution-Focused Brief Therapy (SFBT)",
            "Person-Centred Supportive Counselling",
            "Grief Psycho-education & Resilience Building"
        ],
        "disallowed_terms": ["formal psychiatric formulation", "neuropsychological evaluation", "personality disorder diagnosis", "intensive psychodynamic reconstruction"]
    },
    "Social Worker (SACSSP)": {
        "council": "SACSSP",
        "reg_prefix": "10-",
        "bhf_prefix": "089",
        "scope_note": "Biopsychosocial assessment, systemic family dynamics, crisis trauma debriefing, bereavement support, and social casework under SACSSP.",
        "allowed_tariffs": {
            "89001": "Initial Biopsychosocial Assessment (51-60 min)",
            "89005": "Individual Social Work Counselling & Support (51-60 min)",
            "89007": "Conjoint / Family Systemic Intervention",
            "89015": "Collateral / School / EAP / Multi-agency Liaison"
        },
        "modalities": [
            "Biopsychosocial-Spiritual Model",
            "Systemic Family Therapy",
            "Trauma-Informed Crisis Intervention",
            "Narrative Therapy & Meaning Reconstruction",
            "Strength-Based Empowerment"
        ],
        "disallowed_terms": ["psychometric assessment", "formal iq evaluation", "neurodevelopmental diagnosis"]
    },
    "Educational Psychologist (HPCSA)": {
        "council": "HPCSA",
        "reg_prefix": "PS",
        "bhf_prefix": "086",
        "scope_note": "Psycho-educational assessment, academic barriers, ADHD, developmental milestones, child/adolescent bereavement, and family guidance.",
        "allowed_tariffs": {
            "86301": "Initial Psycho-educational Diagnostic Intake (51-60 min)",
            "86305": "Individual Psychotherapy / Cognitive Intervention (51-60 min)",
            "86307": "Parent Guidance / Family Consultation (51-60 min)",
            "86310": "Formal Psychometric Assessment (per hour)",
            "86315": "Multi-disciplinary School / Collateral Liaison"
        },
        "modalities": [
            "Cognitive-Behavioural Therapy (CBT)",
            "Acceptance & Commitment Therapy (ACT)",
            "Play-Based Therapeutic Intervention",
            "Executive Function Coaching",
            "Parent-Guidance & Academic Support Framework"
        ],
        "disallowed_terms": ["adult forensic criminal capacity", "geriatric neuropsychological rehabilitation"]
    },
    "Counselling Psychologist (HPCSA)": {
        "council": "HPCSA",
        "reg_prefix": "PS",
        "bhf_prefix": "086",
        "scope_note": "Psychological adjustment, relational and systemic therapy, existential/life transitions, complicated bereavement, and mild-to-moderate psychopathology.",
        "allowed_tariffs": {
            "86301": "Initial Clinical Diagnostic Consultation (51-60 min)",
            "86305": "Individual Psychotherapy / Counselling Session (51-60 min)",
            "86307": "Couples / Marital / Family Psychotherapy (51-60 min)",
            "86315": "Collateral / Multi-disciplinary Case Consultation"
        },
        "modalities": [
            "Integrative Psychotherapy",
            "Cognitive-Behavioural Therapy (CBT)",
            "Emotion-Focused Therapy (EFT)",
            "Existential-Humanistic Psychotherapy",
            "Meaning Reconstruction & Dual-Process Grief Model"
        ],
        "disallowed_terms": ["forensic criminal competency", "inpatient neuropsychiatric rehabilitation"]
    },
    "Clinical Psychologist (HPCSA)": {
        "council": "HPCSA",
        "reg_prefix": "PS",
        "bhf_prefix": "086",
        "scope_note": "Comprehensive clinical psychodiagnosis, evidence-based psychotherapy for severe psychopathology, Prolonged Grief Disorder, and personality assessment.",
        "allowed_tariffs": {
            "86301": "Initial Comprehensive Clinical Diagnostic Evaluation",
            "86305": "Individual Evidence-Based Psychotherapy (51-60 min)",
            "86307": "Family / Systems Psychotherapy Consultation (51-60 min)",
            "86310": "Formal Neuropsychological / Personality Assessment (per hour)",
            "86315": "Multi-disciplinary Psychiatric Case Liaison"
        },
        "modalities": [
            "Dialectical Behavior Therapy (DBT)",
            "Cognitive Behavioural Therapy (CBT / Trauma-Focused)",
            "Complicated Grief Therapy (CGT)",
            "Psychodynamic Psychotherapy",
            "Schema Therapy"
        ],
        "disallowed_terms": []
    }
}


def get_scope_guidelines(designation: str) -> dict:
    if designation in SCOPE_GUIDELINES:
        return SCOPE_GUIDELINES[designation]
    for key, val in SCOPE_GUIDELINES.items():
        if key.lower().split()[0] in designation.lower():
            return val
    return SCOPE_GUIDELINES["Registered Counsellor (HPCSA)"]


def validate_scope(discipline_name: str, text: str) -> list:
    config = get_scope_guidelines(discipline_name)
    disallowed = config.get("disallowed_terms", [])
    text_lower = text.lower()
    return [term.lower() for term in disallowed if term.lower() in text_lower]


def synthesize_clinical_narrative(designation: str, icd10: str, modality: str, symptoms: list, session_count: int, dates: list) -> dict:
    """
    Dynamically generates profession-specific clinical narrative, adherence report,
    ongoing barriers, and progressive session-by-session notes tailored for medical scheme reviews.
    """
    sym_str = ", ".join(symptoms[:3]) if symptoms else "situational adjustment difficulties"
    is_grief = "grief" in icd10.lower() or "bereavement" in icd10.lower() or any("grief" in s.lower() or "yearning" in s.lower() for s in symptoms)

    # 1. Trajectory / Rationale
    if "Registered Counsellor" in designation:
        if is_grief:
            trajectory = (
                f"Client presented for supportive counselling following bereavement-related distress ({sym_str}). "
                f"Interventions utilized {modality} to normalize the grief trajectory, facilitate emotional processing, "
                f"and restore everyday functional containment. Observable progress is noted in the client's capacity to engage in routine tasks."
            )
        else:
            trajectory = (
                f"Client engaged in primary supportive counselling for {icd10}, presenting with {sym_str}. "
                f"Utilizing {modality}, sessions prioritized psycho-education, coping skill acquisition, and solution-focused behavioral strategies. "
                f"Client demonstrates stabilized baseline containment and improved problem-solving capacity."
            )
        adherence = "High attendance compliance. Punctual for scheduled appointments and demonstrates receptive engagement during supportive reviews."
        barriers = "Acute situational stressors within personal/work environment; occasional lapses into emotional overwhelm during high-demand periods."

    elif "Social Worker" in designation:
        if is_grief:
            trajectory = (
                f"Client presented with significant biopsychosocial disruption secondary to loss and bereavement ({sym_str}). "
                f"Interventions applied {modality} to address relational impact, mobilize systemic/family support, and support adaptive meaning-making. "
                f"Environmental coping and familial role stabilization have shown measurable improvement."
            )
        else:
            trajectory = (
                f"Client evaluated from a biopsychosocial perspective presenting with {sym_str} related to {icd10}. "
                f"Applied {modality} targeting systemic functioning, environmental coping barriers, and social support integration. "
                f"Observable progress noted in social re-engagement and management of interpersonal stressors."
            )
        adherence = "Consistent session attendance. Active participation in systemic discussions and openness to exploring psychosocial support structures."
        barriers = "Systemic family communication hurdles, environmental stressors, and limited external community/economic support networks."

    elif "Educational Psychologist" in designation:
        if is_grief:
            trajectory = (
                f"Client presented with developmental and psycho-educational distress secondary to significant loss ({sym_str}). "
                f"Interventions utilized {modality} to support emotional expression, reduce cognitive intrusion during learning tasks, and coordinate with caregivers. "
                f"Academic attentional focus and emotional equilibrium in structured environments show positive progress."
            )
        else:
            trajectory = (
                f"Client presented with cognitive-affective and academic functioning barriers related to {icd10} ({sym_str}). "
                f"Interventions integrated {modality} alongside executive coping frameworks and parent/academic consultation. "
                f"Demonstrating improved task initiation, test-taking composure, and self-regulatory skills."
            )
        adherence = "Dependable attendance supported by caregivers. Responsive engagement with therapeutic activities and reflective tasks."
        barriers = "Academic timeline pressures, fluctuating executive stamina, and somatic stress reactions in high-evaluative settings."

    elif "Counselling Psychologist" in designation:
        if is_grief:
            trajectory = (
                f"Client engaged in psychological counselling for complicated bereavement responses ({sym_str}). "
                f"Interventions framed through {modality} and the Dual-Process Model of bereavement to work through emotional avoidance, process ambivalent feelings, and re-engage in life aspirations. "
                f"Client demonstrates deepening reflective capacity and decreased debilitating preoccupation with loss."
            )
        else:
            trajectory = (
                f"Client presented for psychotherapy addressing {icd10} characterized by {sym_str}. "
                f"Utilizing {modality}, clinical focus centered on cognitive-affective restructuring, interpersonal patterns, and adaptive identity integration. "
                f"Treatment has yielded improved self-efficacy, reduced affective intensity, and consolidated coping mechanisms."
            )
        adherence = "Consistent and reflective attendance. Demonstrates high therapeutic alliance and completes between-session cognitive exercises."
        barriers = "Entrenched introspective rumination, residual anxiety regarding major life transitions, and interpersonal boundary challenges."

    else:  # Clinical Psychologist
        if is_grief:
            trajectory = (
                f"Client presents with clinically significant psychopathology meeting criteria for Prolonged Grief Disorder / severe adjustment reactions ({sym_str}). "
                f"Evidence-based intervention via {modality} addressed intense separation distress, trauma-related avoidance of loss reminders, and depressive cognition. "
                f"Symptom intensity metrics indicate emergent stabilization with meaningful reduction in existential despair and cognitive fixation."
            )
        else:
            trajectory = (
                f"Comprehensive clinical psychological evaluation for {icd10} presenting with marked symptom burden ({sym_str}). "
                f"Evidence-based psychotherapeutic treatment utilizing {modality} targeted cognitive schemas, affective dysregulation, and neurobehavioral reactivation. "
                f"Clinical monitoring shows progressive de-escalation of acute symptom clusters and consolidation of emotional stabilization protocols."
            )
        adherence = "Full compliance with clinical treatment protocols. Active engagement in specialized therapeutic tasks and symptom-monitoring tracking."
        barriers = "Persistent core depressive schemas, autonomic reactivity under acute stressors, and risk of relapse upon confronting unresolved traumatic triggers."

    # 2. Dynamic Session Breakdown
    sessions = []
    for i in range(1, session_count + 1):
        s_date = dates[i - 1].strftime("%Y-%m-%d") if i - 1 < len(dates) else "2026-01-01"
        if i == 1:
            target = "Clinical Intake & Assessment" if "Psychologist" in designation else "Intake & Baseline Screening"
            content = f"Comprehensive intake evaluation targeting {sym_str}. Assessed risk, established safety baseline, and structured the {modality} framework."
        elif i == session_count:
            target = "Progress Evaluation & Authorisation Motivation"
            content = f"Evaluation of progress across target symptoms ({symptoms[0] if symptoms else 'baseline presentation'}). Consolidated therapeutic gains and formulated motivation for continued care."
        else:
            idx = (i - 2) % len(symptoms) if symptoms else 0
            cur_sym = symptoms[idx] if symptoms else "coping mechanisms"
            target = f"Intervention: {cur_sym}"
            content = f"Applied {modality} strategies targeting {cur_sym}. Client engaged constructively; observed development of adaptive cognitive/emotional coping strategies."

        sessions.append({
            "num": i,
            "date": s_date,
            "symptom_target": target,
            "content": content
        })

    return {
        "trajectory": trajectory,
        "adherence": adherence,
        "barriers": barriers,
        "sessions": sessions
    }

def calculate_session_dates(start_date: datetime.date, count: int) -> list:
    """
    Calculates consecutive weekly weekday dates starting from start_date.
    Ensures sessions do not land on weekends.
    """
    dates = []
    curr = start_date
    while len(dates) < count:
        if curr.weekday() < 5:  # Monday to Friday
            dates.append(curr)
        curr += datetime.timedelta(days=7)
    return dates