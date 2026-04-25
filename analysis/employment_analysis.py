"""
TALASH M2 - Employment Profile Analysis

Evaluates professional profile, employment continuity,
career progression, and skill relevance.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Seniority classification keywords ──────────────────────────────────────
SENIORITY_PATTERNS = {
    "leadership": [
        r"\b(director|vp|vice president|ceo|cto|cfo|coo|head|dean|provost|"
        r"president|principal|chief)\b"
    ],
    "senior": [
        r"\b(senior|sr\.?|lead|manager|supervisor|coordinator|"
        r"associate professor|professor)\b"
    ],
    "mid": [
        r"\b(engineer|developer|analyst|consultant|specialist|lecturer|"
        r"assistant professor|officer|executive)\b"
    ],
    "junior": [
        r"\b(junior|jr\.?|intern|trainee|assistant|fellow|"
        r"teaching assistant|research assistant|ta|ra)\b"
    ],
}


# ── 2.1  extract_professional_experience ────────────────────────────────────
def extract_professional_experience(
    experience_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Extract and standardize professional experience records from CSV data.

    Input : experience DataFrame filtered for one candidate
    Output: list of dicts with standardized fields
    """
    if experience_df.empty:
        return []

    records: List[Dict[str, Any]] = []
    for _, row in experience_df.iterrows():
        start_year = _safe_int(row.get("start_year"))
        end_year = _safe_int(row.get("end_year"))

        # Determine employment type from title
        title = str(row.get("post_job_title", "")).lower()
        emp_type = _infer_employment_type(title)

        # Calculate duration
        duration_years: Optional[float] = None
        if start_year and end_year:
            duration_years = end_year - start_year
        elif start_year:
            duration_years = None  # ongoing

        records.append({
            "post_job_title": row.get("post_job_title"),
            "organization": row.get("organization"),
            "location": row.get("location"),
            "duration": row.get("duration"),
            "start_year": start_year,
            "end_year": end_year,
            "duration_years": duration_years,
            "employment_type": emp_type,
            "seniority_level": _classify_seniority(
                str(row.get("post_job_title", ""))
            ),
        })

    # Sort chronologically
    records.sort(key=lambda r: r.get("start_year") or 9999)
    return records


