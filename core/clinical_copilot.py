"""
core/clinical_copilot.py
Offline Clinical Synthesis & Formulations Engine
Aligns clinical text with HPCSA / SACSSP scopes and medical aid audit expectations.
"""
from typing import List, Dict, Any

# Clinical modality frameworks mapping theoretical mechanisms, goals, and outcomes
MODALITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "CBT": {
        "framework": "Cognitive Behavioral Therapy (CBT)",
        "intake_goal": "Establish cognitive case formulation; identify automatic negative thoughts (NATs) and baseline avoidance behaviors.",
        "intake_outcome": "Baseline BDI/BAI psychometrics recorded; initial cognitive thought record introduced.",
        "session_goals": [
            "Identify and restructure cognitive distortions (catastrophizing, dichotomous thinking) maintaining {symptom}.",
            "Implement structured behavioral activation and activity scheduling to disrupt avoidance loops related to {symptom}.",
            "Conduct behavioral experiments and core belief challenging to evaluate maladaptive schemas.",
            "Consolidate cognitive restructuring strategies and build systematic distress tolerance protocols."
        ],
        "session_outcomes": [
            "Demonstrated reduction in cognitive fusion with automatic thoughts; completed thought records with moderate fidelity.",
            "Increased engagement in targeted mastery/pleasure activities; measurable drop in subjective units of distress (SUDs).",
            "Modification of rigid intermediate beliefs; client articulated alternative adaptive interpretations.",
            "Independent execution of cognitive self-disputation during acute symptom elevation."
        ],
        "termination_goal": "Develop relapse prevention blueprint and establish maintenance cognitive self-monitoring schedule.",
        "termination_outcome": "Consolidated treatment gains, documented objective symptom reduction, and agreed on maintenance review intervals."
    },
    "ACT": {
        "framework": "Acceptance and Commitment Therapy (ACT)",
        "intake_goal": "Assess psychological flexibility, experiential avoidance, and clarify core personal values across life domains.",
        "intake_outcome": "Baseline AAQ-2 established; willingness contract and hexaflex baseline mapped.",
        "session_goals": [
            "Cultivate cognitive defusion techniques to alter relationship with distressing cognitions concerning {symptom}.",
            "Promote mindful acceptance of unwanted internal experiences and bodily sensations without experiential avoidance.",
            "Clarify core values and establish structured, values-aligned behavioral goals despite presence of {symptom}.",
            "Strengthen the 'Self-as-Context' perspective to observe psychological distress from an expanded vantage point."
        ],
        "session_outcomes": [
            "Client successfully untangled from unhelpful thought patterns using verbal and visual defusion exercises.",
            "Demonstrated increased willingness to endure distress without defaulting to chronic avoidance behaviors.",
            "Executed concrete, committed actions aligned with identified personal values between sessions.",
            "Enhanced psychological flexibility and reduced struggle with private emotional experiences."
        ],
        "termination_goal": "Integrate ongoing committed action habits and values-led decision framework into long-term routine.",
        "termination_outcome": "Sustained increase in psychological flexibility metrics; robust adherence to values-directed living."
    },
    "PSYCHODYNAMIC": {
        "framework": "Psychodynamic Psychotherapy",
        "intake_goal": "Explore developmental trajectory, primary attachment patterns, and active psychological defense mechanisms.",
        "intake_outcome": "Initial psychodynamic formulation completed; therapeutic contract and safe container established.",
        "session_goals": [
            "Facilitate affective insight into unconscious conflicts and repetitive relational schemas linked to {symptom}.",
            "Examine intrapsychic defense mechanisms (e.g., intellectualization, projection) triggered by emotional stressors.",
            "Process transference/countertransference dynamics within the therapeutic alliance to illuminate interpersonal patterns.",
            "Work through historical attachment injuries and facilitate affective integration of disowned emotional states."
        ],
        "session_outcomes": [
            "Client expressed and tolerated difficult affect previously suppressed or converted into physical/psychological tension.",
            "Heightened reflective functioning and conscious awareness of automated defensive reactions.",
            "Recognition of how historical relational dynamics are reenacted in current personal and occupational relationships.",
            "Consolidated emotional autonomy, increased capacity for self-compassion, and adaptive interpersonal boundary setting."
        ],
        "termination_goal": "Process termination-related affect, consolidate ego strength, and review internal relational representations.",
        "termination_outcome": "Increased structural ego resilience, enhanced affect tolerance, and resolved focal intrapsychic conflict."
    },
    "SOLUTION-FOCUSED": {
        "framework": "Solution-Focused Brief Therapy (SFBT)",
        "intake_goal": "Elicit preferred future via the miracle question, establish concrete baseline scaling, and map pre-session change.",
        "intake_outcome": "Measurable baseline scaling score (1-10) established; explicit, positive outcome goals co-constructed.",
        "session_goals": [
            "Identify exceptions when {symptom} was absent or less intense, amplifying client-generated coping resources.",
            "Formulate behavioral micro-steps to facilitate movement along the scaling continuum.",
            "Reinforce successful coping mechanisms and explore factors sustaining positive exceptions.",
            "Consolidate functional solutions and scale up behaviors that produce adaptive outcomes."
        ],
        "session_outcomes": [
            "Client identified 2 distinct exceptions where distress was managed effectively using dormant internal assets.",
            "Self-rated scaling improved by 1 to 2 points; executed designated behavioral exceptions.",
            "Validation of client resilience; observable shift in narrative from problem-saturated to competence-focused.",
            "Consistent application of self-directed micro-solutions across daily occupational and interpersonal routines."
        ],
        "termination_goal": "Consolidate self-maintenance strategy, establish maintenance scaling benchmarks, and prepare for formal discharge.",
        "termination_outcome": "Goal attainment achieved on primary scaling target; client equipped with self-directed maintenance protocol."
    },
    "DBT": {
        "framework": "Dialectical Behavior Therapy (DBT)",
        "intake_goal": "Establish biosocial model framing, prioritize target hierarchy (safety/therapy-interfering behaviors), and introduce diary cards.",
        "intake_outcome": "Commitment to DBT skills training established; baseline emotional dysregulation metrics mapped.",
        "session_goals": [
            "Train core mindfulness skills (Wise Mind, Observe/Describe) to counteract acute dysregulation stemming from {symptom}.",
            "Introduce distress tolerance crisis survival strategies (TIPP, STOP skill) to prevent behavioral escalation.",
            "Develop emotion regulation competencies (opposite action, ABC PLEASE) targeting {symptom}.",
            "Train interpersonal effectiveness skills (DEAR MAN, FAST) to negotiate boundaries and reduce relational chaos."
        ],
        "session_outcomes": [
            "Client utilized STOP/TIPP protocols during acute arousal rather than engaging in maladaptive coping.",
            "Accurate completion of weekly diary card demonstrating decreased frequency of target problem behaviors.",
            "Demonstrated capacity to identify vulnerability factors and apply opposite action to secondary emotional reactions.",
            "Successfully asserted boundaries in interpersonal context without escalating relational distress or compromising self-respect."
        ],
        "termination_goal": "Review skill generalization across all environments and synthesize ongoing secondary target plans.",
        "termination_outcome": "Significant stabilization of emotional reactivity; consistent independent utilization of Wise Mind skills."
    }
}

