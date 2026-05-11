"""
TALASH M3 - Candidates API Routes

REST endpoints for candidate management with database integration.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.database import (
    get_db, Candidate, Education, Experience, Publication,
    Book, Patent, CandidateAnalysis, MissingInfoLog, JobAlignment, PipelineStatus,
)
from backend.schemas import (
    APIResponse,
    ProcessFolderRequest,
    SendInfoRequestBody,
    BatchProcessRequest,
    CandidateStatusUpdate,
)
from backend.services.candidate_service import (
    get_candidate_list_db,
    load_assessment_db,
)
from backend.services.assessment_service import (
    run_preprocessing,
    run_analysis_pipeline,
    generate_batch_emails,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/candidates", tags=["candidates"])


# ── 1. POST /api/candidates/process-folder ──────────────────────────────────
@router.post("/process-folder", response_model=APIResponse)
async def process_folder(request: ProcessFolderRequest, db: Session = Depends(get_db)):
    """Trigger M1 preprocessing and M2/M3 analysis on a folder of CVs."""
    result = run_preprocessing(request.folder_path)

    # Also run analysis after preprocessing
    if result["status"] == "completed":
        analysis_result = run_analysis_pipeline(db=db)
        result["analysis_status"] = analysis_result["status"]
        result["analysis_message"] = analysis_result["message"]

    return APIResponse(
        status=result["status"],
        data=result,
        error=result.get("message") if result["status"] == "error" else None,
    )


# ── 2. GET /api/candidates/list ─────────────────────────────────────────────
@router.get("/list", response_model=APIResponse)
async def list_candidates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query("overall_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    search: Optional[str] = Query(None, description="Search by name"),
    min_score: Optional[float] = Query(None, description="Minimum score filter"),
    max_score: Optional[float] = Query(None, description="Maximum score filter"),
    status: Optional[str] = Query(None, description="Pipeline status filter"),
    db: Session = Depends(get_db),
):
    """List all processed candidates with pagination and filtering."""
    result = get_candidate_list_db(
        db=db,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        min_score=min_score,
        max_score=max_score,
        status=status,
    )
    return APIResponse(status="success", data=result)


# ── 3. GET /api/candidates/{candidate_id}/full-assessment ───────────────────
@router.get("/{candidate_id}/full-assessment", response_model=APIResponse)
async def get_full_assessment(candidate_id: str, db: Session = Depends(get_db)):
    """Get complete candidate assessment with all sub-scores."""
    assessment = load_assessment_db(db, candidate_id)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment not found for candidate: {candidate_id}",
        )
    latest_status = db.query(PipelineStatus).filter(
        PipelineStatus.candidate_id == candidate_id,
        PipelineStatus.job_id.is_(None),
    ).order_by(PipelineStatus.updated_at.desc()).first()
    assessment["pipeline_status"] = latest_status.status if latest_status else "unreviewed"
    return APIResponse(status="success", data=assessment)


# ── 4. GET /api/candidates/{candidate_id}/missing-info ──────────────────────
@router.get("/{candidate_id}/missing-info", response_model=APIResponse)
async def get_missing_info(candidate_id: str, db: Session = Depends(get_db)):
    """Get missing information details and email draft."""
    assessment = load_assessment_db(db, candidate_id)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment not found for candidate: {candidate_id}",
        )

    missing = assessment.get("missing_info", {})
    email = assessment.get("missing_info_email")

    result = {
        "total_missing_fields": missing.get("total_missing_fields", 0),
        "critical_count": missing.get("critical_count", 0),
        "completeness_percentage": missing.get("completeness_percentage", 100),
        "fields": missing.get("fields", []),
        "email_draft": email,
    }

    return APIResponse(status="success", data=result)


# ── 5. POST /api/candidates/{candidate_id}/send-info-request ────────────────
@router.post("/{candidate_id}/send-info-request", response_model=APIResponse)
async def send_info_request(
    candidate_id: str, body: SendInfoRequestBody, db: Session = Depends(get_db)
):
    """Send/save missing information request email."""
    assessment = load_assessment_db(db, candidate_id)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment not found for candidate: {candidate_id}",
        )

    email_data = assessment.get("missing_info_email", {})
    if not email_data:
        return APIResponse(
            status="no_action",
            data={"message": "No missing information email to send."},
        )

    # Mark as sent in DB
    log = db.query(MissingInfoLog).filter(
        MissingInfoLog.candidate_id == candidate_id
    ).first()
    if log:
        log.email_sent = True
        db.commit()

    return APIResponse(
        status="success",
        data={
            "status": "draft_saved",
            "email_id": f"email_{candidate_id}",
            "subject": body.email_subject or email_data.get("subject", ""),
            "recipient": body.recipient or email_data.get("recipient", ""),
            "message": "Email draft saved and marked as sent.",
        },
    )


# ── 6. POST /api/candidates/batch-process ───────────────────────────────────
@router.post("/batch-process", response_model=APIResponse)
async def batch_process(request: BatchProcessRequest, db: Session = Depends(get_db)):
    """Run missing info email generation for a batch of candidates."""
    if not request.candidate_ids:
        # If no specific IDs provided, process all
        all_candidates = db.query(Candidate).all()
        candidate_ids = [c.candidate_id for c in all_candidates]
    else:
        candidate_ids = request.candidate_ids

    result = generate_batch_emails(candidate_ids)
    return APIResponse(status="success", data=result)


# ── 7. GET /api/candidates/{candidate_id}/summary ──────────────────────────
@router.get("/{candidate_id}/summary", response_model=APIResponse)
async def get_candidate_summary(candidate_id: str, db: Session = Depends(get_db)):
    """Get human-readable candidate summary report."""
    assessment = load_assessment_db(db, candidate_id)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment not found for candidate: {candidate_id}",
        )

    pi = assessment.get("personal_info", {})
    summary = {
        "candidate_id": candidate_id,
        "candidate_name": pi.get("full_name", "Unknown"),
        "overall_score": assessment.get("overall_score", 0),
        "overall_tier": assessment.get("overall_tier", "below_average"),
        "quick_profile": assessment.get("summary_report", ""),
        "strengths": assessment.get("strengths", []),
        "concerns": assessment.get("concerns", []),
        "recommendation": assessment.get("recommendation", ""),
        "educational_narrative": assessment.get("educational_narrative", ""),
        "employment_narrative": assessment.get("employment_narrative", ""),
        "score_breakdown": assessment.get("score_breakdown", {}),
    }

    return APIResponse(status="success", data=summary)


# ── 8. POST /api/candidates/upload-cv (M3 new) ─────────────────────────────
@router.post("/upload-cv", response_model=APIResponse)
async def upload_cv(files: list[UploadFile] = File(...)):
    """Upload CV files for processing."""
    import shutil
    from pathlib import Path
    from backend.config import settings

    upload_dir = settings.INPUT_CVS_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for f in files:
        incoming = Path(f.filename)
        if incoming.is_absolute() or ".." in incoming.parts:
            incoming = Path(incoming.name)
        dest = upload_dir / incoming
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as buf:
            shutil.copyfileobj(f.file, buf)
        saved.append(str(incoming))

    return APIResponse(
        status="success",
        data={
            "files_saved": saved,
            "count": len(saved),
            "upload_dir": str(upload_dir),
            "message": f"{len(saved)} CV(s) uploaded. Use process-folder to analyze them.",
        },
    )


# ── 9. POST /api/candidates/{candidate_id}/status ─────────────────────────
@router.post("/{candidate_id}/status", response_model=APIResponse)
async def update_candidate_status(
    candidate_id: str, body: CandidateStatusUpdate, db: Session = Depends(get_db)
):
    """Update a candidate's pipeline status (shortlisted/rejected/unreviewed)."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")

    status_value = (body.status or "").strip().lower()
    allowed = {"shortlisted", "rejected", "unreviewed"}
    if status_value not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status value")

    if status_value == "unreviewed":
        db.query(PipelineStatus).filter(
            PipelineStatus.candidate_id == candidate_id,
            PipelineStatus.job_id.is_(None),
        ).delete(synchronize_session=False)
        db.commit()
        return APIResponse(status="success", data={"candidate_id": candidate_id, "status": "unreviewed"})

    db.add(PipelineStatus(candidate_id=candidate_id, status=status_value))
    db.commit()
    return APIResponse(status="success", data={"candidate_id": candidate_id, "status": status_value})


# ── 10. DELETE /api/candidates/{candidate_id} ───────────────────────────────
@router.delete("/{candidate_id}", response_model=APIResponse)
async def delete_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """Delete a candidate and all related records from the database."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate not found: {candidate_id}",
        )

    # JobAlignment is not configured with Candidate ORM cascade.
    db.query(JobAlignment).filter(JobAlignment.candidate_id == candidate_id).delete(
        synchronize_session=False
    )
    db.delete(candidate)
    db.commit()

    return APIResponse(
        status="success",
        data={
            "candidate_id": candidate_id,
            "message": "Candidate and related records deleted successfully.",
        },
    )
