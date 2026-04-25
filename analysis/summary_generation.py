"""
TALASH M2 - Candidate Summary Generation

Generates concise, actionable candidate assessment summaries
with weighted overall scores and key strengths/concerns.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── 4.1  calculate_candidate_overall_score ──────────────────────────────────
def calculate_candidate_overall_score(
    educational_strength: float = 0.0,
    professional_strength: float = 0.0,
    completeness_score: float = 0.0,
    basic_skill_relevance: float = 50.0,
) -> Dict[str, Any]:
    """
    Calculate weighted overall candidate score.

    Weights:
      - Educational Strength:    30%
      - Professional Strength:   35%
      - Data Completeness:       15%
      - Basic Skill Relevance:   20% (basic M2 implementation, detailed in M3)

    Returns: {'overall_score': float, 'tier': str}
    """
    overall_score = round(
        educational_strength * 0.30
        + professional_strength * 0.35
        + completeness_score * 0.15
        + basic_skill_relevance * 0.20,
        1,
    )

    # Clamp to 0-100
    overall_score = max(0.0, min(100.0, overall_score))

    tier = _classify_tier(overall_score)

    return {
        "overall_score": overall_score,
        "tier": tier,
        "score_breakdown": {
            "educational_strength": round(educational_strength, 1),
            "educational_weight": 0.30,
            "educational_contribution": round(educational_strength * 0.30, 1),
            "professional_strength": round(professional_strength, 1),
            "professional_weight": 0.35,
            "professional_contribution": round(professional_strength * 0.35, 1),
            "completeness_score": round(completeness_score, 1),
            "completeness_weight": 0.15,
            "completeness_contribution": round(completeness_score * 0.15, 1),
            "skill_relevance": round(basic_skill_relevance, 1),
            "skill_weight": 0.20,
            "skill_contribution": round(basic_skill_relevance * 0.20, 1),
        },
    }


# ── 4.2  generate_strengths_and_concerns ────────────────────────────────────
def generate_strengths_and_concerns(
    educational_assessment: Dict[str, Any],
    employment_assessment: Dict[str, Any],
    missing_summary: Dict[str, Any],
) -> Dict[str, List[str]]:
    """
    Extract top 3 strengths and top 3 concerns from assessment data.

    Returns: {'strengths': List[str], 'concerns': List[str]}
    """
    strengths: List[str] = []
    concerns: List[str] = []

    # ── Evaluate educational strengths/concerns ──
    edu_strength = educational_assessment.get("overall_educational_strength", 0)
    perf_level = educational_assessment.get("academic_performance_level", "unknown")
    highest = educational_assessment.get("highest_qualification_level", "unknown")
    trend = educational_assessment.get("performance_trend", "variable")
    avg_score = educational_assessment.get("average_score")

    # Strengths
    if highest in ("phd", "postdoc", "doctorate"):
        strengths.append(f"Advanced degree holder ({highest.upper()})")
    elif highest in ("mphil", "pg", "masters"):
        strengths.append(f"Holds postgraduate qualification ({highest.upper()})")

    if avg_score and avg_score >= 75:
        strengths.append(
            f"Strong academic performance (average: {avg_score:.1f}%)"
        )

    if trend == "improving":
        strengths.append("Consistently improving academic performance")

    edu_consistency = educational_assessment.get("academic_consistency_score", 0)
    if edu_consistency >= 80:
        strengths.append("Coherent educational progression")

    # Concerns
    if perf_level in ("fair", "weak"):
        concerns.append(f"Below-average academic performance ({perf_level})")

    if trend == "declining":
        concerns.append("Declining academic performance trend")

    edu_gaps = educational_assessment.get("gaps", [])
    flagged_gaps = [g for g in edu_gaps if g.get("is_flagged")]
    if len(flagged_gaps) > 0:
        unjustified = [g for g in flagged_gaps if not g.get("justified_by_experience")]
        if unjustified:
            concerns.append(
                f"{len(unjustified)} unexplained educational gap(s)"
            )

    # ── Evaluate employment strengths/concerns ──
    total_years = employment_assessment.get("total_years_of_experience", 0)
    trajectory = employment_assessment.get("seniority_trajectory", "stable")
    growth = employment_assessment.get("career_growth_rate", "minimal")
    continuity = employment_assessment.get("employment_continuity_score", 0)

    if total_years >= 10:
        strengths.append(f"Extensive experience ({total_years:.0f}+ years)")
    elif total_years >= 5:
        strengths.append(f"Solid professional experience ({total_years:.0f} years)")

    if trajectory == "ascending":
        strengths.append("Clear career progression (ascending trajectory)")

    if continuity >= 85:
        strengths.append("Continuous employment with minimal gaps")

    if growth == "strong":
        strengths.append("Strong career growth rate")

    # Employment concerns
    emp_gaps = employment_assessment.get("justified_gaps", [])
    unexplained_emp = [
        g for g in emp_gaps if g.get("justification_type") == "unexplained"
    ]
    if unexplained_emp:
        concerns.append(
            f"{len(unexplained_emp)} unexplained employment gap(s)"
        )

    anomalies = employment_assessment.get("timeline_anomalies", [])
    if anomalies:
        concerns.append(
            f"Timeline inconsistencies detected ({len(anomalies)} anomaly/ies)"
        )

    if trajectory == "declining":
        concerns.append("Career trajectory shows decline in seniority")

    if total_years < 2:
        concerns.append("Limited professional experience")

    # ── Completeness concerns ──
    completeness = missing_summary.get("completeness_percentage", 100)
    critical_count = missing_summary.get("critical_count", 0)

    if critical_count > 0:
        concerns.append(
            f"{critical_count} critical field(s) missing from CV"
        )

    if completeness < 60:
        concerns.append(
            f"Low data completeness ({completeness:.0f}%)"
        )

    # Limit to top 3 each
    return {
        "strengths": strengths[:3] if strengths else ["No notable strengths identified"],
        "concerns": concerns[:3] if concerns else ["No significant concerns identified"],
    }


# ── 4.3  generate_candidate_summary ─────────────────────────────────────────
def generate_candidate_summary(
    personal_info: Dict[str, Any],
    educational_assessment: Dict[str, Any],
    employment_assessment: Dict[str, Any],
    missing_summary: Dict[str, Any],
    overall_score_data: Optional[Dict[str, Any]] = None,
    strengths_concerns: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive candidate summary report.

    Returns: CandidateSummary dict with all sections.
    """
    # Calculate overall score if not provided
    if overall_score_data is None:
        edu_strength = educational_assessment.get(
            "overall_educational_strength", 0
        )
        emp_strength = employment_assessment.get(
            "overall_professional_strength", 0
        )
        completeness = missing_summary.get("completeness_percentage", 0)

        overall_score_data = calculate_candidate_overall_score(
            educational_strength=edu_strength,
            professional_strength=emp_strength,
            completeness_score=completeness,
        )

    # Generate strengths/concerns if not provided
    if strengths_concerns is None:
        strengths_concerns = generate_strengths_and_concerns(
            educational_assessment, employment_assessment, missing_summary,
        )

    # Build executive summary
    name = personal_info.get("full_name", "Unknown Candidate")
    score = overall_score_data["overall_score"]
    tier = overall_score_data["tier"]

    highest_deg = educational_assessment.get(
        "highest_qualification_level", "N/A"
    )
    total_exp = employment_assessment.get("total_years_of_experience", 0)
    exp_level = employment_assessment.get("experience_level", "N/A")

    quick_profile = (
        f"{name} is a {exp_level.replace('_', ' ')} professional "
        f"with {total_exp:.0f} years of experience "
        f"and a {highest_deg.upper()} qualification. "
        f"Overall assessment: {tier.replace('_', ' ').title()} "
        f"({score}/100)."
    )

    # Build recommendation
    if score >= 85:
        recommendation = (
            "Strongly recommended for further consideration. "
            "Candidate shows excellent qualifications and professional record."
        )
    elif score >= 75:
        recommendation = (
            "Recommended for consideration. Candidate has a strong overall profile "
            "with minor areas for clarification."
        )
    elif score >= 65:
        recommendation = (
            "Conditionally recommended. Candidate meets basic requirements "
            "but some areas need further review or clarification."
        )
    elif score >= 50:
        recommendation = (
            "May be considered if candidate pool is limited. "
            "Several aspects of the profile require clarification."
        )
    else:
        recommendation = (
            "Not recommended at this time based on available information. "
            "Significant gaps in qualifications or data completeness."
        )

    return {
        "candidate_id": personal_info.get("candidate_id"),
        "candidate_name": name,
        "candidate_email": personal_info.get("email"),
        "post_applied_for": personal_info.get("post_applied_for"),
        "overall_score": score,
        "overall_tier": tier,
        "quick_profile": quick_profile,
        "score_breakdown": overall_score_data.get("score_breakdown", {}),
        "educational_profile": {
            "highest_qualification": highest_deg,
            "academic_performance": educational_assessment.get(
                "academic_performance_level"
            ),
            "average_score": educational_assessment.get("average_score"),
            "institution_quality": educational_assessment.get(
                "institution_quality_average"
            ),
            "education_continuity": educational_assessment.get(
                "educational_continuity_score"
            ),
            "educational_strength": educational_assessment.get(
                "overall_educational_strength"
            ),
        },
        "professional_profile": {
            "total_experience_years": total_exp,
            "experience_level": exp_level,
            "current_role": _get_latest_role(employment_assessment),
            "career_progression": employment_assessment.get(
                "seniority_trajectory"
            ),
            "employment_continuity": employment_assessment.get(
                "employment_continuity_score"
            ),
            "professional_strength": employment_assessment.get(
                "overall_professional_strength"
            ),
        },
        "strengths": strengths_concerns["strengths"],
        "concerns": strengths_concerns["concerns"],
        "completeness": {
            "percentage": missing_summary.get("completeness_percentage", 0),
            "critical_missing": missing_summary.get("critical_count", 0),
            "total_missing": missing_summary.get("total_missing_fields", 0),
        },
        "recommendation": recommendation,
        "educational_narrative": educational_assessment.get("narrative_summary"),
        "employment_narrative": employment_assessment.get("narrative_summary"),
    }


# ── Helper functions ────────────────────────────────────────────────────────

def _classify_tier(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 75:
        return "very_good"
    if score >= 65:
        return "good"
    if score >= 50:
        return "fair"
    return "below_average"


def _get_latest_role(employment_assessment: Dict[str, Any]) -> Optional[str]:
    records = employment_assessment.get("experience_records", [])
    if not records:
        return None
    latest = records[-1]
    title = latest.get("post_job_title", "N/A")
    org = latest.get("organization", "N/A")
    return f"{title} at {org}"
