"""
TALASH M3 - Legacy Candidate Service

File-system based candidate listing and assessment loading.
Kept for backward compatibility and fallback when DB entries don't exist.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def get_candidate_list(
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    search: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build candidate list from JSON assessment files on disk.
    """
    assessments_dir = settings.ASSESSMENTS_DIR
    if not assessments_dir.exists():
        return {"total": 0, "page": page, "page_size": page_size, "candidates": []}

    all_candidates: List[Dict[str, Any]] = []
    for json_file in assessments_dir.glob("cand_*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            pi = data.get("personal_info", {})
            edu = data.get("educational_assessment", {})
            emp = data.get("employment_assessment", {})
            missing = data.get("missing_info", {})

            all_candidates.append({
                "candidate_id": data.get("candidate_id"),
                "full_name": pi.get("full_name", "Unknown"),
                "email": pi.get("email"),
                "source_file": pi.get("source_file"),
                "post_applied_for": pi.get("post_applied_for"),
                "overall_score": data.get("overall_score", 0),
                "overall_tier": data.get("overall_tier", "below_average"),
                "educational_strength": edu.get("overall_educational_strength", 0),
                "professional_strength": emp.get("overall_professional_strength", 0),
                "publication_count": data.get("research_assessment", {}).get("total_publications", 0),
                "missing_info_count": missing.get("total_missing_fields", 0),
                "completeness_percentage": missing.get("completeness_percentage", 100),
            })
        except Exception as exc:
            logger.error(f"Error loading {json_file}: {exc}")

    # Filter
    if search:
        search_lower = search.lower()
        all_candidates = [
            c for c in all_candidates
            if search_lower in (c.get("full_name") or "").lower()
        ]
    if min_score is not None:
        all_candidates = [c for c in all_candidates if c["overall_score"] >= min_score]
    if max_score is not None:
        all_candidates = [c for c in all_candidates if c["overall_score"] <= max_score]

    # Sort
    reverse = sort_order == "desc"
    all_candidates.sort(key=lambda c: c.get(sort_by, 0) or 0, reverse=reverse)

    total = len(all_candidates)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "candidates": all_candidates[start:end],
    }


def load_assessment(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Load full assessment from JSON file on disk."""
    assessments_dir = settings.ASSESSMENTS_DIR
    if not assessments_dir.exists():
        return None

    # Search for matching file
    for json_file in assessments_dir.glob("cand_*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("candidate_id") == candidate_id:
                return data
        except Exception:
            continue

    return None
