"""
TALASH M3 - Assessment Service

Business logic for running the analysis pipeline from the backend.
Now stores results in the database alongside file-system.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings

logger = logging.getLogger(__name__)


def run_preprocessing(folder_path: str) -> Dict[str, Any]:
    """
    Trigger M1 preprocessing pipeline on a folder of CVs.

    Returns: status dict with file count and job_id.
    """
    input_path = Path(folder_path)
    if not input_path.exists():
        return {
            "status": "error",
            "message": f"Folder not found: {folder_path}",
            "file_count": 0,
            "job_id": "",
        }

    # Count PDFs
    pdf_files = list(input_path.rglob("*.pdf"))
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    if not pdf_files:
        return {
            "status": "error",
            "message": "No PDF files found in the specified folder.",
            "file_count": 0,
            "job_id": job_id,
        }

    # Validate API key before running
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "status": "error",
            "message": (
                "No valid Gemini API key configured. "
                "Please set GEMINI_API_KEY in your .env file. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            ),
            "file_count": 0,
            "job_id": job_id,
        }

    # Run preprocessing (import M1 modules)
    try:
        from extraction import process_pdfs

        process_pdfs(
            input_path=input_path,
            output_dir=settings.CSV_OUTPUT_DIR,
            api_key=api_key,
            model_name=settings.GEMINI_MODEL,
            append=False,
        )

        return {
            "status": "completed",
            "message": f"Successfully processed {len(pdf_files)} CV(s).",
            "file_count": len(pdf_files),
            "job_id": job_id,
        }
    except Exception as exc:
        logger.error(f"Preprocessing error: {exc}")
        return {
            "status": "error",
            "message": f"Processing failed: {str(exc)}",
            "file_count": len(pdf_files),
            "job_id": job_id,
        }


def run_analysis_pipeline(db=None) -> Dict[str, Any]:
    """
    Run M2/M3 analysis on all candidates from M1 CSV outputs.

    If a DB session is provided, results are also stored in the database.
    Returns: summary of processing results.
    """
    try:
        from analysis.batch_processor import run_batch_processing

        run_batch_processing(
            input_csvs_dir=settings.CSV_OUTPUT_DIR,
            output_dir=settings.ASSESSMENTS_DIR,
        )

        # If DB provided, import results into the database
        if db:
            _import_assessments_to_db(db)

        return {
            "status": "completed",
            "message": "Analysis pipeline completed successfully.",
        }
    except Exception as exc:
        logger.error(f"Analysis pipeline error: {exc}")
        return {
            "status": "error",
            "message": f"Analysis failed: {str(exc)}",
        }


def _import_assessments_to_db(db):
    """Import JSON assessment files into the database."""
    from backend.database import (
        Candidate, CandidateAnalysis, MissingInfoLog,
    )
    import pandas as pd

    assessments_dir = settings.ASSESSMENTS_DIR

    # Also re-import candidates from CSV to ensure DB is in sync
    csv_dir = settings.CSV_OUTPUT_DIR
    candidates_csv = csv_dir / "candidates.csv"
    if candidates_csv.exists():
        df = pd.read_csv(candidates_csv)
        for _, row in df.iterrows():
            cid = str(row.get("candidate_id", ""))
            if not cid:
                continue
            existing = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
            if not existing:
                c = Candidate(
                    candidate_id=cid,
                    source_file=str(row.get("source_file", "")),
                    full_name=str(row.get("full_name", "")) if pd.notna(row.get("full_name")) else None,
                    email=str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                    phone=str(row.get("phone", "")) if pd.notna(row.get("phone")) else None,
                    post_applied_for=str(row.get("post_applied_for", "")) if pd.notna(row.get("post_applied_for")) else None,
                    uploaded_at=datetime.now(),
                )
                db.add(c)
        db.commit()

    # Import assessments from JSON files
    if assessments_dir.exists():
        for json_file in assessments_dir.glob("cand_*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cid = data.get("candidate_id")
                if not cid:
                    continue

                cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
                if not cand:
                    continue

                # Update overall score
                cand.overall_score = data.get("overall_score", 0.0)
                cand.processed_at = datetime.now()

                # Upsert analysis
                existing = db.query(CandidateAnalysis).filter(
                    CandidateAnalysis.candidate_id == cid,
                    CandidateAnalysis.analysis_type == "full_assessment",
                ).first()
                if existing:
                    existing.analysis_json = json.dumps(data)
                    existing.llm_summary = data.get("summary_report", "")
                    existing.generated_at = datetime.now()
                else:
                    db.add(CandidateAnalysis(
                        candidate_id=cid,
                        analysis_type="full_assessment",
                        analysis_json=json.dumps(data),
                        llm_summary=data.get("summary_report", ""),
                    ))

                # Upsert missing info
                missing = data.get("missing_info", {})
                if missing.get("total_missing_fields", 0) > 0:
                    existing_log = db.query(MissingInfoLog).filter(
                        MissingInfoLog.candidate_id == cid
                    ).first()
                    if existing_log:
                        existing_log.missing_fields = json.dumps(missing.get("fields", []))
                        email_data = data.get("missing_info_email")
                        if email_data:
                            existing_log.draft_email = json.dumps(email_data)
                    else:
                        db.add(MissingInfoLog(
                            candidate_id=cid,
                            missing_fields=json.dumps(missing.get("fields", [])),
                            draft_email=json.dumps(data.get("missing_info_email")) if data.get("missing_info_email") else None,
                        ))

            except Exception as exc:
                logger.error(f"Failed to import assessment {json_file.name}: {exc}")

        db.commit()


def generate_batch_emails(candidate_ids: List[str]) -> Dict[str, Any]:
    """
    Generate missing info emails for a batch of candidates.
    """
    from backend.services.candidate_service_legacy import load_assessment

    results = []
    for cid in candidate_ids:
        assessment = load_assessment(cid)
        if assessment and assessment.get("missing_info_email"):
            results.append({
                "candidate_id": cid,
                "name": assessment.get("personal_info", {}).get("full_name"),
                "email_drafted": True,
                "email": assessment["missing_info_email"],
            })
        elif assessment:
            results.append({
                "candidate_id": cid,
                "name": assessment.get("personal_info", {}).get("full_name"),
                "email_drafted": False,
                "reason": "No missing information detected",
            })

    return {
        "status": "completed",
        "total_processed": len(candidate_ids),
        "emails_drafted": sum(1 for r in results if r.get("email_drafted")),
        "results": results,
    }

