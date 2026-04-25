"""
TALASH M2 - Educational Profile Analysis

Evaluates candidate's academic background in a structured, quantifiable manner.
Reuses M1 normalization functions — does NOT duplicate them.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Degree-level ordering for progression analysis ──────────────────────────
DEGREE_ORDER = {
    "ssc": 1, "hssc": 2, "diploma": 3,
    "ug": 4, "bachelors": 4, "pg": 5, "masters": 5,
    "mphil": 6, "phd": 7, "doctorate": 7, "postdoc": 8,
}

STAGE_ORDER = {
    "sse": 1, "hssc": 2, "ug": 3, "pg": 4,
    "doctorate": 5, "postdoc": 6, "other": 0,
}


# ── 1.1  extract_school_education ───────────────────────────────────────────
def extract_school_education(
    education_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Extract SSE/HSSC (school-level) education records.

    Input : education DataFrame filtered for one candidate
    Output: list of dicts with school education details
    """
    if education_df.empty:
        return []

    school_levels = {"ssc", "hssc", "sse"}
    school_stages = {"sse", "hssc"}

    records: List[Dict[str, Any]] = []
    for _, row in education_df.iterrows():
        level = str(row.get("degree_level", "")).lower().strip()
        stage = str(row.get("education_stage", "")).lower().strip()

        if level in school_levels or stage in school_stages:
            records.append({
                "degree_level": level if level in school_levels else stage,
                "degree_title_raw": row.get("degree_title_raw"),
                "degree_title_normalized": row.get("degree_title_normalized"),
                "institution_name": row.get("institution_name"),
                "board_or_university": row.get("board_or_university"),
                "passing_year": _safe_int(row.get("passing_year")),
                "score_raw": row.get("score_raw"),
                "score_normalized_percentage": _safe_float(
                    row.get("score_normalized_percentage")
                ),
            })
    return records


