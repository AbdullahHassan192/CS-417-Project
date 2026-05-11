from __future__ import annotations

import re
from typing import Optional

from models import ExtractionResult, PublicationItem


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"n/a", "na", "none", "null", "-", "--"}:
        return None
    return cleaned


def first_non_null(*values: Optional[str]) -> Optional[str]:
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return None


def parse_year(value: Optional[str]) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(19\d{2}|20\d{2})", text)
    if not match:
        return None
    return int(match.group(1))


def normalize_degree_title(
    raw_degree: Optional[str],
    specialization: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return canonical degree title, degree level, and education stage."""
    degree = clean_text(raw_degree)
    spec = clean_text(specialization)
    combined = " ".join(part for part in [degree, spec] if part)
    if not combined:
        return None, None, None

    text = combined.lower()

    if re.search(r"\b(postdoc|post-doctoral|post doctoral)\b", text):
        return "Postdoctoral", "postdoc", "postdoc"
    if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", text):
        return "PhD", "phd", "doctorate"
    if re.search(r"\b(m\.?phil|mphil)\b", text):
        return "MPhil", "mphil", "pg"
    if re.search(r"\b(m\.?s\b|msc\b|master|m\.?eng|mba\b|ma\b|mcom\b)\b", text):
        return "Master's", "masters", "pg"
    if re.search(r"\b(bs\b|bsc\b|be\b|bee\b|b\.?eng\b|bachelor|b\.tech|btech)\b", text):
        return "Bachelor's", "bachelors", "ug"
    if re.search(r"\b(hssc|intermediate|f\.?(sc|a)|ics|a-?level)\b", text):
        return "HSSC/Intermediate", "hssc", "hssc"
    if re.search(r"\b(ssc|sse|matric|o-?level)\b", text):
        return "SSC/SSE/Matric", "ssc", "sse"
    if re.search(r"\b(diploma|certificate)\b", text):
        return "Diploma/Certificate", "diploma", "other"
    if re.search(
        r"\b(engineering|computer science|information technology|electronics|telecommunications|software)\b",
        text,
    ):
        return first_non_null(degree, spec), "discipline_only", "ug_pg_unspecified"

    if degree:
        return degree, None, "other"
    return None, None, "other"


def normalize_level_hint(value: Optional[str]) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    lower = text.lower()
    if lower in {"ssc", "hssc", "ug", "pg", "mphil", "phd", "postdoc", "other"}:
        return lower
    if "bachelor" in lower:
        return "ug"
    if "master" in lower:
        return "pg"
    if "doctor" in lower:
        return "phd"
    if "inter" in lower:
        return "hssc"
    if "matric" in lower:
        return "ssc"
    return "other"


def level_to_stage(level: Optional[str]) -> Optional[str]:
    if not level:
        return None
    mapping = {
        "ssc": "sse",
        "hssc": "hssc",
        "ug": "ug",
        "pg": "pg",
        "mphil": "pg",
        "phd": "doctorate",
        "postdoc": "postdoc",
        "other": "other",
    }
    return mapping.get(level, "other")


def normalize_stage_hint(value: Optional[str]) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    lower = text.lower()
    if lower in {"sse", "hssc", "ug", "pg", "doctorate", "postdoc", "other", "ug_pg_unspecified"}:
        return lower
    if "ssc" in lower or "matric" in lower:
        return "sse"
    if "inter" in lower or "hssc" in lower:
        return "hssc"
    if "bachelor" in lower or "under" in lower:
        return "ug"
    if "master" in lower or "post" in lower:
        return "pg"
    if "doctor" in lower or "phd" in lower:
        return "doctorate"
    return "other"


def format_float(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def normalize_score(score_raw: Optional[str]) -> dict[str, Optional[str]]:
    """
    Normalize marks/CGPA while preserving the original score text.
    Returns normalized percentage only when reasonably derivable.
    """
    result = {
        "score_raw": clean_text(score_raw),
        "score_type": None,
        "score_value": None,
        "score_scale": None,
        "score_normalized_percentage": None,
        "score_normalization_basis": None,
    }

    raw = result["score_raw"]
    if not raw:
        return result

    text = raw.lower()

    frac = re.search(r"(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)", text)
    if frac:
        value = float(frac.group(1))
        scale = float(frac.group(2))
        if scale > 0:
            result["score_type"] = "fraction"
            result["score_value"] = format_float(value)
            result["score_scale"] = format_float(scale)
            result["score_normalized_percentage"] = format_float((value / scale) * 100)
            result["score_normalization_basis"] = "value_divided_by_scale"
            return result

    if "%" in text or "percentage" in text or "percent" in text:
        num = re.search(r"(-?\d+(?:\.\d+)?)", text)
        if num:
            value = float(num.group(1))
            result["score_type"] = "percentage"
            result["score_value"] = format_float(value)
            result["score_scale"] = "100"
            result["score_normalized_percentage"] = format_float(value)
            result["score_normalization_basis"] = "explicit_percentage"
            return result

    cgpa = re.search(r"cgpa\s*[:=]?\s*(-?\d+(?:\.\d+)?)", text)
    if cgpa:
        value = float(cgpa.group(1))
        if value <= 4.0:
            scale = 4.0
        elif value <= 5.0:
            scale = 5.0
        else:
            scale = 10.0
        result["score_type"] = "cgpa"
        result["score_value"] = format_float(value)
        result["score_scale"] = format_float(scale)
        result["score_normalized_percentage"] = format_float((value / scale) * 100)
        result["score_normalization_basis"] = "cgpa_keyword_with_default_scale"
        return result

    num = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", raw)
    if num:
        value = float(num.group(1))
        result["score_value"] = format_float(value)

        if 0 <= value <= 4.0:
            result["score_type"] = "cgpa"
            result["score_scale"] = "4"
            result["score_normalized_percentage"] = format_float((value / 4.0) * 100)
            result["score_normalization_basis"] = "heuristic_numeric_le_4_assumed_cgpa4"
            return result
        if 4.0 < value <= 5.0:
            result["score_type"] = "cgpa"
            result["score_scale"] = "5"
            result["score_normalized_percentage"] = format_float((value / 5.0) * 100)
            result["score_normalization_basis"] = "heuristic_numeric_le_5_assumed_cgpa5"
            return result
        if 5.0 < value <= 10.0:
            result["score_type"] = "cgpa"
            result["score_scale"] = "10"
            result["score_normalized_percentage"] = format_float((value / 10.0) * 100)
            result["score_normalization_basis"] = "heuristic_numeric_le_10_assumed_cgpa10"
            return result
        if 10.0 < value <= 100.0:
            result["score_type"] = "percentage"
            result["score_scale"] = "100"
            result["score_normalized_percentage"] = format_float(value)
            result["score_normalization_basis"] = "heuristic_numeric_le_100_assumed_percentage"
            return result

        result["score_type"] = "raw_numeric"
        result["score_normalization_basis"] = "numeric_outside_supported_range"
        return result

    if "division" in text:
        result["score_type"] = "division"
        result["score_normalization_basis"] = "division_not_converted"
        return result

    if re.search(r"\b(a\+|a-|a|b\+|b-|b|c\+|c|d|f)\b", text):
        result["score_type"] = "grade"
        result["score_normalization_basis"] = "letter_grade_not_converted"
        return result

    result["score_type"] = "unparsed"
    result["score_normalization_basis"] = "unable_to_parse"
    return result


def extract_year_bounds_from_duration(duration: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    text = clean_text(duration)
    if not text:
        return None, None

    years = [int(year) for year in re.findall(r"(19\d{2}|20\d{2})", text)]
    if not years:
        return None, None
    if len(years) == 1:
        if re.search(r"present|current", text, re.IGNORECASE):
            return years[0], None
        return years[0], years[0]
    return years[0], years[-1]


def split_authors(authors_text: Optional[str]) -> list[str]:
    text = clean_text(authors_text)
    if not text:
        return []
    parts = re.split(r",|;| and ", text, flags=re.IGNORECASE)
    return [clean_text(part) for part in parts if clean_text(part)]


def normalize_name_for_match(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def infer_authorship_role(
    authors_text: Optional[str],
    candidate_name: Optional[str],
) -> tuple[Optional[int], Optional[str], Optional[bool], Optional[bool], int]:
    authors = split_authors(authors_text)
    author_count = len(authors)
    if not authors:
        return None, None, None, None, 0

    candidate = clean_text(candidate_name)
    if not candidate:
        return None, None, None, None, author_count

    norm_candidate = normalize_name_for_match(candidate)
    position: Optional[int] = None
    for idx, author in enumerate(authors, start=1):
        norm_author = normalize_name_for_match(author)
        if norm_candidate == norm_author or norm_candidate in norm_author or norm_author in norm_candidate:
            position = idx
            break

    if position is None:
        return None, "not_listed_or_unmatched", False, None, author_count

    is_first = position == 1
    is_corresponding = True if "*" in (authors_text or "") and is_first else None

    if is_first and is_corresponding is True:
        role = "first_and_corresponding_author"
    elif is_first:
        role = "first_author"
    elif is_corresponding is True:
        role = "corresponding_author"
    else:
        role = "co_author"

    return position, role, is_first, is_corresponding, author_count


def infer_publication_type(item: PublicationItem) -> Optional[str]:
    value = clean_text(item.publication_type)
    if value:
        lower = value.lower()
        if "journal" in lower:
            return "journal"
        if "conference" in lower:
            return "conference"
        if "book" in lower:
            return "book_chapter"
        return lower

    venue = " ".join(
        part
        for part in [clean_text(item.published_in), clean_text(item.journal_name), clean_text(item.conference_name)]
        if part
    )
    if not venue:
        return None

    lower = venue.lower()
    if re.search(r"conference|conf\.|symposium|workshop|proceedings", lower):
        return "conference"
    return "journal"


def flatten_to_relational_rows(result: ExtractionResult) -> dict[str, list[dict]]:
    """Convert nested candidate object into relational table rows with normalization."""
    pi = result.data.personal_information

    candidate_rows = [
        {
            "candidate_id": result.candidate_id,
            "source_file": result.source_file,
            "full_name": clean_text(pi.full_name),
            "father_guardian_name": clean_text(pi.father_guardian_name),
            "spouse_name": clean_text(pi.spouse_name),
            "date_of_birth": clean_text(pi.date_of_birth),
            "nationality": clean_text(pi.nationality),
            "marital_status": clean_text(pi.marital_status),
            "current_salary": clean_text(pi.current_salary),
            "expected_salary": clean_text(pi.expected_salary),
            "present_employment": clean_text(pi.present_employment),
            "post_applied_for": clean_text(pi.post_applied_for),
        }
    ]

    education_rows: list[dict] = []
    for item in result.data.education:
        degree_title_raw = clean_text(item.degree_title)
        specialization = clean_text(item.specialization)
        inferred_title, inferred_level, inferred_stage = normalize_degree_title(
            degree_title_raw,
            specialization,
        )

        hint_level = normalize_level_hint(item.degree_level_hint)
        hint_stage = normalize_stage_hint(item.education_stage_hint)
        hint_title = clean_text(item.degree_title_normalized_hint)

        degree_title_normalized = first_non_null(hint_title, inferred_title)
        degree_level = first_non_null(hint_level, inferred_level)
        education_stage = first_non_null(hint_stage, level_to_stage(hint_level), inferred_stage)
        score = normalize_score(item.score_or_cgpa)

        institution = clean_text(item.institution_name)
        board = clean_text(item.board_name)

        education_rows.append(
            {
                "candidate_id": result.candidate_id,
                "education_stage": education_stage,
                "degree_title_raw": degree_title_raw,
                "degree_title_normalized": degree_title_normalized,
                "degree_level": degree_level,
                "specialization": specialization,
                "institution_name": institution,
                "board_or_university": first_non_null(board, institution),
                "admission_year": parse_year(item.admission_year),
                "completion_year": parse_year(item.completion_year),
                "passing_year": parse_year(item.passing_year),
                "score_raw": score["score_raw"],
                "score_type": score["score_type"],
                "score_value": score["score_value"],
                "score_scale": score["score_scale"],
                "score_normalized_percentage": score["score_normalized_percentage"],
                "score_normalization_basis": score["score_normalization_basis"],
                "qs_rank_reported": clean_text(item.qs_rank_reported),
                "the_rank_reported": clean_text(item.the_rank_reported),
            }
        )

    education_rows.sort(
        key=lambda row: (
            row["passing_year"] is None,
            row["passing_year"] if row["passing_year"] is not None else 9999,
            row["degree_level"] or "",
        )
    )

    experience_rows: list[dict] = []
    for item in result.data.experience:
        start_year, end_year = extract_year_bounds_from_duration(item.duration)
        experience_rows.append(
            {
                "candidate_id": result.candidate_id,
                "post_job_title": clean_text(item.post_job_title),
                "organization": clean_text(item.organization),
                "location": clean_text(item.location),
                "duration": clean_text(item.duration),
                "start_year": start_year,
                "end_year": end_year,
            }
        )

    publication_rows: list[dict] = []
    candidate_name = clean_text(pi.full_name)
    for item in result.data.publications:
        position, role, is_first, is_corresponding, author_count = infer_authorship_role(
            item.authors,
            candidate_name,
        )
        pub_type = infer_publication_type(item)
        publication_rows.append(
            {
                "candidate_id": result.candidate_id,
                "paper_title": clean_text(item.paper_title),
                "publication_type": pub_type,
                "authors": clean_text(item.authors),
                "author_count": author_count,
                "candidate_author_position": position,
                "candidate_authorship_role": role,
                "candidate_is_first_author": is_first,
                "candidate_is_corresponding_author": is_corresponding,
                "venue_name": first_non_null(item.published_in, item.journal_name, item.conference_name),
                "journal_name": clean_text(item.journal_name),
                "conference_name": clean_text(item.conference_name),
                "published_in": clean_text(item.published_in),
                "publisher": clean_text(item.publisher),
                "issn": clean_text(item.issn),
                "isbn": clean_text(item.isbn),
                "doi": clean_text(item.doi),
                "volume": clean_text(item.volume),
                "issue": clean_text(item.issue),
                "pages": clean_text(item.pages),
                "impact_factor_reported": clean_text(item.impact_factor_reported),
                "quartile_reported": clean_text(item.quartile_reported),
                "wos_indexed_reported": clean_text(item.wos_indexed_reported),
                "scopus_indexed_reported": clean_text(item.scopus_indexed_reported),
                "conference_rank_reported": clean_text(item.conference_rank_reported),
                "conference_series_edition": clean_text(item.conference_series_edition),
                "proceedings_indexed_in": clean_text(item.proceedings_indexed_in),
                "date_text": clean_text(item.date_text),
                "publication_year": parse_year(item.publication_year or item.date_text),
                "url": clean_text(item.url),
                "verification_notes": "reported_in_cv_unverified",
            }
        )

    book_rows: list[dict] = []
    for item in result.data.books:
        _, role, _, _, _ = infer_authorship_role(item.authors, candidate_name)
        book_rows.append(
            {
                "candidate_id": result.candidate_id,
                "book_title": clean_text(item.book_title),
                "authors": clean_text(item.authors),
                "candidate_authorship_role": role,
                "isbn": clean_text(item.isbn),
                "publisher": clean_text(item.publisher),
                "publication_year": parse_year(item.publication_year),
                "url": clean_text(item.url),
            }
        )

    patent_rows: list[dict] = []
    for item in result.data.patents:
        _, role, is_first, _, _ = infer_authorship_role(item.inventors, candidate_name)
        inventor_role = "lead_inventor" if is_first else role
        patent_rows.append(
            {
                "candidate_id": result.candidate_id,
                "patent_number": clean_text(item.patent_number),
                "patent_title": clean_text(item.patent_title),
                "inventors": clean_text(item.inventors),
                "candidate_inventor_role": inventor_role,
                "filing_country": clean_text(item.filing_country),
                "date_text": clean_text(item.date_text),
                "filing_year": parse_year(item.filing_year or item.date_text),
                "url": clean_text(item.url),
            }
        )

    return {
        "candidates": candidate_rows,
        "education": education_rows,
        "experience": experience_rows,
        "publications": publication_rows,
        "books": book_rows,
        "patents": patent_rows,
    }