# UI input normalizer mapping various frontend dropdown strings to canonical keys
MODALITY_ALIASES: Dict[str, str] = {
    "CBT": "CBT",
    "COGNITIVE BEHAVIORAL THERAPY": "CBT",
    "ACT": "ACT",
    "ACCEPTANCE AND COMMITMENT THERAPY": "ACT",
    "PSYCHODYNAMIC": "PSYCHODYNAMIC",
    "PSYCHODYNAMIC PSYCHOTHERAPY": "PSYCHODYNAMIC",
    "SFBT": "SOLUTION-FOCUSED",
    "SOLUTION-FOCUSED": "SOLUTION-FOCUSED",
    "SOLUTION-FOCUSED BRIEF THERAPY": "SOLUTION-FOCUSED",
    "DBT": "DBT",
    "DIALECTICAL BEHAVIOR THERAPY": "DBT",
}


def _resolve_modality_profile(modality: str) -> Dict[str, Any]:
    """
    Safely maps UI modality strings to MODALITY_PROFILES with a robust fallback.
    """
    clean_key = MODALITY_ALIASES.get(modality.strip().upper(), "CBT")
    return MODALITY_PROFILES[clean_key]


def synthesize_treatment_plan(
    modality: str,
    symptoms: List[str],
    total_sessions: int = 6
) -> List[Dict[str, Any]]:
    """
    Generates a structured treatment plan where session goals, multi-symptom targets,
    and expected clinical outcomes dynamically adapt to the theoretical mechanism of the intervention.
    """
    if total_sessions <= 0:
        return []

    profile = _resolve_modality_profile(modality)
    symptom_pool = [s.strip() for s in symptoms if s.strip()] or ["presenting psychological distress"]
    
    plan = []
    goal_pool = profile["session_goals"]
    outcome_pool = profile["session_outcomes"]
    num_mid_goals = len(goal_pool)

    for idx in range(1, total_sessions + 1):
        # Rotate through all selected symptoms across intermediate sessions
        active_symptom = symptom_pool[(idx - 2) % len(symptom_pool)]

        if idx == 1:
            primary_focus = ", ".join(symptom_pool[:2])
            goal = f"{profile['intake_goal']} (Primary assessment targets: {primary_focus})."
            outcome = profile["intake_outcome"]
            milestone = "Intake, Formulation & Baseline Metrics"
        elif idx == total_sessions and total_sessions > 1:
            goal = profile["termination_goal"]
            outcome = profile["termination_outcome"]
            milestone = "Consolidation, Relapse Prevention & Discharge Planning"
        else:
            pool_index = (idx - 2) % num_mid_goals
            raw_goal = goal_pool[pool_index]
            
            # Format with symptom if token exists; append context cleanly if not
            if "{symptom}" in raw_goal:
                goal = raw_goal.format(symptom=active_symptom)
            else:
                goal = f"{raw_goal.rstrip('.')} in relation to {active_symptom}."
                
            outcome = outcome_pool[pool_index]
            milestone = f"Targeted Clinical Intervention: {active_symptom}"

        plan.append({
            "session_num": idx,
            "phase": milestone,
            "modality": profile["framework"],
            "session_goal": goal,
            "expected_outcome": outcome
        })

    return plan


