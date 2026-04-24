"""
TALASH M2 - Assessment Service

Business logic for running the M2 analysis pipeline from the backend.
"""
from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

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


def run_analysis_pipeline() -> Dict[str, Any]:
    """
    Run M2 analysis on all candidates from M1 CSV outputs.

    Returns: summary of processing results.
    """
    try:
        from analysis.batch_processor import run_batch_processing

        run_batch_processing(
            input_csvs_dir=settings.CSV_OUTPUT_DIR,
            output_dir=settings.ASSESSMENTS_DIR,
        )

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


def generate_batch_emails(candidate_ids: List[str]) -> Dict[str, Any]:
    """
    Generate missing info emails for a batch of candidates.
    """
    from backend.services.candidate_service import load_assessment

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
