"""
TALASH M2 - Missing Information Detection & Email Drafting

Identifies incomplete/missing data in CV and generates
personalized email requests for additional information.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Field definitions with severity ─────────────────────────────────────────
CRITICAL_FIELDS = {
    "personal": ["full_name", "date_of_birth"],
    "education": ["degree_title_raw", "institution_name"],
    "experience": ["post_job_title", "organization"],
}

IMPORTANT_FIELDS = {
    "personal": ["nationality"],
    "education": [
        "passing_year", "score_raw", "specialization",
        "admission_year", "completion_year",
    ],
    "experience": ["start_year", "end_year", "duration"],
}

USEFUL_FIELDS = {
    "personal": [
        "father_guardian_name", "marital_status",
        "current_salary", "expected_salary",
    ],
    "education": ["board_or_university", "score_type"],
    "experience": ["location"],
}


# ── 3.1  detect_missing_information ─────────────────────────────────────────
def detect_missing_information(
    candidate_data: Dict[str, pd.DataFrame],
    educational_assessment: Optional[Dict[str, Any]] = None,
    employment_assessment: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Identify missing/incomplete fields across all CV sections.

    Input:
      - candidate_data: dict of DataFrames (candidates, education, experience, etc.)
      - educational_assessment: output from educational analysis (optional)
      - employment_assessment: output from employment analysis (optional)

    Returns: list of MissingInfoField dicts
    """
    missing_fields: List[Dict[str, Any]] = []

    # ── Personal information checks ──
    cand_df = candidate_data.get("candidates", pd.DataFrame())
    if not cand_df.empty:
        row = cand_df.iloc[0]
        for severity_level, field_map in [
            ("critical", CRITICAL_FIELDS),
            ("important", IMPORTANT_FIELDS),
            ("useful", USEFUL_FIELDS),
        ]:
            for field in field_map.get("personal", []):
                val = row.get(field)
                if _is_missing(val):
                    missing_fields.append({
                        "section": "personal",
                        "field_name": field,
                        "severity": severity_level,
                        "current_value": None,
                        "missing_detail": f"Missing {_humanize_field(field)}",
                        "impact": _field_impact("personal", field),
                    })
    else:
        missing_fields.append({
            "section": "personal",
            "field_name": "all",
            "severity": "critical",
            "current_value": None,
            "missing_detail": "No personal information found",
            "impact": "Cannot identify candidate without personal information",
        })

    # ── Education checks ──
    edu_df = candidate_data.get("education", pd.DataFrame())
    if edu_df.empty:
        missing_fields.append({
            "section": "education",
            "field_name": "all",
            "severity": "critical",
            "current_value": None,
            "missing_detail": "No education records found",
            "impact": "Cannot assess academic qualifications",
        })
    else:
        for idx, (_, row) in enumerate(edu_df.iterrows()):
            degree = row.get("degree_title_raw", "Unknown degree")
            for severity_level, field_map in [
                ("critical", CRITICAL_FIELDS),
                ("important", IMPORTANT_FIELDS),
                ("useful", USEFUL_FIELDS),
            ]:
                for field in field_map.get("education", []):
                    val = row.get(field)
                    if _is_missing(val):
                        missing_fields.append({
                            "section": "education",
                            "field_name": field,
                            "severity": severity_level,
                            "current_value": None,
                            "missing_detail": (
                                f"Missing {_humanize_field(field)} "
                                f"for {degree}"
                            ),
                            "impact": _field_impact("education", field),
                        })

    # ── Experience checks ──
    exp_df = candidate_data.get("experience", pd.DataFrame())
    if exp_df.empty:
        missing_fields.append({
            "section": "experience",
            "field_name": "all",
            "severity": "important",
            "current_value": None,
            "missing_detail": "No experience records found",
            "impact": "Cannot assess professional background",
        })
    else:
        for _, row in exp_df.iterrows():
            title_val = row.get("post_job_title")
            title = "Unknown role" if _is_missing(title_val) else title_val
            for severity_level, field_map in [
                ("critical", CRITICAL_FIELDS),
                ("important", IMPORTANT_FIELDS),
                ("useful", USEFUL_FIELDS),
            ]:
                for field in field_map.get("experience", []):
                    val = row.get(field)
                    if _is_missing(val):
                        missing_fields.append({
                            "section": "experience",
                            "field_name": field,
                            "severity": severity_level,
                            "current_value": None,
                            "missing_detail": (
                                f"Missing {_humanize_field(field)} "
                                f"for role: {title}"
                            ),
                            "impact": _field_impact("experience", field),
                        })

    # ── Check for unexplained gaps from assessments ──
    if employment_assessment:
        unexplained = [
            g for g in employment_assessment.get("justified_gaps", [])
            if g.get("justification_type") == "unexplained"
        ]
        for gap in unexplained:
            missing_fields.append({
                "section": "experience",
                "field_name": "gap_explanation",
                "severity": "important",
                "current_value": gap.get("gap_period"),
                "missing_detail": (
                    f"Unexplained employment gap: {gap.get('gap_period')} "
                    f"({gap.get('duration_months', 0)} months)"
                ),
                "impact": "Employment gaps without explanation may affect assessment",
            })

    return missing_fields


