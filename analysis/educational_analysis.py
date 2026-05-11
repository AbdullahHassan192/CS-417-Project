"""
TALASH M2 - Educational Profile Analysis

Evaluates candidate's academic background in a structured, quantifiable manner.
Reuses M1 normalization functions — does NOT duplicate them.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from analysis.regex_rank_lookup import resolve_university_rank_regex

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

EXPECTED_DEGREE_DURATIONS = {
    "hssc": 2,
    "ug": 4,
    "bachelors": 4,
    "pg": 3,
    "masters": 3,
    "mphil": 3,
    "phd": 5,
    "doctorate": 5,
}

PROFESSIONAL_ACTIVITY_KEYWORDS = {
    "teaching": [r"\b(lecturer|teacher|instructor|professor|faculty)\b"],
    "internship": [r"\b(intern|internship)\b"],
    "freelancing": [r"\b(freelanc|independent)\b"],
    "research": [r"\b(research|researcher|r\s*&\s*d)\b"],
    "consultancy": [r"\b(consult|advisor|advisory)\b"],
    "entrepreneurship": [r"\b(founder|co-?founder|entrepreneur|startup|owner)\b"],
    "assistantships": [r"\b(assistantship|teaching assistant|research assistant|\bta\b|\bra\b)\b"],
}

_project_root = Path(__file__).resolve().parent.parent
_rankings_file = _project_root / "data" / "university_rankings.json"
_rankings_cache_file = _project_root / "data" / "university_rankings_cache.json"
_runtime_ranking_cache: Dict[str, Dict[str, Any]] = {}


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
                "qs_rank_reported": _safe_int(row.get("qs_rank_reported")),
                "the_rank_reported": _safe_int(row.get("the_rank_reported")),
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
            "qs_rank_reported": _safe_int(row.get("qs_rank_reported")),
            "the_rank_reported": _safe_int(row.get("the_rank_reported")),
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
    llm_qs_rank: Optional[Any] = None,
    llm_the_rank: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Resolve institutional quality with primary source from LLM-provided ranking,
    then fallback to local QS/THE file when unknown.
    """
    parsed_llm_qs = _parse_rank_value(llm_qs_rank)
    parsed_llm_the = _parse_rank_value(llm_the_rank)

    if not institution_name:
        return {
            "institution_name": institution_name,
            "matched_name": None,
            "the_rank": None,
            "the_score": None,
            "qs_rank": None,
            "qs_score": None,
            "qs_display": "Not Found",
            "the_display": "Not Found",
            "ranking_status": "not_found",
            "ranking_score": 35.0,
            "ranking_source": "none",
        }

    qs_rank = parsed_llm_qs
    the_rank = parsed_llm_the
    matched_name = institution_name
    ranking_source = "llm" if (parsed_llm_qs is not None or parsed_llm_the is not None) else "not_found"

    # Fallback to regex-based lookup in data\qs_ranks.json when LLM could not provide value(s).
    if qs_rank is None or the_rank is None:
        matched_data = resolve_university_rank_regex(institution_name)
        if matched_data:
            matched_name = matched_data.get("matched_name") or matched_name
            if qs_rank is None:
                qs_rank = _parse_rank_value(matched_data.get("rank"))
            if the_rank is None:
                # qs_ranks.json does not include THE; proxy to same rank only when missing.
                the_rank = _parse_rank_value(matched_data.get("rank"))
            ranking_source = "llm+regex_qs" if ranking_source == "llm" else "regex_qs"

    qs_score = _rank_to_quality_score(qs_rank)
    the_score = _rank_to_quality_score(the_rank)
    rank_scores = [s for s in (qs_score, the_score) if s is not None]
    ranking_score = round(sum(rank_scores) / len(rank_scores), 1) if rank_scores else 35.0

    resolved = {
        "institution_name": institution_name,
        "matched_name": matched_name,
        "the_rank": the_rank,
        "the_score": the_score,
        "qs_rank": qs_rank,
        "qs_score": qs_score,
        "qs_display": str(qs_rank) if qs_rank is not None else "Not Found",
        "the_display": str(the_rank) if the_rank is not None else "Not Found",
        "ranking_status": "found" if qs_rank is not None or the_rank is not None else "not_found",
        "ranking_score": ranking_score,
        "ranking_source": ranking_source,
    }
    return resolved


