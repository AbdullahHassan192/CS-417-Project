"""
TALASH M3 - Jobs API Routes
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db, Job, JobAlignment, Candidate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = "full_time"
    description: str = ""
    required_skills: Optional[list] = None


class UpdateJobRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list] = None
    status: Optional[str] = None


@router.get("")
async def list_jobs(db: Session = Depends(get_db)):
    """List all jobs."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    result = []
    for j in jobs:
        alignment_count = db.query(JobAlignment).filter(JobAlignment.job_id == j.id).count()
        result.append({
            "id": j.id,
            "title": j.title,
            "department": j.department,
            "location": j.location,
            "employment_type": j.employment_type,
            "description": j.description,
            "required_skills": json.loads(j.required_skills) if j.required_skills else [],
            "status": j.status,
            "created_at": str(j.created_at) if j.created_at else None,
            "total_applicants": alignment_count,
        })
    return {"status": "success", "data": result}


@router.post("")
async def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    """Create a new job posting."""
    job = Job(
        id=f"job_{uuid.uuid4().hex[:12]}",
        title=request.title,
        department=request.department,
        location=request.location,
        employment_type=request.employment_type,
        description=request.description,
        required_skills=json.dumps(request.required_skills or []),
        status="active",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "status": "success",
        "data": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "status": job.status,
        },
    }


@router.get("/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job details with aligned candidates."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    alignments = (
        db.query(JobAlignment, Candidate)
        .join(Candidate, JobAlignment.candidate_id == Candidate.candidate_id)
        .filter(JobAlignment.job_id == job_id)
        .order_by(JobAlignment.alignment_score.desc())
        .all()
    )
    candidates = []
    for a, c in alignments:
        candidates.append({
            "candidate_id": c.candidate_id,
            "full_name": c.full_name,
            "email": c.email,
            "alignment_score": a.alignment_score,
            "rank_position": a.rank_position,
            "overall_score": c.overall_score,
        })
    return {
        "status": "success",
        "data": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "location": job.location,
            "employment_type": job.employment_type,
            "description": job.description,
            "required_skills": json.loads(job.required_skills) if job.required_skills else [],
            "status": job.status,
            "created_at": str(job.created_at) if job.created_at else None,
            "candidates": candidates,
        },
    }


@router.patch("/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest, db: Session = Depends(get_db)):
    """Update job details."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if request.title is not None:
        job.title = request.title
    if request.department is not None:
        job.department = request.department
    if request.location is not None:
        job.location = request.location
    if request.employment_type is not None:
        job.employment_type = request.employment_type
    if request.description is not None:
        job.description = request.description
    if request.required_skills is not None:
        job.required_skills = json.dumps(request.required_skills or [])
    if request.status is not None:
        job.status = request.status
    db.commit()
    return {"status": "success", "data": {"id": job.id, "title": job.title}}


@router.delete("/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job posting and its alignments."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.query(JobAlignment).filter(JobAlignment.job_id == job_id).delete(synchronize_session=False)
    db.delete(job)
    db.commit()
    return {"status": "success", "data": {"id": job_id}}


@router.post("/{job_id}/match")
async def smart_match(job_id: str, db: Session = Depends(get_db)):
    """Run skill alignment for all candidates against this job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = db.query(Candidate).all()
    if not candidates:
        return {"status": "success", "data": {"candidates": [], "total": 0}}

    # Simple keyword-based matching (LLM matching deferred to background task)
    desc_lower = (job.description or "").lower()
    skills = json.loads(job.required_skills) if job.required_skills else []
    skills_lower = [s.lower() for s in skills]

    results = []
    for c in candidates:
        # Score based on overall_score + name/skill keyword overlap
        base_score = (c.overall_score or 0) * 0.7
        skill_bonus = 0
        candidate_text = f"{c.full_name or ''} {c.present_employment or ''} {c.post_applied_for or ''}".lower()
        for sk in skills_lower:
            if sk in candidate_text:
                skill_bonus += 5
        score = min(100, base_score + skill_bonus + 15)  # baseline alignment

        # Upsert alignment
        existing = db.query(JobAlignment).filter(
            JobAlignment.candidate_id == c.candidate_id,
            JobAlignment.job_id == job_id,
        ).first()
        if existing:
            existing.alignment_score = round(score, 1)
        else:
            db.add(JobAlignment(
                candidate_id=c.candidate_id,
                job_id=job_id,
                alignment_score=round(score, 1),
            ))
        results.append({
            "candidate_id": c.candidate_id,
            "full_name": c.full_name,
            "alignment_score": round(score, 1),
            "overall_score": c.overall_score,
        })

    db.commit()

    # Rank
    results.sort(key=lambda x: x["alignment_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return {"status": "success", "data": {"candidates": results, "total": len(results)}}
