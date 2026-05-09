"""
TALASH M3 - Dashboard & Analytics API Routes
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import (
    get_db, Candidate, Education, Experience, Publication,
    Book, Patent, CandidateAnalysis, Job, PipelineStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["dashboard", "analytics"])


def _compute_unique_experience_years(experiences) -> float:
    current_year = datetime.now().year
    intervals = []
    for exp in experiences:
        start = exp.start_year
        end = exp.end_year or current_year
        if start is None:
            continue
        if end < start:
            start, end = end, start
        intervals.append((start, end))

    if not intervals:
        return 0.0

    intervals.sort(key=lambda x: x[0])
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return float(round(sum(max(0, e - s) for s, e in merged), 1))


def _assessment_fallbacks(analysis_json: str):
    """Extract fallback fields from assessment JSON."""
    try:
        data = json.loads(analysis_json)
    except (json.JSONDecodeError, TypeError):
        return {
            "highest_degree": None,
            "institution": None,
            "total_experience_years": None,
            "publication_count": None,
            "book_count": None,
            "patent_count": None,
        }

    edu = data.get("educational_assessment", {})
    emp = data.get("employment_assessment", {})
    res = data.get("research_assessment", {})

    highest_degree = edu.get("highest_qualification_level")
    institution = None
    records = edu.get("higher_education_records", []) or []
    if records:
        def _year(rec):
            return rec.get("completion_year") or rec.get("passing_year") or 0
        top = max(records, key=_year)
        institution = top.get("institution_name") or top.get("board_or_university")

    return {
        "highest_degree": highest_degree,
        "institution": institution,
        "total_experience_years": emp.get("total_years_of_experience"),
        "publication_count": res.get("total_publications"),
        "book_count": res.get("total_books"),
        "patent_count": res.get("total_patents"),
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """KPI stats for the dashboard."""
    total = db.query(Candidate).count()
    avg_score = db.query(func.avg(Candidate.overall_score)).scalar() or 0
    shortlisted = db.query(Candidate).filter(Candidate.overall_score >= 70).count()
    ratio = f"1:{max(1, round(total / max(shortlisted, 1)))}" if total else "—"
    total_pubs = db.query(Publication).count()
    total_jobs = db.query(Job).filter(Job.status == "active").count()

    return {
        "status": "success",
        "data": {
            "candidate_score_avg": round(avg_score, 1),
            "shortlist_ratio": ratio,
            "shortlist_count": shortlisted,
            "active_pipeline": total,
            "time_to_hire": 12,  # placeholder
            "total_publications": total_pubs,
            "active_jobs": total_jobs,
        },
    }


@router.get("/dashboard/charts")
async def get_dashboard_charts(db: Session = Depends(get_db)):
    """Chart data for the dashboard."""
    # Publication type breakdown
    pubs = db.query(Publication.publication_type, func.count(Publication.id)).group_by(
        Publication.publication_type
    ).all()
    pub_breakdown = {(t or "unknown"): c for t, c in pubs}

    # Education level distribution
    edu = db.query(Education.degree_level, func.count(Education.id)).group_by(
        Education.degree_level
    ).all()
    edu_breakdown = {(l or "other"): c for l, c in edu}

    # Score distribution (buckets)
    candidates = db.query(Candidate.overall_score).all()
    score_buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for (s,) in candidates:
        score = s or 0
        if score < 20: score_buckets["0-20"] += 1
        elif score < 40: score_buckets["20-40"] += 1
        elif score < 60: score_buckets["40-60"] += 1
        elif score < 80: score_buckets["60-80"] += 1
        else: score_buckets["80-100"] += 1

    return {
        "status": "success",
        "data": {
            "publication_breakdown": pub_breakdown,
            "education_levels": edu_breakdown,
            "score_distribution": score_buckets,
        },
    }


@router.get("/analytics/candidates")
async def get_analytics_candidates(db: Session = Depends(get_db)):
    """Candidate comparison data for analytics page."""
    candidates = db.query(Candidate).order_by(Candidate.overall_score.desc()).all()
    result = []
    for c in candidates:
        edu_count = db.query(Education).filter(Education.candidate_id == c.candidate_id).count()
        exp_count = db.query(Experience).filter(Experience.candidate_id == c.candidate_id).count()
        pub_count = db.query(Publication).filter(Publication.candidate_id == c.candidate_id).count()
        book_count = db.query(Book).filter(Book.candidate_id == c.candidate_id).count()
        patent_count = db.query(Patent).filter(Patent.candidate_id == c.candidate_id).count()

        analysis = db.query(CandidateAnalysis).filter(
            CandidateAnalysis.candidate_id == c.candidate_id,
            CandidateAnalysis.analysis_type == "full_assessment",
        ).first()
        fallback = _assessment_fallbacks(analysis.analysis_json if analysis else None)

        # Get highest degree
        highest_edu = db.query(Education).filter(
            Education.candidate_id == c.candidate_id
        ).order_by(Education.completion_year.desc()).first()

        # Get total experience years
        exps = db.query(Experience).filter(Experience.candidate_id == c.candidate_id).all()
        total_years = _compute_unique_experience_years(exps)
        if not exps and fallback.get("total_experience_years") is not None:
            total_years = float(fallback.get("total_experience_years") or 0)

        final_pub_count = pub_count or int(fallback.get("publication_count") or 0)
        final_book_count = book_count or int(fallback.get("book_count") or 0)
        final_patent_count = patent_count or int(fallback.get("patent_count") or 0)
        final_degree = highest_edu.degree_level if highest_edu else (fallback.get("highest_degree") or "N/A")
        final_institution = highest_edu.institution_name if highest_edu else (fallback.get("institution") or "N/A")

        result.append({
            "candidate_id": c.candidate_id,
            "full_name": c.full_name,
            "email": c.email,
            "overall_score": c.overall_score or 0,
            "rank_position": c.rank_position,
            "highest_degree": final_degree,
            "institution": final_institution,
            "total_experience_years": total_years,
            "publication_count": final_pub_count,
            "book_count": final_book_count,
            "patent_count": final_patent_count,
            "post_applied_for": c.post_applied_for,
        })
    return {"status": "success", "data": result}


@router.get("/analytics/education")
async def get_education_analytics(db: Session = Depends(get_db)):
    """Education-level analytics."""
    levels = db.query(
        Education.degree_level, func.count(Education.id)
    ).group_by(Education.degree_level).all()

    institutions = db.query(
        Education.institution_name, func.count(Education.id)
    ).group_by(Education.institution_name).order_by(
        func.count(Education.id).desc()
    ).limit(10).all()

    return {
        "status": "success",
        "data": {
            "degree_distribution": {(l or "other"): c for l, c in levels},
            "top_institutions": [
                {"name": n, "count": c} for n, c in institutions if n
            ],
        },
    }


@router.get("/analytics/publications")
async def get_publication_analytics(db: Session = Depends(get_db)):
    """Publication analytics."""
    by_type = db.query(
        Publication.publication_type, func.count(Publication.id)
    ).group_by(Publication.publication_type).all()

    by_year = db.query(
        Publication.publication_year, func.count(Publication.id)
    ).filter(Publication.publication_year.isnot(None)).group_by(
        Publication.publication_year
    ).order_by(Publication.publication_year).all()

    # Per-candidate counts
    per_candidate = db.query(
        Candidate.full_name, func.count(Publication.id)
    ).join(Publication, Candidate.candidate_id == Publication.candidate_id).group_by(
        Candidate.full_name
    ).order_by(func.count(Publication.id).desc()).limit(10).all()

    return {
        "status": "success",
        "data": {
            "by_type": {(t or "unknown"): c for t, c in by_type},
            "by_year": [{"year": y, "count": c} for y, c in by_year if y],
            "per_candidate": [{"name": n, "count": c} for n, c in per_candidate if n],
        },
    }


@router.get("/analytics/gaps")
async def get_gap_analytics(db: Session = Depends(get_db)):
    """Employment gap heatmap data."""
    candidates = db.query(Candidate).all()
    gap_data = []
    for c in candidates:
        analysis = db.query(CandidateAnalysis).filter(
            CandidateAnalysis.candidate_id == c.candidate_id,
            CandidateAnalysis.analysis_type == "full_assessment",
        ).first()
        if analysis and analysis.analysis_json:
            try:
                data = json.loads(analysis.analysis_json)
                emp = data.get("employment_assessment", {})
                gaps = emp.get("justified_gaps", [])
                for g in gaps:
                    gap_data.append({
                        "candidate_id": c.candidate_id,
                        "candidate_name": c.full_name,
                        "gap_period": g.get("gap_period", ""),
                        "duration_months": g.get("duration_months", 0),
                        "justified": g.get("justification_type", "unexplained") != "unexplained",
                        "justification": g.get("justification_detail", ""),
                    })
            except (json.JSONDecodeError, TypeError):
                pass
    return {"status": "success", "data": gap_data}


@router.get("/rankings")
async def get_rankings(db: Session = Depends(get_db)):
    """Global candidate rankings."""
    candidates = db.query(Candidate).filter(
        Candidate.overall_score.isnot(None)
    ).order_by(Candidate.overall_score.desc()).all()

    result = []
    for i, c in enumerate(candidates, 1):
        pub_count = db.query(Publication).filter(
            Publication.candidate_id == c.candidate_id
        ).count()

        analysis = db.query(CandidateAnalysis).filter(
            CandidateAnalysis.candidate_id == c.candidate_id,
            CandidateAnalysis.analysis_type == "full_assessment",
        ).first()
        fallback = _assessment_fallbacks(analysis.analysis_json if analysis else None)

        # Get highest degree
        highest_edu = db.query(Education).filter(
            Education.candidate_id == c.candidate_id
        ).order_by(Education.completion_year.desc()).first()

        exps = db.query(Experience).filter(Experience.candidate_id == c.candidate_id).all()
        total_years = _compute_unique_experience_years(exps)
        if not exps and fallback.get("total_experience_years") is not None:
            total_years = float(fallback.get("total_experience_years") or 0)

        final_pub_count = pub_count or int(fallback.get("publication_count") or 0)
        final_degree = highest_edu.degree_level if highest_edu else (fallback.get("highest_degree") or "N/A")

        result.append({
            "rank": i,
            "candidate_id": c.candidate_id,
            "full_name": c.full_name,
            "overall_score": round(c.overall_score or 0, 1),
            "highest_degree": final_degree,
            "experience_years": total_years,
            "publication_count": final_pub_count,
            "post_applied_for": c.post_applied_for,
        })
    return {"status": "success", "data": result}


@router.get("/missing-info")
async def get_all_missing_info(db: Session = Depends(get_db)):
    """All candidates with missing data."""
    from backend.database import MissingInfoLog
    logs = db.query(MissingInfoLog, Candidate).join(
        Candidate, MissingInfoLog.candidate_id == Candidate.candidate_id
    ).all()
    result = []
    for log, cand in logs:
        result.append({
            "candidate_id": cand.candidate_id,
            "candidate_name": cand.full_name,
            "missing_fields": json.loads(log.missing_fields) if log.missing_fields else [],
            "draft_email": json.loads(log.draft_email) if log.draft_email else None,
            "email_sent": log.email_sent,
        })
    return {"status": "success", "data": result}
