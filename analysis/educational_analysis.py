"""
TALASH M2 - Educational Profile Analysis

Evaluates candidate's academic background in a structured, quantifiable manner.
Reuses M1 normalization functions — does NOT duplicate them.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

try:
    from google import genai
except Exception:  # pragma: no cover - handled at runtime
    genai = None

logger = logging.getLogger(__name__)

# Load .env so direct CLI runs can still access GEMINI_API_KEY.
load_dotenv()

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

# Expected time-to-completion thresholds (in years) by current level.
DEGREE_DURATION_THRESHOLDS = {
    "hssc": 2,
    "ug": 4,
    "bachelors": 4,
    "pg": 3,
    "masters": 3,
    "mphil": 3,
    "phd": 5,
    "doctorate": 5,
    "postdoc": 5,
}

RANKING_REFERENCE_URLS = {
    "the": "https://www.timeshighereducation.com/worlduniversity-rankings",
    "qs": "https://www.topuniversities.com/world-university-rankings",
}

_RANKING_CACHE: Dict[str, Dict[str, Any]] = {}


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
    Return ranking status for one institution.

    Rankings are enriched via LLM with strict instructions to avoid guessing.
    If unavailable or uncertain, values remain null and status is transparent.
    """
    cleaned_name = _clean_institution_name(institution_name)
    if not cleaned_name:
        return {
            "institution_name": institution_name,
            "the_rank": None,
            "the_score": None,
            "qs_rank": None,
            "qs_score": None,
            "ranking_status": "unavailable",
            "unavailable_reason": "No institution name provided.",
            "references": RANKING_REFERENCE_URLS,
        }

    rankings = _extract_rankings_for_institutions([cleaned_name])
    ranked = rankings.get(cleaned_name, {})

    the_rank = _safe_int(ranked.get("the_rank"))
    qs_rank = _safe_int(ranked.get("qs_rank"))
    the_score = _rank_to_quality_score(the_rank)
    qs_score = _rank_to_quality_score(qs_rank)
    status = _ranking_status_from_record(the_rank, qs_rank, ranked.get("status"))

    reason = ranked.get("reason")
    if not reason and status in {"unavailable", "unknown"}:
        reason = "No reliable THE/QS rank found for this institution."

    return {
        "institution_name": cleaned_name,
        "the_rank": the_rank,
        "the_score": the_score,
        "qs_rank": qs_rank,
        "qs_score": qs_score,
        "ranking_status": status,
        "unavailable_reason": reason,
        "references": RANKING_REFERENCE_URLS,
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
) -> List[Dict[str, Any]]:
    """
    Identify gaps between education stages.
    Cross-references with employment to check if gaps are justified.
    """
    if not education_records or len(education_records) < 2:
        return []

    sorted_recs = sorted(
        education_records,
        key=lambda r: _safe_int(r.get("passing_year")) or _best_year(r) or 9999,
    )

    gaps: List[Dict[str, Any]] = []
    for i in range(len(sorted_recs) - 1):
        prev_rec = sorted_recs[i]
        curr_rec = sorted_recs[i + 1]

        prev_year = _safe_int(prev_rec.get("passing_year") or prev_rec.get("completion_year"))
        curr_year = _safe_int(curr_rec.get("passing_year") or curr_rec.get("completion_year"))

        if prev_year is None or curr_year is None:
            continue

        completion_months = (curr_year - prev_year) * 12
        if completion_months <= 0:
            continue

        curr_level = _normalize_level_for_threshold(curr_rec.get("degree_level"))
        threshold_years = DEGREE_DURATION_THRESHOLDS.get(curr_level)
        if threshold_years is None:
            continue

        threshold_months = threshold_years * 12
        excess_months = max(0, completion_months - threshold_months)
        is_flagged = excess_months > 0
        if not is_flagged:
            continue

        # Represent only the unexplained/extra duration as the educational gap.
        gap_start_year = prev_year + threshold_years
        gap_end_year = curr_year

        from_level = prev_rec.get("degree_level", "unknown")
        to_level = curr_rec.get("degree_level", "unknown")
        gap_type = f"{from_level}_to_{to_level}"

        # Only flagged excess duration needs external justification.
        justified = False
        justification_detail = None
        if is_flagged and experience_records:
            gap_window_start = gap_start_year
            gap_window_end = gap_end_year
            for exp in experience_records:
                exp_start = exp.get("start_year")
                exp_end = exp.get("end_year")
                if exp_start:
                    exp_s = int(exp_start)
                    exp_e = int(exp_end) if exp_end else curr_year
                    overlaps = exp_s <= gap_window_end and exp_e >= gap_window_start
                    if overlaps:
                        justified = True
                        justification_detail = (
                            f"Employed at {exp.get('organization', 'N/A')} "
                            f"as {exp.get('post_job_title', 'N/A')} "
                            f"({exp_s}-{exp_e})"
                        )
                        break

        gaps.append({
            "gap_type": gap_type,
            "duration_months": excess_months,
            "allowed_duration_months": threshold_months,
            "excess_duration_months": excess_months,
            "start_date": gap_start_year,
            "end_date": gap_end_year,
            "is_flagged": is_flagged,
            "justified_by_experience": justified,
            "justification_detail": justification_detail,
            "threshold_rule": (
                f"{to_level.upper()} expected <= {threshold_years} year(s)"
            ),
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

    # Institution quality enrichment (THE + QS ranking checks)
    institutions = []
    seen_institutions = set()
    for r in higher:
        cleaned = _clean_institution_name(r.get("institution_name"))
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen_institutions:
            continue
        seen_institutions.add(key)
        institutions.append(cleaned)
    inst_quality = [assess_institution_quality(name) for name in institutions]

    ranking_scores: List[float] = []
    for item in inst_quality:
        item_scores = [
            s for s in [item.get("the_score"), item.get("qs_score")]
            if s is not None
        ]
        if item_scores:
            ranking_scores.append(sum(item_scores) / len(item_scores))

    inst_quality_avg = (
        round(sum(ranking_scores) / len(ranking_scores), 1)
        if ranking_scores
        else None
    )

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
        components.append(avg_score * 0.30)
    else:
        components.append(50.0 * 0.30)  # neutral default

    components.append(progression["progression_score"] * 0.20)
    components.append(continuity * 0.20)
    components.append(progression["specialization_consistency"] * 0.10)
    components.append(gap_completeness * 0.10)
    components.append((inst_quality_avg if inst_quality_avg is not None else 50.0) * 0.10)

    overall_strength = round(sum(components), 1)

    # Narrative
    narrative = _build_education_narrative(
        highest_level, perf_level, avg_score,
        progression["performance_trend"], len(flagged_gaps), inst_quality_avg,
    )

    return {
        "overall_educational_strength": overall_strength,
        "academic_performance_level": perf_level,
        "highest_qualification_level": highest_level,
        "institution_quality_average": inst_quality_avg,
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
        "strength_breakdown": {
            "academic_performance_weight": 0.30,
            "progression_weight": 0.20,
            "continuity_weight": 0.20,
            "specialization_weight": 0.10,
            "gap_justification_weight": 0.10,
            "institution_quality_weight": 0.10,
            "institution_quality_used": (
                inst_quality_avg if inst_quality_avg is not None else 50.0
            ),
        },
        "narrative_summary": narrative,
    }


# ── Helper functions ────────────────────────────────────────────────────────

def _safe_int(val: Any) -> Optional[int]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if isinstance(val, str):
            text = val.strip()
            if not text:
                return None

            # Support ranking formats such as "#451", "401-500", "=215", "1,024".
            match = re.search(r"\d+(?:,\d+)?", text)
            if match:
                return int(match.group(0).replace(",", ""))

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
    trend: str, flagged_count: int, institution_quality_avg: Optional[float],
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

    if institution_quality_avg is not None:
        parts.append(
            f"Average institutional quality score (THE/QS-based) is "
            f"{institution_quality_avg:.1f}/100."
        )
    else:
        parts.append(
            "Institution rankings (THE/QS) are unavailable for one or more "
            "institutions and are reported transparently as unavailable."
        )

    return " ".join(parts)


def _normalize_level_for_threshold(level: Optional[str]) -> str:
    if not level:
        return "other"
    lvl = str(level).strip().lower()
    alias = {
        "sse": "ssc",
        "matric": "ssc",
        "intermediate": "hssc",
        "bsc": "ug",
        "bs": "ug",
        "ms": "pg",
        "mba": "pg",
    }
    return alias.get(lvl, lvl)


def _clean_institution_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    cleaned = str(name).strip()
    if not cleaned or cleaned.lower() in {"nan", "none", "null"}:
        return None
    return re.sub(r"\s+", " ", cleaned)


def _rank_to_quality_score(rank: Optional[int], max_rank: int = 2000) -> Optional[float]:
    if rank is None or rank <= 0:
        return None
    clamped = min(rank, max_rank)
    score = 100.0 * (1.0 - (clamped - 1) / max_rank)
    return round(max(0.0, min(100.0, score)), 1)


def _ranking_status_from_record(
    the_rank: Optional[int],
    qs_rank: Optional[int],
    upstream_status: Optional[str] = None,
) -> str:
    if the_rank is not None and qs_rank is not None:
        return "both_available"
    if the_rank is not None:
        return "the_only"
    if qs_rank is not None:
        return "qs_only"
    if upstream_status in {"unavailable", "unknown"}:
        return upstream_status
    return "unavailable"


def _extract_rankings_for_institutions(
    institutions: List[str],
) -> Dict[str, Dict[str, Any]]:
    unique_names = []
    seen = set()
    for name in institutions:
        cleaned = _clean_institution_name(name)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_names.append(cleaned)

    if not unique_names:
        return {}

    results: Dict[str, Dict[str, Any]] = {}
    missing = []
    for name in unique_names:
        if name in _RANKING_CACHE:
            results[name] = _RANKING_CACHE[name]
        else:
            missing.append(name)

    if missing:
        fetched = _call_gemini_for_rankings(missing)
        for name in missing:
            record = fetched.get(name) or {
                "institution_name": name,
                "the_rank": None,
                "qs_rank": None,
                "status": "unavailable",
                "reason": "No ranking found from configured sources.",
            }
            _RANKING_CACHE[name] = record
            results[name] = record

    return results


def _call_gemini_for_rankings(
    institutions: List[str],
) -> Dict[str, Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return {
            name: {
                "institution_name": name,
                "the_rank": None,
                "qs_rank": None,
                "status": "unavailable",
                "reason": "Gemini API key or SDK unavailable.",
            }
            for name in institutions
        }

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        "You are filling university rankings for hiring analytics. "
        "For each institution, use best-effort lookup and include common aliases "
        "(abbreviations, campus suffixes, punctuation variants). "
        "Return THE World University Ranking and QS World University Ranking values "
        "when available. If not confidently available, return null. "
        "Never guess fabricated numbers.\n\n"
        "Important normalization rules:\n"
        "1) If rank appears as a range (e.g., 401-500), return the lower bound integer (401).\n"
        "2) If rank has symbols (#, =), return integer only.\n"
        "3) Match each output row to one provided input institution name.\n\n"
        "Respond ONLY as a JSON array.\n"
        "Schema per item: "
        "{\"institution_name\": str, \"the_rank\": int|null, \"qs_rank\": int|null, "
        "\"status\": \"both_available\"|\"the_only\"|\"qs_only\"|\"unavailable\"|\"unknown\", "
        "\"reason\": str|null}.\n"
        f"Institutions: {json.dumps(institutions)}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = getattr(response, "text", "") or ""
        rows = _extract_json_array(text)
    except Exception as exc:
        logger.warning("Ranking enrichment request failed: %s", exc)
        rows = []

    requested_by_norm = {_normalize_institution_key(n): n for n in institutions}

    by_name: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = _clean_institution_name(row.get("institution_name"))
        if not name:
            continue

        matched = _match_requested_institution_name(name, institutions)
        key_name = matched or requested_by_norm.get(_normalize_institution_key(name)) or name
        by_name[key_name] = {
            "institution_name": key_name,
            "the_rank": _safe_int(row.get("the_rank")),
            "qs_rank": _safe_int(row.get("qs_rank")),
            "status": str(row.get("status") or "unknown"),
            "reason": row.get("reason"),
        }

    for name in institutions:
        if name not in by_name:
            by_name[name] = {
                "institution_name": name,
                "the_rank": None,
                "qs_rank": None,
                "status": "unavailable",
                "reason": "No ranking record returned by enrichment step.",
            }

    return by_name


def _normalize_institution_key(name: str) -> str:
    key = name.lower().strip()
    key = re.sub(r"[^a-z0-9\s]", " ", key)
    key = re.sub(r"\b(university|institute|campus|college|of|the|and)\b", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


def _match_requested_institution_name(
    returned_name: str,
    requested_names: List[str],
) -> Optional[str]:
    ret_key = _normalize_institution_key(returned_name)
    if not ret_key:
        return None

    for req in requested_names:
        req_key = _normalize_institution_key(req)
        if not req_key:
            continue
        if req_key == ret_key or req_key in ret_key or ret_key in req_key:
            return req

    return None


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    stripped = text.strip()
    candidates = [stripped]

    # Also try extracting first JSON array from markdown-style wrappers.
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidates.append(stripped[start:end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            continue

    return []


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
        "strength_breakdown": {
            "academic_performance_weight": 0.30,
            "progression_weight": 0.20,
            "continuity_weight": 0.20,
            "specialization_weight": 0.10,
            "gap_justification_weight": 0.10,
            "institution_quality_weight": 0.10,
            "institution_quality_used": 50.0,
        },
        "narrative_summary": "No educational records available for assessment.",
    }
