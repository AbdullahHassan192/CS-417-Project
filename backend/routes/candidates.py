"""
TALASH M2 - Candidates API Routes

All 7 REST endpoints for the candidates resource.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.schemas import (
    APIResponse,
    BatchProcessRequest,
    BatchProcessResponse,
    CandidateListResponse,
    CandidateSummaryResponse,
    FullAssessmentResponse,
    MissingInfoResponse,
    MissingInfoEmailDraft,
    MissingInfoField,
    ProcessFolderRequest,
    ProcessFolderResponse,
    SendInfoRequestBody,
)
from backend.services.candidate_service import (
    get_candidate_list,
    load_assessment,
)
from backend.services.assessment_service import (
    generate_batch_emails,
    run_analysis_pipeline,
    run_preprocessing,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/candidates", tags=["candidates"])


# ── 1. POST /api/candidates/process-folder ──────────────────────────────────
@router.post("/process-folder", response_model=APIResponse)
async def process_folder(request: ProcessFolderRequest):
    """Trigger M1 preprocessing pipeline on a folder of CVs."""
    result = run_preprocessing(request.folder_path)

    # Also run M2 analysis after preprocessing
    if result["status"] == "completed":
        analysis_result = run_analysis_pipeline()
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
):
    """List all processed candidates with pagination and filtering."""
    result = get_candidate_list(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        min_score=min_score,
        max_score=max_score,
    )
    return APIResponse(status="success", data=result)


# ── 3. GET /api/candidates/{candidate_id}/full-assessment ───────────────────
@router.get("/{candidate_id}/full-assessment", response_model=APIResponse)
async def get_full_assessment(candidate_id: str):
    """Get complete candidate assessment with all sub-scores."""
    assessment = load_assessment(candidate_id)
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment not found for candidate: {candidate_id}",
        )
    return APIResponse(status="success", data=assessment)


# ── 4. GET /api/candidates/{candidate_id}/missing-info ──────────────────────
@router.get("/{candidate_id}/missing-info", response_model=APIResponse)
async def get_missing_info(candidate_id: str):
    """Get missing information details and email draft."""
    assessment = load_assessment(candidate_id)
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
async def send_info_request(candidate_id: str, body: SendInfoRequestBody):
    """
    Send/save missing information request email.
    NOTE: Email sending is mocked for M2.
    """
    assessment = load_assessment(candidate_id)
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

    # In M2 we mock the sending — just return the email as "draft_only"
    return APIResponse(
        status="success",
        data={
            "status": "draft_only",
            "email_id": f"email_{candidate_id}",
            "subject": body.email_subject or email_data.get("subject", ""),
            "recipient": body.recipient or email_data.get("recipient", ""),
            "message": "Email saved as draft. Actual sending will be implemented in M3.",
        },
    )


# ── 6. POST /api/candidates/batch-process ───────────────────────────────────
@router.post("/batch-process", response_model=APIResponse)
async def batch_process(request: BatchProcessRequest):
    """Run missing info email generation for a batch of candidates."""
    if not request.candidate_ids:
        # If no specific IDs provided, process all
        all_data = get_candidate_list(page=1, page_size=1000)
        candidate_ids = [
            c["candidate_id"] for c in all_data.get("candidates", [])
        ]
    else:
        candidate_ids = request.candidate_ids

    result = generate_batch_emails(candidate_ids)
    return APIResponse(status="success", data=result)


# ── 7. GET /api/candidates/{candidate_id}/summary ──────────────────────────
@router.get("/{candidate_id}/summary", response_model=APIResponse)
async def get_candidate_summary(candidate_id: str):
    """Get human-readable candidate summary report."""
    assessment = load_assessment(candidate_id)
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