def _resolve_ranking_with_fallbacks(institution_name: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    rankings = _load_university_rankings()
    if not rankings:
        return None, None

    # 1) Exact key lookup
    if institution_name in rankings:
        return institution_name, rankings[institution_name]

    # 2) Case-insensitive and normalized-key exact lookup
    normalized_input = _normalize_institution_name(institution_name)
    normalized_map = {
        _normalize_institution_name(key): key
        for key in rankings.keys()
    }
    direct_key = normalized_map.get(normalized_input)
    if direct_key:
        return direct_key, rankings[direct_key]

    # 3) Try generated name variations
    for variation in _generate_institution_variations(institution_name):
        if variation in rankings:
            return variation, rankings[variation]
        normalized_variation = _normalize_institution_name(variation)
        direct_key = normalized_map.get(normalized_variation)
        if direct_key:
            return direct_key, rankings[direct_key]

    return None, None


def _load_university_rankings() -> Dict[str, Dict[str, Any]]:
    if not _rankings_file.exists():
        logger.warning("University rankings file not found at %s", _rankings_file)
        return {}
    try:
        with open(_rankings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Failed to load university rankings: %s", exc)
        return {}


def _load_rank_lookup_cache() -> Dict[str, Dict[str, Any]]:
    if not _rankings_cache_file.exists():
        return {}
    try:
        with open(_rankings_cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_rank_lookup_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    try:
        _rankings_cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_rankings_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _normalize_institution_name(name: Optional[str]) -> str:
    if not name:
        return ""
    text = str(name).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\(\)\[\],.\-_/]", " ", text)
    text = re.sub(r"\b(the|campus|pakistan|islamabad|lahore|karachi|peshawar)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _generate_institution_variations(name: str) -> List[str]:
    base = str(name).strip()
    if not base:
        return []

    variations = {
        base,
        base.replace("&", "and"),
        base.replace("and", "&"),
        re.sub(r"\s*\(.*?\)", "", base).strip(),
        re.sub(r"\bUniversity\b", "Univ", base, flags=re.IGNORECASE).strip(),
        re.sub(r"\bUniv\b", "University", base, flags=re.IGNORECASE).strip(),
        re.sub(r"\bIslamabad|Lahore|Karachi|Peshawar|Pakistan\b", "", base, flags=re.IGNORECASE).strip(),
    }
    abbreviations = {
        "national university of sciences and technology": "NUST",
        "comsats university islamabad": "COMSATS",
        "national university of computer and emerging sciences": "FAST",
        "fast nuces": "FAST-NUCES",
        "foundation university islamabad": "Foundation University",
        "qurtuba university of science and information technology": "Qurtuba University",
    }
    normalized = _normalize_institution_name(base)
    if normalized in abbreviations:
        variations.add(abbreviations[normalized])
    for full_name, short_name in abbreviations.items():
        if short_name.lower() in normalized:
            variations.add(full_name.title())
            variations.add(short_name)
    return [v for v in variations if v]


def _rank_to_quality_score(rank: Optional[int]) -> Optional[float]:
    if rank is None:
        return None
    if rank <= 10:
        return 100.0
    if rank <= 50:
        return 95.0
    if rank <= 100:
        return 90.0
    if rank <= 200:
        return 80.0
    if rank <= 400:
        return 70.0
    if rank <= 600:
        return 60.0
    if rank <= 800:
        return 50.0
    if rank <= 1000:
        return 40.0
    return 30.0


def _is_cache_match_valid(institution_name: str, cached_data: Dict[str, Any]) -> bool:
    matched_name = cached_data.get("matched_name")
    if not matched_name:
        return True
    normalized_query = _normalize_institution_name(institution_name)
    allowed = {_normalize_institution_name(v) for v in _generate_institution_variations(institution_name)}
    allowed.add(normalized_query)
    return _normalize_institution_name(matched_name) in allowed


def _parse_rank_value(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = int(value)
        return v if v > 0 else None

    text = str(value).strip().lower()
    if text in {"", "not found", "unknown", "n/a", "na", "none", "null", "-", "--"}:
        return None

    match = re.search(r"\d{1,4}", text)
    if not match:
        return None
    parsed = int(match.group(0))
    return parsed if parsed > 0 else None


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
    Identify only the excess unexplained years between education transitions.
    Gap = (difference between completion years) - expected duration of next degree.
    """
    if not education_records or len(education_records) < 2:
        return []

    sorted_recs = sorted(
        education_records,
        key=lambda r: _best_year(r) or 9999,
    )

    gaps: List[Dict[str, Any]] = []
    for i in range(len(sorted_recs) - 1):
        prev_end = sorted_recs[i].get("completion_year") or sorted_recs[i].get("passing_year")
        next_end = sorted_recs[i + 1].get("completion_year") or sorted_recs[i + 1].get("passing_year")
        if prev_end is None or next_end is None:
            continue

        prev_end = int(prev_end)
        next_end = int(next_end)
        if next_end <= prev_end:
            continue

        from_level = _canonical_degree_level(
            sorted_recs[i].get("degree_level"),
            sorted_recs[i].get("degree_title_raw"),
        )
        to_level = _canonical_degree_level(
            sorted_recs[i + 1].get("degree_level"),
            sorted_recs[i + 1].get("degree_title_raw"),
        )
        expected_duration = EXPECTED_DEGREE_DURATIONS.get(to_level)
        if expected_duration is None:
            continue

        transition_years = next_end - prev_end
        actual_gap_years = max(0, transition_years - expected_duration)
        if actual_gap_years <= 0:
            continue

        gap_start = next_end - actual_gap_years
        gap_end = next_end
        gap_type = f"{from_level}_to_{to_level}"

        justified, justification_detail = _gap_justified_by_professional_activity(
            gap_start=gap_start,
            gap_end=gap_end,
            experience_records=experience_records or [],
        )

        gaps.append({
            "gap_type": gap_type,
            "from_level": from_level,
            "to_level": to_level,
            "duration_months": int(actual_gap_years * 12),
            "duration_years": round(float(actual_gap_years), 1),
            "start_date": gap_start,
            "end_date": gap_end,
            "is_flagged": True,
            "justified_by_experience": justified,
            "status": "Justified" if justified else "Unexplained",
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

    # Institution quality enrichment (QS/THE) only for higher education records.
    institution_records: Dict[str, Dict[str, Any]] = {}
    for record in higher:
        institution_name = record.get("institution_name") or record.get("board_or_university")
        ranking = assess_institution_quality(
            institution_name=institution_name,
            llm_qs_rank=record.get("qs_rank_reported"),
            llm_the_rank=record.get("the_rank_reported"),
        )
        record["institution_ranking"] = ranking
        record["qs_rank"] = ranking["qs_rank"]
        record["the_rank"] = ranking["the_rank"]
        record["qs_display"] = ranking["qs_display"]
        record["the_display"] = ranking["the_display"]
        dedupe_key = _normalize_institution_name(institution_name)
        if dedupe_key and dedupe_key not in institution_records:
            institution_records[dedupe_key] = ranking
    inst_quality = list(institution_records.values())

    # Explicitly avoid ranking display for school-level records.
    for rec in school:
        rec["institution_ranking"] = None
        rec["qs_rank"] = None
        rec["the_rank"] = None
        rec["qs_display"] = "N/A (SSC/HSSC)"
        rec["the_display"] = "N/A (SSC/HSSC)"

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

    # Gap justification completeness and continuity
    flagged_gaps = gaps
    justified_gaps = [g for g in flagged_gaps if g.get("justified_by_experience")]
    gap_completeness = (
        (len(justified_gaps) / len(flagged_gaps) * 100)
        if flagged_gaps
        else 100.0
    )
    total_gap_years = sum(float(g.get("duration_years", 0)) for g in flagged_gaps)
    unexplained_count = len([g for g in flagged_gaps if not g.get("justified_by_experience")])
    continuity_penalty = total_gap_years * 12 + unexplained_count * 12
    continuity = max(0.0, min(100.0, 100.0 - continuity_penalty))

    ranking_scores = [r.get("ranking_score") for r in inst_quality if r.get("ranking_score") is not None]
    institution_quality_avg = (
        round(sum(ranking_scores) / len(ranking_scores), 1)
        if ranking_scores
        else None
    )

    overall_strength, strength_breakdown = _calculate_educational_strength(
        average_score=avg_score,
        highest_level=highest_level,
        institution_quality_avg=institution_quality_avg,
        consistency_score=progression["progression_score"],
        gaps=gaps,
    )

    # Narrative
    narrative = _build_education_narrative(
        highest_level, perf_level, avg_score,
        progression["performance_trend"], len(flagged_gaps),
    )

    return {
        "overall_educational_strength": overall_strength,
        "educational_strength_band": _classify_educational_strength(overall_strength),
        "educational_strength_breakdown": strength_breakdown,
        "academic_performance_level": perf_level,
        "highest_qualification_level": highest_level,
        "institution_quality_average": institution_quality_avg,
        "academic_consistency_score": round(progression["progression_score"], 1),
        "educational_continuity_score": round(continuity, 1),
        "gap_explanation_completeness": round(gap_completeness, 1),
        "specialization_consistency": round(progression["specialization_consistency"], 1),
        "performance_trend": progression["performance_trend"],
        "average_score": round(avg_score, 1) if avg_score is not None else None,
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
            "employment_type": row.get("employment_type"),
            "duration": row.get("duration"),
            "location": row.get("location"),
        })
    return records


def _canonical_degree_level(level: Optional[str], degree_title: Optional[str]) -> str:
    level_text = (level or "").strip().lower()
    if level_text in DEGREE_ORDER:
        return level_text
    inferred = normalize_degree_levels(degree_title, level_text).get("normalized") or "other"
    if inferred == "other" and level_text:
        return level_text
    return inferred


def _gap_justified_by_professional_activity(
    gap_start: int,
    gap_end: int,
    experience_records: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    current_year = datetime.now().year
    for exp in experience_records:
        exp_start = _safe_int(exp.get("start_year"))
        exp_end = _safe_int(exp.get("end_year")) or current_year
        if exp_start is None:
            continue
        overlaps_gap = exp_start <= gap_end and exp_end >= gap_start
        if not overlaps_gap:
            continue

        activity = _classify_professional_activity(exp)
        if activity is None:
            continue

        title = exp.get("post_job_title") or "N/A"
        org = exp.get("organization") or "N/A"
        end_label = exp.get("end_year") or "Present"
        detail = f"Worked as {title} at {org} ({exp_start}–{end_label})"
        return True, detail
    return False, None


def _classify_professional_activity(exp_record: Dict[str, Any]) -> Optional[str]:
    title = str(exp_record.get("post_job_title") or "").lower()
    emp_type = str(exp_record.get("employment_type") or "").lower()
    combined = f"{title} {emp_type}"

    for activity, patterns in PROFESSIONAL_ACTIVITY_KEYWORDS.items():
        if any(re.search(pattern, combined) for pattern in patterns):
            return activity

    if title:
        return "employment"
    return None


def _calculate_educational_strength(
    average_score: Optional[float],
    highest_level: str,
    institution_quality_avg: Optional[float],
    consistency_score: float,
    gaps: List[Dict[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    weights = {
        "academic_scores": 0.30,
        "highest_qualification": 0.20,
        "institution_quality": 0.15,
        "academic_consistency": 0.15,
        "educational_gaps": 0.10,
        "gap_justification": 0.10,
    }
    qualification_base = {
        "ssc": 25.0,
        "hssc": 35.0,
        "diploma": 45.0,
        "ug": 65.0,
        "bachelors": 65.0,
        "pg": 78.0,
        "masters": 78.0,
        "mphil": 88.0,
        "phd": 96.0,
        "doctorate": 96.0,
        "postdoc": 100.0,
    }

    academic_scores_raw = average_score if average_score is not None else 50.0
    highest_qualification_raw = qualification_base.get(highest_level, 50.0)
    institution_quality_raw = institution_quality_avg if institution_quality_avg is not None else 35.0
    academic_consistency_raw = max(0.0, min(100.0, consistency_score))

    total_gap_years = sum(float(g.get("duration_years", 0)) for g in gaps)
    unexplained = len([g for g in gaps if not g.get("justified_by_experience")])
    educational_gaps_raw = max(0.0, 100.0 - (total_gap_years * 20.0) - (unexplained * 15.0))
    gap_justification_raw = (
        (len([g for g in gaps if g.get("justified_by_experience")]) / len(gaps) * 100.0)
        if gaps else 100.0
    )

    components = {
        "academic_scores": round(academic_scores_raw * weights["academic_scores"], 2),
        "highest_qualification": round(highest_qualification_raw * weights["highest_qualification"], 2),
        "institution_quality": round(institution_quality_raw * weights["institution_quality"], 2),
        "academic_consistency": round(academic_consistency_raw * weights["academic_consistency"], 2),
        "educational_gaps": round(educational_gaps_raw * weights["educational_gaps"], 2),
        "gap_justification": round(gap_justification_raw * weights["gap_justification"], 2),
    }
    overall = round(sum(components.values()), 1)
    breakdown = {
        "weights": weights,
        "raw_scores": {
            "academic_scores": round(academic_scores_raw, 1),
            "highest_qualification": round(highest_qualification_raw, 1),
            "institution_quality": round(institution_quality_raw, 1),
            "academic_consistency": round(academic_consistency_raw, 1),
            "educational_gaps": round(educational_gaps_raw, 1),
            "gap_justification": round(gap_justification_raw, 1),
        },
        "weighted_contributions": components,
    }
    return overall, breakdown


def _empty_educational_assessment() -> Dict[str, Any]:
    return {
        "overall_educational_strength": 0.0,
        "educational_strength_band": "below_average",
        "educational_strength_breakdown": {
            "weights": {},
            "raw_scores": {},
            "weighted_contributions": {},
        },
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


def _classify_educational_strength(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 75:
        return "very_good"
    if score >= 65:
        return "good"
    if score >= 50:
        return "fair"
    return "below_average"