def synthesize_session_notes(
    discipline: str,
    modality: str,
    selected_symptoms: List[str],
    service_dates: List[str]
) -> List[Dict[str, Any]]:
    """
    Generates structured, symptom-linked progression notes synchronized with the treatment plan.
    Incorporates discipline scope and multi-bullet depth.
    """
    total = len(service_dates)
    if total == 0:
        return []

    plan = synthesize_treatment_plan(modality, selected_symptoms, total_sessions=total)
    scope_label = discipline.strip() if discipline else "Clinical Practice"
    sessions = []

    for idx, dt_str in enumerate(service_dates):
        plan_step = plan[idx]
        content = (
            f"Phase Target: {plan_step['phase']} ({scope_label} Scope)\n"
            f"• Framework Applied: {plan_step['modality']}\n"
            f"• Objective Session Goal: {plan_step['session_goal']}\n"
            f"• Clinical Progress & Expected Outcome: {plan_step['expected_outcome']}"
        )

        sessions.append({
            "num": plan_step["session_num"],
            "date": dt_str,
            "symptom_target": plan_step["phase"],
            "content": content
        })

    return sessions


def synthesize_recommendation(discipline: str, modality: str, symptoms: List[str], tariff_code: str) -> str:
    """
    Produces standard medical scheme motivation phrasing tailored to discipline and modality framework.
    """
    profile = _resolve_modality_profile(modality)
    primary_syms = ", ".join(symptoms[:3]) if symptoms else "presenting clinical indicators"
    scope_label = discipline.strip() if discipline else "psychological"
    
    return (
        f"Within the {scope_label} scope of practice, the client has demonstrated measurable clinical responsiveness "
        f"to structured interventions under {profile['framework']} targeting {primary_syms}. "
        f"In accordance with statutory Council for Medical Schemes (CMS) billing guidelines and HPCSA best practice, "
        f"continuation of therapeutic support under tariff {tariff_code} is respectfully motivated to achieve "
        f"planned clinical milestones, consolidate functional coping strategies, and mitigate relapse risk."
    )
