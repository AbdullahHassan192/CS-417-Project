"""
TALASH M3 - Candidate Ranking Module

Composite ranking of all candidates based on weighted scores
from education, experience, research, and completeness.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ranking weight configuration
RANKING_WEIGHTS = {
    "education": 0.25,
    "experience": 0.30,
    "research": 0.25,
    "completeness": 0.10,
    "skill_alignment": 0.10,
}


def compute_candidate_ranking(
    assessments: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Compute global ranking of candidates.

    Input: List of full assessment dicts (one per candidate).
    Returns: Sorted list of ranking entries with composite scores.
    """
    w = weights or RANKING_WEIGHTS
    rankings = []

    for a in assessments:
        cid = a.get("candidate_id")
        name = a.get("personal_info", {}).get("full_name", "Unknown")

        edu_score = a.get("educational_assessment", {}).get("overall_educational_strength", 0)
        emp_score = a.get("employment_assessment", {}).get("overall_professional_strength", 0)
        res_score = a.get("research_assessment", {}).get("overall_research_strength", 0)
        completeness = a.get("missing_info", {}).get("completeness_percentage", 100)
        skill_score = 50.0  # Default if no job-specific alignment

        composite = (
            edu_score * w.get("education", 0.25)
            + emp_score * w.get("experience", 0.30)
            + res_score * w.get("research", 0.25)
            + completeness * w.get("completeness", 0.10)
            + skill_score * w.get("skill_alignment", 0.10)
        )

        rankings.append({
            "candidate_id": cid,
            "candidate_name": name,
            "composite_score": round(composite, 2),
            "education_score": round(edu_score, 1),
            "experience_score": round(emp_score, 1),
            "research_score": round(res_score, 1),
            "completeness": round(completeness, 1),
            "skill_alignment_score": round(skill_score, 1),
        })

    # Sort descending by composite score
    rankings.sort(key=lambda x: x["composite_score"], reverse=True)

    # Assign ranks
    for i, r in enumerate(rankings, 1):
        r["rank"] = i
        if r["composite_score"] >= 80:
            r["tier"] = "excellent"
        elif r["composite_score"] >= 65:
            r["tier"] = "very_good"
        elif r["composite_score"] >= 50:
            r["tier"] = "good"
        elif r["composite_score"] >= 35:
            r["tier"] = "fair"
        else:
            r["tier"] = "below_average"

    return rankings
