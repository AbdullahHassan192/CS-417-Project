"""
TALASH M2 - Pydantic Response Schemas

Defines response models for all API endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    status: str = "success"
    data: Any = None
    error: Optional[str] = None


# ── Candidate List ──────────────────────────────────────────────────────────

class CandidateListItem(BaseModel):
    """Summary item for candidate listing."""
    candidate_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    source_file: Optional[str] = None
    overall_score: float = 0.0
    overall_tier: str = "below_average"
    educational_strength: float = 0.0
    professional_strength: float = 0.0
    total_years_of_experience: float = 0.0
    publication_count: int = 0
    completeness_percentage: float = 0.0
    missing_info_count: int = 0
    pipeline_status: str = "unreviewed"
    processed_date: Optional[str] = None


class CandidateListResponse(BaseModel):
    """Response for GET /api/candidates/list."""
    candidates: List[CandidateListItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 10


# ── Full Assessment ─────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    """Score breakdown details."""
    educational_strength: float = 0.0
    educational_weight: float = 0.30
    educational_contribution: float = 0.0
    professional_strength: float = 0.0
    professional_weight: float = 0.35
    professional_contribution: float = 0.0
    completeness_score: float = 0.0
    completeness_weight: float = 0.15
    completeness_contribution: float = 0.0
    skill_relevance: float = 50.0
    skill_weight: float = 0.20
    skill_contribution: float = 0.0


class EducationalProfileResponse(BaseModel):
    """Educational assessment details."""
    overall_educational_strength: float = 0.0
    academic_performance_level: str = "unknown"
    highest_qualification_level: str = "unknown"
    institution_quality_average: Optional[float] = None
    academic_consistency_score: float = 0.0
    educational_continuity_score: float = 0.0
    specialization_consistency: float = 0.0
    performance_trend: str = "variable"
    average_score: Optional[float] = None
    school_records: List[Dict[str, Any]] = []
    higher_education_records: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    narrative_summary: str = ""


class EmploymentProfileResponse(BaseModel):
    """Employment assessment details."""
    total_years_of_experience: float = 0.0
    experience_level: str = "entry_level"
    employment_continuity_score: float = 0.0
    career_progression_score: float = 0.0
    timeline_consistency_score: float = 100.0
    overall_professional_strength: float = 0.0
    seniority_trajectory: str = "stable"
    career_growth_rate: str = "minimal"
    experience_records: List[Dict[str, Any]] = []
    timeline_overlaps: List[Dict[str, Any]] = []
    timeline_gaps: List[Dict[str, Any]] = []
    justified_gaps: List[Dict[str, Any]] = []
    narrative_summary: str = ""


class ResearchProfileResponse(BaseModel):
    """Research assessment details for M2."""
    overall_research_strength: float = 0.0
    total_publications: int = 0
    total_books: int = 0
    total_patents: int = 0
    publications: List[Dict[str, Any]] = []
    books: List[Dict[str, Any]] = []
    patents: List[Dict[str, Any]] = []
    narrative_summary: str = ""


class MissingInfoField(BaseModel):
    """Single missing information entry."""
    section: str
    field_name: str
    severity: str
    current_value: Optional[str] = None
    missing_detail: str
    impact: str = ""


class MissingInfoEmailDraft(BaseModel):
    """Email draft for requesting missing information."""
    subject: str = ""
    body: str = ""
    recipient: str = ""
    candidate_name: str = ""
    date_drafted: Optional[str] = None
    missing_items_count: int = 0
    tone: str = "professional"


class MissingInfoResponse(BaseModel):
    """Missing information details."""
    total_missing_fields: int = 0
    critical_count: int = 0
    important_count: int = 0
    useful_count: int = 0
    completeness_percentage: float = 100.0
    fields: List[MissingInfoField] = []
    email_draft: Optional[MissingInfoEmailDraft] = None


class TimelineAnalysisResponse(BaseModel):
    """Timeline consistency analysis."""
    overlaps: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    consistency_score: float = 100.0
    anomaly_count: int = 0
    anomalies: List[str] = []


class FullAssessmentResponse(BaseModel):
    """Complete candidate assessment."""
    candidate_id: str
    source_file: Optional[str] = None
    processed_date: Optional[str] = None
    personal_info: Dict[str, Any] = {}
    overall_score: float = 0.0
    overall_tier: str = "below_average"
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    educational_assessment: EducationalProfileResponse = EducationalProfileResponse()
    employment_assessment: EmploymentProfileResponse = EmploymentProfileResponse()
    research_assessment: ResearchProfileResponse = ResearchProfileResponse()
    timeline_analysis: TimelineAnalysisResponse = TimelineAnalysisResponse()
    missing_info: MissingInfoResponse = MissingInfoResponse()
    strengths: List[str] = []
    concerns: List[str] = []
    summary_report: str = ""
    recommendation: str = ""
    missing_info_email: Optional[MissingInfoEmailDraft] = None


class CandidateSummaryResponse(BaseModel):
    """Human-readable candidate summary."""
    candidate_id: str
    candidate_name: str = ""
    overall_score: float = 0.0
    overall_tier: str = "below_average"
    quick_profile: str = ""
    strengths: List[str] = []
    concerns: List[str] = []
    recommendation: str = ""
    educational_narrative: str = ""
    employment_narrative: str = ""
    research_narrative: str = ""


# ── Processing ──────────────────────────────────────────────────────────────

class ProcessFolderRequest(BaseModel):
    """Request body for POST /api/candidates/process-folder."""
    folder_path: str = Field(..., description="Path to folder containing CVs")


class ProcessFolderResponse(BaseModel):
    """Response for POST /api/candidates/process-folder."""
    status: str = "processing"
    file_count: int = 0
    job_id: str = ""
    message: str = ""


class BatchProcessRequest(BaseModel):
    """Request body for POST /api/candidates/batch-process."""
    candidate_ids: List[str] = Field(
        default=[], description="List of candidate IDs to process"
    )


class BatchProcessResponse(BaseModel):
    """Response for batch processing."""
    status: str = "completed"
    total_processed: int = 0
    emails_drafted: int = 0
    results: List[Dict[str, Any]] = []


class SendInfoRequestBody(BaseModel):
    """Request body for POST /api/candidates/{id}/send-info-request."""
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    recipient: Optional[str] = None


class CandidateStatusUpdate(BaseModel):
    """Request body for POST /api/candidates/{id}/status."""
    status: str = Field(..., description="Candidate pipeline status")