# ── 3.2  generate_missing_info_summary ──────────────────────────────────────
def generate_missing_info_summary(
    missing_fields: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Organize missing fields by severity and section.

    Returns: MissingInfoSummary with organized field list and statistics.
    """
    if not missing_fields:
        return {
            "total_missing_fields": 0,
            "critical_count": 0,
            "important_count": 0,
            "useful_count": 0,
            "completeness_percentage": 100.0,
            "fields_by_severity": {"critical": [], "important": [], "useful": []},
            "fields_by_section": {},
        }

    # Count by severity
    critical = [f for f in missing_fields if f["severity"] == "critical"]
    important = [f for f in missing_fields if f["severity"] == "important"]
    useful = [f for f in missing_fields if f["severity"] == "useful"]

    # Group by section
    by_section: Dict[str, List] = {}
    for f in missing_fields:
        section = f["section"]
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(f)

    # Calculate completeness (deductions per severity)
    deductions = len(critical) * 20 + len(important) * 10 + len(useful) * 5
    completeness = max(0.0, 100.0 - deductions)

    return {
        "total_missing_fields": len(missing_fields),
        "critical_count": len(critical),
        "important_count": len(important),
        "useful_count": len(useful),
        "completeness_percentage": round(completeness, 1),
        "fields_by_severity": {
            "critical": critical,
            "important": important,
            "useful": useful,
        },
        "fields_by_section": by_section,
    }


# ── 3.3  draft_missing_info_email ──────────────────────────────────────────
def draft_missing_info_email(
    candidate_name: Optional[str],
    candidate_email: Optional[str],
    missing_summary: Dict[str, Any],
    source_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a professional, personalized email requesting missing information.

    Returns: PersonalizedEmail dict with subject, body, recipient, etc.
    """
    name = candidate_name or "Candidate"
    email = candidate_email or "N/A"

    critical_fields = missing_summary.get("fields_by_severity", {}).get("critical", [])
    important_fields = missing_summary.get("fields_by_severity", {}).get("important", [])

    # Build email body
    lines = []
    lines.append(f"Dear {name},")
    lines.append("")
    lines.append(
        "Thank you for submitting your CV for consideration. "
        "We appreciate your interest and the time you have taken to apply."
    )
    lines.append("")
    lines.append(
        "Upon reviewing your application, we noticed that some information "
        "is missing or incomplete. To ensure a thorough and fair assessment "
        "of your profile, we kindly request you to provide the following details:"
    )
    lines.append("")

    if critical_fields:
        lines.append("**Critical Information Required:**")
        for f in critical_fields:
            lines.append(f"  - {f['missing_detail']}")
        lines.append("")

    if important_fields:
        lines.append("**Additional Information Needed:**")
        for f in important_fields:
            lines.append(f"  - {f['missing_detail']}")
        lines.append("")

    lines.append(
        "Please provide the updated information within 7 working days "
        "by replying to this email. If you have any questions or need "
        "clarification, please do not hesitate to reach out."
    )
    lines.append("")
    lines.append(
        "If any of the requested information is not applicable, "
        "kindly mention that in your response so we can update your profile accordingly."
    )
    lines.append("")
    lines.append("Best regards,")
    lines.append("HR Recruitment Team")
    lines.append("TALASH - Smart HR Recruitment System")

    body = "\n".join(lines)

    subject = f"Additional Information Required - Application Review ({name})"

    return {
        "subject": subject,
        "body": body,
        "recipient": email,
        "candidate_name": name,
        "date_drafted": datetime.now().isoformat(),
        "missing_items_count": missing_summary.get("total_missing_fields", 0),
        "tone": "professional",
        "source_file": source_file,
    }


# ── 3.4  generate_batch_missing_info_emails ─────────────────────────────────
def generate_batch_missing_info_emails(
    candidates_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate missing info emails for multiple candidates.

    Input: list of dicts, each with:
      - candidate_name, candidate_email, missing_summary, source_file

    Returns: dict with emails list and batch summary
    """
    emails: List[Dict[str, Any]] = []
    candidates_with_missing = 0

    for cand in candidates_data:
        summary = cand.get("missing_summary", {})
        if summary.get("total_missing_fields", 0) > 0:
            candidates_with_missing += 1
            email = draft_missing_info_email(
                candidate_name=cand.get("candidate_name"),
                candidate_email=cand.get("candidate_email"),
                missing_summary=summary,
                source_file=cand.get("source_file"),
            )
            emails.append(email)

    # Severity breakdown across all candidates
    total_critical = sum(
        c.get("missing_summary", {}).get("critical_count", 0)
        for c in candidates_data
    )
    total_important = sum(
        c.get("missing_summary", {}).get("important_count", 0)
        for c in candidates_data
    )

    return {
        "emails": emails,
        "batch_summary": {
            "total_candidates": len(candidates_data),
            "candidates_with_missing_info": candidates_with_missing,
            "total_emails_drafted": len(emails),
            "total_critical_fields": total_critical,
            "total_important_fields": total_important,
            "generated_at": datetime.now().isoformat(),
        },
    }


# ── Helper functions ────────────────────────────────────────────────────────

def _is_missing(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and val.strip().lower() in (
        "", "n/a", "na", "none", "null", "-", "--",
    ):
        return True
    return False


def _humanize_field(field_name: str) -> str:
    return field_name.replace("_", " ").title()


def _field_impact(section: str, field: str) -> str:
    impacts = {
        ("personal", "full_name"): "Required for candidate identification",
        ("personal", "date_of_birth"): "Needed for age verification and eligibility",
        ("personal", "nationality"): "Required for visa/eligibility considerations",
        ("education", "degree_title_raw"): "Required for qualification assessment",
        ("education", "institution_name"): "Required for institutional quality analysis",
        ("education", "passing_year"): "Needed for timeline and progression analysis",
        ("education", "score_raw"): "Required for academic performance evaluation",
        ("education", "specialization"): "Important for field-specific matching",
        ("education", "admission_year"): "Needed for gap detection analysis",
        ("education", "completion_year"): "Needed for education timeline analysis",
        ("experience", "post_job_title"): "Required for career progression assessment",
        ("experience", "organization"): "Required for employment verification",
        ("experience", "start_year"): "Needed for timeline consistency analysis",
        ("experience", "end_year"): "Needed for gap detection and duration calculation",
        ("experience", "duration"): "Needed for experience calculation",
        ("experience", "location"): "Useful for geographic analysis",
    }
    return impacts.get(
        (section, field),
        f"Improves completeness of {section} profile",
    )