# ── 1.2  extract_higher_education ───────────────────────────────────────────
def extract_higher_education(
    education_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Extract UG / PG / MPhil / PhD / Postdoc education records.

    Input : education DataFrame filtered for one candidate
    Output: list of dicts with higher-education details
    """
    if education_df.empty:
        return []

    school_levels = {"ssc", "hssc", "sse"}
    school_stages = {"sse", "hssc"}

    records: List[Dict[str, Any]] = []
    for _, row in education_df.iterrows():
        level = str(row.get("degree_level", "")).lower().strip()
        stage = str(row.get("education_stage", "")).lower().strip()

        if level in school_levels or stage in school_stages:
            continue  # skip school records

        records.append({
            "degree_level": level or stage or "other",
            "education_stage": stage or level or "other",
            "degree_title_raw": row.get("degree_title_raw"),
            "degree_title_normalized": row.get("degree_title_normalized"),
            "specialization": row.get("specialization"),
            "institution_name": row.get("institution_name"),
            "board_or_university": row.get("board_or_university"),
            "admission_year": _safe_int(row.get("admission_year")),
            "completion_year": _safe_int(row.get("completion_year")),
            "passing_year": _safe_int(row.get("passing_year")),
            "score_raw": row.get("score_raw"),
            "score_type": row.get("score_type"),
            "score_value": _safe_float(row.get("score_value")),
            "score_scale": row.get("score_scale"),
            "score_normalized_percentage": _safe_float(
                row.get("score_normalized_percentage")
            ),
        })
    return records


# ── 1.3  normalize_degree_levels ────────────────────────────────────────────
def normalize_degree_levels(
    raw_degree: Optional[str],
    degree_level_hint: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Map raw degree title to canonical level.

    NOTE: M1 already normalizes degrees in normalization.py.
    This function is provided for any ad-hoc re-normalization needs in M2.
    Returns: {'raw': original, 'normalized': canonical_level}
    """
    if not raw_degree:
        return {"raw": raw_degree, "normalized": degree_level_hint}

    text = raw_degree.lower()

    patterns = [
        (r"\b(postdoc|post-?doctoral)\b", "postdoc"),
        (r"\b(ph\.?d|dphil|doctorate|doctoral)\b", "phd"),
        (r"\b(m\.?phil)\b", "mphil"),
        (r"\b(m\.?s\b|msc|master|m\.?eng|mba|ma\b|mcom)\b", "pg"),
        (r"\b(bs|bsc|be\b|bee|b\.?eng|bachelor|b\.?tech|btech)\b", "ug"),
        (r"\b(hssc|intermediate|f\.?sc|f\.?a|ics|a-?level)\b", "hssc"),
        (r"\b(ssc|sse|matric|o-?level)\b", "ssc"),
        (r"\b(diploma|certificate)\b", "diploma"),
    ]
    for pattern, level in patterns:
        if re.search(pattern, text):
            return {"raw": raw_degree, "normalized": level}

    return {"raw": raw_degree, "normalized": degree_level_hint or "other"}


# ── 1.4  normalize_academic_scores ──────────────────────────────────────────
def normalize_academic_scores(
    score_raw: Optional[str],
    score_type: Optional[str] = None,
    score_value: Optional[float] = None,
    score_scale: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert diverse score formats to percentage (0-100).

    NOTE: M1 already normalizes scores. This wraps the result for
    M2 assessment usage.
    """
    result: Dict[str, Any] = {
        "raw_score": score_raw,
        "score_type": score_type,
        "normalized_percentage": None,
        "score_scale": score_scale,
    }

    if score_value is not None and score_scale is not None:
        try:
            scale = float(score_scale)
            if scale > 0:
                result["normalized_percentage"] = round(
                    (score_value / scale) * 100, 2
                )
                return result
        except (ValueError, TypeError):
            pass

    if score_raw:
        text = str(score_raw).lower()
        frac = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
        if frac:
            val, sc = float(frac.group(1)), float(frac.group(2))
            if sc > 0:
                result["normalized_percentage"] = round((val / sc) * 100, 2)
                result["score_type"] = "fraction"
                return result

        if "%" in text:
            num = re.search(r"(\d+(?:\.\d+)?)", text)
            if num:
                result["normalized_percentage"] = float(num.group(1))
                result["score_type"] = "percentage"
                return result

    if score_value is not None:
        v = float(score_value)
        if 0 <= v <= 4.0:
            result["normalized_percentage"] = round((v / 4.0) * 100, 2)
            result["score_type"] = "cgpa"
            result["score_scale"] = "4.0"
        elif 4.0 < v <= 5.0:
            result["normalized_percentage"] = round((v / 5.0) * 100, 2)
            result["score_type"] = "cgpa"
            result["score_scale"] = "5.0"
        elif 5.0 < v <= 10.0:
            result["normalized_percentage"] = round((v / 10.0) * 100, 2)
            result["score_type"] = "cgpa"
            result["score_scale"] = "10.0"
        elif 10.0 < v <= 100.0:
            result["normalized_percentage"] = v
            result["score_type"] = "percentage"
            result["score_scale"] = "100"

    return result


# ── 1.5  assess_institution_quality ─────────────────────────────────────────
def assess_institution_quality(
    institution_name: Optional[str],
) -> Dict[str, Any]:
    """
    Placeholder for institutional quality assessment.

    Actual ranking API integration (THE, QS) deferred to M3.
    Returns default 'unknown' ranking status.
    """
    return {
        "institution_name": institution_name,
        "the_rank": None,
        "the_score": None,
        "qs_rank": None,
        "qs_score": None,
        "ranking_status": "unknown",
    }


# ── 1.6  analyze_educational_progression ────────────────────────────────────
def analyze_educational_progression(
    education_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyze chronological progression, specialization consistency,
    and academic performance trend across education records.
    """
    if not education_records:
        return {
            "progression_score": 0.0,
            "specialization_consistency": 0.0,
            "performance_trend": "variable",
            "details": [],
        }

    # Sort by best available year
    sorted_records = sorted(
        education_records,
        key=lambda r: _best_year(r) or 9999,
    )

    # — Chronological progression score —
    levels = []
    for rec in sorted_records:
        lvl = rec.get("degree_level", "other")
        order = DEGREE_ORDER.get(lvl, 0)
        levels.append(order)

    progression_score = 100.0
    if len(levels) >= 2:
        reversals = sum(
            1 for i in range(1, len(levels)) if levels[i] < levels[i - 1]
        )
        progression_score = max(0.0, 100.0 - reversals * 25.0)

    # — Specialization consistency —
    specializations = [
        str(r.get("specialization", "")).lower().strip()
        for r in sorted_records
        if r.get("specialization")
    ]
    spec_consistency = 100.0
    if len(specializations) >= 2:
        unique_specs = set(specializations)
        spec_consistency = round(
            (1 / len(unique_specs)) * 100, 1
        ) if unique_specs else 100.0

    # — Performance trend —
    scores = [
        r["score_normalized_percentage"]
        for r in sorted_records
        if r.get("score_normalized_percentage") is not None
    ]
    trend = _compute_trend(scores)

    return {
        "progression_score": round(progression_score, 1),
        "specialization_consistency": round(spec_consistency, 1),
        "performance_trend": trend,
        "details": [
            {
                "degree_level": r.get("degree_level"),
                "year": _best_year(r),
                "score": r.get("score_normalized_percentage"),
                "specialization": r.get("specialization"),
            }
            for r in sorted_records
        ],
    }


# ── 1.7  detect_educational_gaps ────────────────────────────────────────────
def detect_educational_gaps(
    education_records: List[Dict[str, Any]],
    experience_records: Optional[List[Dict[str, Any]]] = None,
    gap_threshold_months: int = 12,
) -> List[Dict[str, Any]]:
    """
    Identify gaps between education stages.
    Cross-references with employment to check if gaps are justified.
    """
    if not education_records or len(education_records) < 2:
        return []

    sorted_recs = sorted(
        education_records,
        key=lambda r: _best_year(r) or 9999,
    )

    gaps: List[Dict[str, Any]] = []
    for i in range(len(sorted_recs) - 1):
        end_year = sorted_recs[i].get("completion_year") or sorted_recs[i].get("passing_year")
        start_year = sorted_recs[i + 1].get("admission_year") or sorted_recs[i + 1].get("passing_year")

        if end_year is None or start_year is None:
            continue

        end_year = int(end_year)
        start_year = int(start_year)
        gap_months = (start_year - end_year) * 12

        if gap_months <= 0:
            continue

        from_level = sorted_recs[i].get("degree_level", "unknown")
        to_level = sorted_recs[i + 1].get("degree_level", "unknown")
        gap_type = f"{from_level}_to_{to_level}"

        # Check if justified by employment
        justified = False
        justification_detail = None
        if experience_records:
            for exp in experience_records:
                exp_start = exp.get("start_year")
                exp_end = exp.get("end_year")
                if exp_start and exp_end:
                    exp_s = int(exp_start)
                    exp_e = int(exp_end)
                    if exp_s <= start_year and exp_e >= end_year:
                        justified = True
                        justification_detail = (
                            f"Employed at {exp.get('organization', 'N/A')} "
                            f"as {exp.get('post_job_title', 'N/A')} "
                            f"({exp_s}-{exp_e})"
                        )
                        break

        gaps.append({
            "gap_type": gap_type,
            "duration_months": gap_months,
            "start_date": end_year,
            "end_date": start_year,
            "is_flagged": gap_months > gap_threshold_months,
            "justified_by_experience": justified,
            "justification_detail": justification_detail,
        })

    return gaps


# ── 1.8  generate_educational_assessment ────────────────────────────────────
def generate_educational_assessment(
    education_df: pd.DataFrame,
    experience_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Synthesize overall educational profile assessment for a candidate.

    Returns a comprehensive dict with all educational metrics and a narrative.
    """
    school = extract_school_education(education_df)
    higher = extract_higher_education(education_df)

    all_records = school + higher
    if not all_records:
        return _empty_educational_assessment()

    # Experience records for gap justification
    exp_records = _df_to_experience_list(experience_df) if experience_df is not None else []

    # Progression analysis
    progression = analyze_educational_progression(all_records)

    # Gap detection
    gaps = detect_educational_gaps(all_records, exp_records)

    # Institution quality (placeholder)
    institutions = [r.get("institution_name") for r in all_records if r.get("institution_name")]
    inst_quality = [assess_institution_quality(name) for name in institutions]

    # Scores
    all_scores = [
        r["score_normalized_percentage"]
        for r in all_records
        if r.get("score_normalized_percentage") is not None
    ]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else None

    # Highest qualification
    highest_level = _get_highest_degree_level(all_records)

    # Performance level
    perf_level = _classify_performance(avg_score)

    # Gap justification completeness
    flagged_gaps = [g for g in gaps if g.get("is_flagged")]
    justified_gaps = [g for g in flagged_gaps if g.get("justified_by_experience")]
    gap_completeness = (
        (len(justified_gaps) / len(flagged_gaps) * 100)
        if flagged_gaps
        else 100.0
    )

    # Continuity score (penalty for unexplained gaps)
    continuity = max(0.0, 100.0 - len(flagged_gaps) * 15.0 + len(justified_gaps) * 10.0)
    continuity = min(100.0, continuity)

    # Overall educational strength
    components = []
    if avg_score is not None:
        components.append(avg_score * 0.35)
    else:
        components.append(50.0 * 0.35)  # default

    components.append(progression["progression_score"] * 0.25)
    components.append(continuity * 0.20)
    components.append(progression["specialization_consistency"] * 0.10)
    components.append(gap_completeness * 0.10)

    overall_strength = round(sum(components), 1)

    # Narrative
    narrative = _build_education_narrative(
        highest_level, perf_level, avg_score,
        progression["performance_trend"], len(flagged_gaps),
    )

    return {
        "overall_educational_strength": overall_strength,
        "academic_performance_level": perf_level,
        "highest_qualification_level": highest_level,
        "institution_quality_average": None,  # M3
        "academic_consistency_score": round(progression["progression_score"], 1),
        "educational_continuity_score": round(continuity, 1),
        "gap_explanation_completeness": round(gap_completeness, 1),
        "specialization_consistency": round(progression["specialization_consistency"], 1),
        "performance_trend": progression["performance_trend"],
        "average_score": round(avg_score, 1) if avg_score else None,
        "school_records": school,
        "higher_education_records": higher,
        "progression_details": progression["details"],
        "gaps": gaps,
        "institution_quality": inst_quality,
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


def _safe_float(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _best_year(record: Dict) -> Optional[int]:
    for key in ("passing_year", "completion_year", "admission_year"):
        val = _safe_int(record.get(key))
        if val:
            return val
    return None


def _compute_trend(scores: List[float]) -> str:
    if len(scores) < 2:
        return "variable"
    diffs = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
    positive = sum(1 for d in diffs if d > 0)
    negative = sum(1 for d in diffs if d < 0)
    if positive > negative:
        return "improving"
    if negative > positive:
        return "declining"
    if all(abs(d) < 5 for d in diffs):
        return "stable"
    return "variable"


def _get_highest_degree_level(records: List[Dict]) -> str:
    best_order = 0
    best_level = "unknown"
    for r in records:
        lvl = r.get("degree_level", "other")
        order = DEGREE_ORDER.get(lvl, 0)
        if order > best_order:
            best_order = order
            best_level = lvl
    return best_level


def _classify_performance(avg_score: Optional[float]) -> str:
    if avg_score is None:
        return "unknown"
    if avg_score >= 85:
        return "excellent"
    if avg_score >= 75:
        return "very_good"
    if avg_score >= 65:
        return "good"
    if avg_score >= 50:
        return "fair"
    return "weak"


def _build_education_narrative(
    highest: str, level: str, avg: Optional[float],
    trend: str, flagged_count: int,
) -> str:
    parts = []
    level_names = {
        "ssc": "SSC/Matric", "hssc": "HSSC/Intermediate",
        "ug": "undergraduate", "bachelors": "undergraduate",
        "pg": "postgraduate", "masters": "postgraduate",
        "mphil": "MPhil", "phd": "PhD", "postdoc": "Postdoctoral",
    }
    h_name = level_names.get(highest, highest)
    parts.append(f"Candidate holds a {h_name} qualification.")

    if avg is not None:
        parts.append(
            f"Overall academic performance is {level} "
            f"with an average normalized score of {avg:.1f}%."
        )

    if trend in ("improving", "stable"):
        parts.append(f"Academic performance trend is {trend}.")
    elif trend == "declining":
        parts.append("Academic performance shows a declining trend.")

    if flagged_count > 0:
        parts.append(
            f"There {'is' if flagged_count == 1 else 'are'} "
            f"{flagged_count} notable gap(s) in the educational timeline."
        )

    return " ".join(parts)


def _df_to_experience_list(exp_df: pd.DataFrame) -> List[Dict[str, Any]]:
    if exp_df is None or exp_df.empty:
        return []
    records = []
    for _, row in exp_df.iterrows():
        records.append({
            "post_job_title": row.get("post_job_title"),
            "organization": row.get("organization"),
            "start_year": _safe_int(row.get("start_year")),
            "end_year": _safe_int(row.get("end_year")),
            "duration": row.get("duration"),
            "location": row.get("location"),
        })
    return records


def _empty_educational_assessment() -> Dict[str, Any]:
    return {
        "overall_educational_strength": 0.0,
        "academic_performance_level": "unknown",
        "highest_qualification_level": "unknown",
        "institution_quality_average": None,
        "academic_consistency_score": 0.0,
        "educational_continuity_score": 0.0,
        "gap_explanation_completeness": 0.0,
        "specialization_consistency": 0.0,
        "performance_trend": "variable",
        "average_score": None,
        "school_records": [],
        "higher_education_records": [],
        "progression_details": [],
        "gaps": [],
        "institution_quality": [],
        "narrative_summary": "No educational records available for assessment.",
    }