# ── 2.2  analyze_timeline_consistency ───────────────────────────────────────
def analyze_timeline_consistency(
    experience_records: List[Dict[str, Any]],
    education_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Detect overlaps and gaps in employment/education timeline.

    Returns: TimelineAnalysis with overlaps, gaps, consistency score, anomalies.
    """
    overlaps: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    anomalies: List[str] = []

    if not experience_records:
        return {
            "overlaps": [],
            "gaps": [],
            "timeline_consistency_score": 100.0,
            "anomaly_count": 0,
            "anomalies": [],
        }

    # Detect job-to-job overlaps
    dated_records = [
        r for r in experience_records
        if r.get("start_year") is not None
    ]

    for i in range(len(dated_records)):
        for j in range(i + 1, len(dated_records)):
            ri, rj = dated_records[i], dated_records[j]
            si, ei = ri["start_year"], ri.get("end_year") or 2026
            sj, ej = rj["start_year"], rj.get("end_year") or 2026

            if si < ej and sj < ei:  # overlap exists
                severity = "acceptable"
                ti = ri.get("employment_type", "full_time")
                tj = rj.get("employment_type", "full_time")
                if ti == "full_time" and tj == "full_time":
                    severity = "suspicious"
                    anomalies.append(
                        f"Two full-time roles overlap: "
                        f"'{ri['post_job_title']}' and '{rj['post_job_title']}'"
                    )
                overlaps.append({
                    "role_a": ri["post_job_title"],
                    "role_b": rj["post_job_title"],
                    "overlap_years": f"{max(si, sj)}-{min(ei, ej)}",
                    "severity": severity,
                })

    # Detect employment gaps
    sorted_records = sorted(dated_records, key=lambda r: r["start_year"])
    for i in range(len(sorted_records) - 1):
        end_current = sorted_records[i].get("end_year")
        start_next = sorted_records[i + 1].get("start_year")

        if end_current and start_next:
            gap_months = (start_next - end_current) * 12
            if gap_months > 3:  # flag gaps > 3 months
                gaps.append({
                    "after_role": sorted_records[i].get("post_job_title"),
                    "before_role": sorted_records[i + 1].get("post_job_title"),
                    "gap_start_year": end_current,
                    "gap_end_year": start_next,
                    "duration_months": gap_months,
                })

    # Education-employment overlap detection
    if education_records:
        for edu in education_records:
            edu_start = edu.get("admission_year") or edu.get("passing_year")
            edu_end = edu.get("completion_year") or edu.get("passing_year")
            if not edu_start or not edu_end:
                continue
            for exp in dated_records:
                es = exp["start_year"]
                ee = exp.get("end_year") or 2026
                if es < edu_end and edu_start < ee:
                    et = exp.get("employment_type", "full_time")
                    if et == "full_time":
                        anomalies.append(
                            f"Full-time employment '{exp['post_job_title']}' "
                            f"overlaps with education "
                            f"'{edu.get('degree_title_raw', 'N/A')}'"
                        )

    # Calculate consistency score
    penalty = len(anomalies) * 15 + len(gaps) * 5
    consistency_score = max(0.0, 100.0 - penalty)

    return {
        "overlaps": overlaps,
        "gaps": gaps,
        "timeline_consistency_score": round(consistency_score, 1),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


# ── 2.3  assess_career_progression ──────────────────────────────────────────
def assess_career_progression(
    experience_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate junior→senior career trajectory.

    Returns: progression pattern, consistency score, growth rate.
    """
    if not experience_records:
        return {
            "progression_consistency": 0.0,
            "career_growth_rate": "minimal",
            "seniority_trajectory": "stable",
            "experience_relevance_to_latest_role": 0.0,
            "role_classifications": [],
        }

    sorted_records = sorted(
        experience_records,
        key=lambda r: r.get("start_year") or 9999,
    )

    # Classify each role
    seniority_order = {"junior": 1, "mid": 2, "senior": 3, "leadership": 4}
    classifications = []
    for rec in sorted_records:
        level = rec.get("seniority_level", "mid")
        classifications.append({
            "title": rec["post_job_title"],
            "seniority": level,
            "order": seniority_order.get(level, 2),
            "year": rec.get("start_year"),
        })

    # Determine trajectory
    orders = [c["order"] for c in classifications]
    trajectory = _determine_trajectory(orders)

    # Consistency score
    if len(orders) >= 2:
        advances = sum(
            1 for i in range(1, len(orders)) if orders[i] >= orders[i - 1]
        )
        consistency = round((advances / (len(orders) - 1)) * 100, 1)
    else:
        consistency = 100.0

    # Growth rate
    if len(orders) >= 2:
        net_change = orders[-1] - orders[0]
        if net_change >= 2:
            growth = "strong"
        elif net_change >= 1:
            growth = "moderate"
        else:
            growth = "minimal"
    else:
        growth = "minimal"

    # Relevance - simple heuristic based on how many roles share domain
    orgs = [
        str(r.get("organization", "")).lower()
        for r in sorted_records if r.get("organization")
    ]
    unique_orgs = set(orgs)
    relevance = round(
        min(100.0, (1 / max(len(unique_orgs), 1)) * 100 + 20), 1
    )

    return {
        "progression_consistency": consistency,
        "career_growth_rate": growth,
        "seniority_trajectory": trajectory,
        "experience_relevance_to_latest_role": relevance,
        "role_classifications": classifications,
    }


# ── 2.4  justify_employment_gaps ────────────────────────────────────────────
def justify_employment_gaps(
    gaps: List[Dict[str, Any]],
    education_records: Optional[List[Dict[str, Any]]] = None,
    experience_records: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    For each gap > 3 months, check if justified by education,
    freelancing, research, etc.
    """
    justified_gaps: List[Dict[str, Any]] = []

    for gap in gaps:
        g_start = gap.get("gap_start_year")
        g_end = gap.get("gap_end_year")
        duration = gap.get("duration_months", 0)

        justification_type = "unexplained"
        justification_detail = "No justification found in CV data."
        impact_level = "none"

        # Check education overlap
        if education_records and g_start and g_end:
            for edu in education_records:
                edu_start = edu.get("admission_year")
                edu_end = edu.get("completion_year") or edu.get("passing_year")
                if edu_start and edu_end:
                    if edu_start <= g_end and edu_end >= g_start:
                        justification_type = "education"
                        justification_detail = (
                            f"Pursuing {edu.get('degree_title_raw', 'degree')} "
                            f"at {edu.get('institution_name', 'N/A')}"
                        )
                        break

        # Determine impact
        if justification_type == "unexplained":
            if duration > 24:
                impact_level = "significant"
            elif duration > 12:
                impact_level = "moderate"
            elif duration > 6:
                impact_level = "minor"
            else:
                impact_level = "none"
        else:
            impact_level = "none"

        justified_gaps.append({
            "gap_period": f"{g_start}-{g_end}",
            "duration_months": duration,
            "justification_type": justification_type,
            "justification_detail": justification_detail,
            "impact_level": impact_level,
        })

    return justified_gaps


# ── 2.5  generate_employment_assessment ─────────────────────────────────────
def generate_employment_assessment(
    experience_df: pd.DataFrame,
    education_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Synthesize overall professional assessment for a candidate.

    Returns comprehensive dict with all employment metrics and narrative.
    """
    exp_records = extract_professional_experience(experience_df)
    edu_records = _edu_df_to_list(education_df) if education_df is not None else []

    if not exp_records:
        return _empty_employment_assessment()

    # Timeline analysis
    timeline = analyze_timeline_consistency(exp_records, edu_records)

    # Career progression
    progression = assess_career_progression(exp_records)

    # Gap justification
    justified = justify_employment_gaps(
        timeline["gaps"], edu_records, exp_records
    )

    # Total years of experience
    total_years = 0.0
    for r in exp_records:
        if r.get("duration_years") is not None and r["duration_years"] > 0:
            total_years += r["duration_years"]
        elif r.get("start_year"):
            # Ongoing role
            total_years += max(0, 2026 - r["start_year"])

    # Experience level classification
    exp_level = _classify_experience_level(total_years)

    # Employment continuity score
    unexplained_gaps = [
        g for g in justified if g["justification_type"] == "unexplained"
    ]
    continuity_penalty = sum(
        min(20, g["duration_months"] * 0.5) for g in unexplained_gaps
    )
    continuity_score = max(0.0, 100.0 - continuity_penalty)

    # Overall professional strength
    overall = round(
        timeline["timeline_consistency_score"] * 0.25
        + progression["progression_consistency"] * 0.25
        + continuity_score * 0.30
        + min(100, total_years * 5) * 0.20,  # capped at 100
        1,
    )

    # Narrative
    narrative = _build_employment_narrative(
        total_years, exp_level, progression["seniority_trajectory"],
        len(unexplained_gaps), exp_records,
    )

    return {
        "total_years_of_experience": round(total_years, 1),
        "experience_level": exp_level,
        "employment_continuity_score": round(continuity_score, 1),
        "career_progression_score": round(progression["progression_consistency"], 1),
        "timeline_consistency_score": timeline["timeline_consistency_score"],
        "overall_professional_strength": overall,
        "seniority_trajectory": progression["seniority_trajectory"],
        "career_growth_rate": progression["career_growth_rate"],
        "experience_records": exp_records,
        "timeline_overlaps": timeline["overlaps"],
        "timeline_gaps": timeline["gaps"],
        "timeline_anomalies": timeline["anomalies"],
        "justified_gaps": justified,
        "role_classifications": progression["role_classifications"],
        "narrative_summary": narrative,
    }


# ── Helper functions ────────────────────────────────────────────────────────

def _safe_int(val: Any) -> Optional[int]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _infer_employment_type(title: str) -> str:
    title_lower = title.lower()
    if re.search(r"\b(intern|internship)\b", title_lower):
        return "internship"
    if re.search(r"\b(part[- ]?time)\b", title_lower):
        return "part_time"
    if re.search(r"\b(contract|freelance|consulting)\b", title_lower):
        return "contract"
    if re.search(r"\b(research assistant|ra)\b", title_lower):
        return "research_assistant"
    if re.search(r"\b(teaching assistant|ta)\b", title_lower):
        return "teaching_assistant"
    return "full_time"


def _classify_seniority(title: str) -> str:
    text = title.lower()
    for level in ["leadership", "senior", "junior"]:
        for pattern in SENIORITY_PATTERNS[level]:
            if re.search(pattern, text):
                return level
    return "mid"


def _determine_trajectory(orders: List[int]) -> str:
    if len(orders) < 2:
        return "stable"
    ascending = all(orders[i] >= orders[i - 1] for i in range(1, len(orders)))
    descending = all(orders[i] <= orders[i - 1] for i in range(1, len(orders)))
    if ascending and orders[-1] > orders[0]:
        return "ascending"
    if descending and orders[-1] < orders[0]:
        return "declining"
    if all(o == orders[0] for o in orders):
        return "stable"
    return "variable"


def _classify_experience_level(years: float) -> str:
    if years >= 15:
        return "leadership"
    if years >= 10:
        return "senior"
    if years >= 5:
        return "mid_level"
    if years >= 2:
        return "junior"
    return "entry_level"


def _build_employment_narrative(
    years: float, level: str, trajectory: str,
    unexplained_count: int, records: List[Dict],
) -> str:
    parts = []
    parts.append(
        f"Candidate has {years:.1f} years of professional experience "
        f"at the {level.replace('_', ' ')} level."
    )
    if records:
        latest = records[-1]
        parts.append(
            f"Most recent role: {latest.get('post_job_title', 'N/A')} "
            f"at {latest.get('organization', 'N/A')}."
        )
    parts.append(f"Career trajectory is {trajectory}.")
    if unexplained_count > 0:
        parts.append(
            f"There {'is' if unexplained_count == 1 else 'are'} "
            f"{unexplained_count} unexplained gap(s) in employment history."
        )
    return " ".join(parts)


def _edu_df_to_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        records.append({
            "degree_level": row.get("degree_level"),
            "degree_title_raw": row.get("degree_title_raw"),
            "institution_name": row.get("institution_name"),
            "admission_year": _safe_int(row.get("admission_year")),
            "completion_year": _safe_int(row.get("completion_year")),
            "passing_year": _safe_int(row.get("passing_year")),
            "score_normalized_percentage": _safe_float(
                row.get("score_normalized_percentage")
            ),
        })
    return records


def _safe_float(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _empty_employment_assessment() -> Dict[str, Any]:
    return {
        "total_years_of_experience": 0.0,
        "experience_level": "entry_level",
        "employment_continuity_score": 0.0,
        "career_progression_score": 0.0,
        "timeline_consistency_score": 100.0,
        "overall_professional_strength": 0.0,
        "seniority_trajectory": "stable",
        "career_growth_rate": "minimal",
        "experience_records": [],
        "timeline_overlaps": [],
        "timeline_gaps": [],
        "timeline_anomalies": [],
        "justified_gaps": [],
        "role_classifications": [],
        "narrative_summary": "No professional experience records available.",
    }
