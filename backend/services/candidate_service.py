"""
TALASH M3 - Candidate Service

Provides DB-backed candidate listing and assessment loading.
Replaces M2's file-system based approach.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, aliased
from sqlalchemy import asc, desc, or_, func, and_

from backend.database import (
    Candidate, Education, Experience, Publication,
    Book, Patent, CandidateAnalysis, MissingInfoLog, PipelineStatus,
)

logger = logging.getLogger(__name__)


def get_candidate_list_db(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    search: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List candidates from the database with pagination, sorting, and filtering.
    """
    latest_status_subq = (
        db.query(
            PipelineStatus.candidate_id.label("candidate_id"),
            func.max(PipelineStatus.updated_at).label("max_updated"),
        )
        .filter(PipelineStatus.job_id.is_(None))
        .group_by(PipelineStatus.candidate_id)
        .subquery()
    )
    latest_status = aliased(PipelineStatus)

    query = (
        db.query(Candidate, latest_status.status.label("pipeline_status"))
        .outerjoin(latest_status_subq, latest_status_subq.c.candidate_id == Candidate.candidate_id)
        .outerjoin(
            latest_status,
            and_(
                latest_status.candidate_id == latest_status_subq.c.candidate_id,
                latest_status.updated_at == latest_status_subq.c.max_updated,
            ),
        )
    )

    # Search filter
    if search:
        query = query.filter(
            or_(
                Candidate.full_name.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%"),
                Candidate.post_applied_for.ilike(f"%{search}%"),
            )
        )

    # Score filters
    if min_score is not None:
        query = query.filter(Candidate.overall_score >= min_score)
    if max_score is not None:
        query = query.filter(Candidate.overall_score <= max_score)

    if status:
        if status == "unreviewed":
            query = query.filter(latest_status.status.is_(None))
        else:
            query = query.filter(latest_status.status == status)

    # Total count
    total = query.count()

    # Sorting
    sort_column = getattr(Candidate, sort_by, Candidate.overall_score)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Pagination
    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()

    # Build response
    result = []
    for c, pipeline_status in candidates:
        # Get supplementary data
        pub_count = db.query(Publication).filter(
            Publication.candidate_id == c.candidate_id
        ).count()

        missing_log = db.query(MissingInfoLog).filter(
            MissingInfoLog.candidate_id == c.candidate_id
        ).first()
        missing_count = 0
        completeness = 100.0
        if missing_log and missing_log.missing_fields:
            try:
                fields = json.loads(missing_log.missing_fields)
                missing_count = len(fields) if isinstance(fields, list) else 0
            except json.JSONDecodeError:
                pass

        # Get assessment data for additional scores
        analysis = db.query(CandidateAnalysis).filter(
            CandidateAnalysis.candidate_id == c.candidate_id,
            CandidateAnalysis.analysis_type == "full_assessment",
        ).first()

        edu_strength = 0
        prof_strength = 0
        total_experience_years = 0
        overall_tier = "below_average"

        if analysis and analysis.analysis_json:
            try:
                data = json.loads(analysis.analysis_json)
                edu = data.get("educational_assessment", {})
                emp = data.get("employment_assessment", {})
                edu_strength = edu.get("overall_educational_strength", 0)
                prof_strength = emp.get("overall_professional_strength", 0)
                total_experience_years = emp.get("total_years_of_experience", 0)
                overall_tier = data.get("overall_tier", "below_average")
                completeness = data.get("missing_info", {}).get("completeness_percentage", 100)
            except json.JSONDecodeError:
                pass

        result.append({
            "candidate_id": c.candidate_id,
            "full_name": c.full_name,
            "email": c.email,
            "source_file": c.source_file,
            "post_applied_for": c.post_applied_for,
            "overall_score": c.overall_score or 0,
            "overall_tier": overall_tier,
            "educational_strength": edu_strength,
            "professional_strength": prof_strength,
            "total_years_of_experience": total_experience_years,
            "publication_count": pub_count,
            "missing_info_count": missing_count,
            "completeness_percentage": completeness,
            "pipeline_status": pipeline_status or "unreviewed",
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "candidates": result,
    }


def load_assessment_db(db: Session, candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Load full assessment for a candidate from the database.
    Falls back to file-system if not in DB yet.
    """
    # Try DB first
    analysis = db.query(CandidateAnalysis).filter(
        CandidateAnalysis.candidate_id == candidate_id,
        CandidateAnalysis.analysis_type == "full_assessment",
    ).first()

    if analysis and analysis.analysis_json:
        try:
            return json.loads(analysis.analysis_json)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in DB for candidate {candidate_id}")

    # Fallback to file-system (legacy M2)
    from backend.services.candidate_service_legacy import load_assessment
    return load_assessment(candidate_id)


# ── Legacy compatibility aliases ──
def get_candidate_list(**kwargs):
    """Legacy wrapper — uses file-based approach."""
    from backend.services.candidate_service_legacy import get_candidate_list as _legacy
    return _legacy(**kwargs)
