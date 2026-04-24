"""
TALASH M2 - Candidate Service

Business logic for loading candidate data from CSVs and JSON assessments.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def load_assessment(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Load a single candidate's JSON assessment from disk."""
    json_path = settings.ASSESSMENTS_DIR / f"{candidate_id}.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Error loading assessment {candidate_id}: {exc}")
        return None


def load_all_assessments() -> List[Dict[str, Any]]:
    """Load all candidate JSON assessments from disk."""
    assessments_dir = settings.ASSESSMENTS_DIR
    if not assessments_dir.exists():
        return []

    assessments = []
    for json_file in sorted(assessments_dir.glob("cand_*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                assessments.append(data)
        except Exception as exc:
            logger.error(f"Error loading {json_file.name}: {exc}")

    return assessments


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
    Get paginated, filtered, sorted list of candidates.
    """
    all_assessments = load_all_assessments()

    # Build list items
    items = []
    for a in all_assessments:
        pi = a.get("personal_info", {})
        items.append({
            "candidate_id": a.get("candidate_id", ""),
            "full_name": pi.get("full_name"),
            "email": pi.get("email"),
            "source_file": pi.get("source_file"),
            "overall_score": a.get("overall_score", 0),
            "overall_tier": a.get("overall_tier", "below_average"),
            "educational_strength": (
                a.get("educational_assessment", {})
                .get("overall_educational_strength", 0)
            ),
            "professional_strength": (
                a.get("employment_assessment", {})
                .get("overall_professional_strength", 0)
            ),
            "completeness_percentage": (
                a.get("missing_info", {})
                .get("completeness_percentage", 0)
            ),
            "missing_info_count": (
                a.get("missing_info", {})
                .get("total_missing_fields", 0)
            ),
            "processed_date": a.get("processed_date"),
        })

    # Search filter
    if search:
        search_lower = search.lower()
        items = [
            i for i in items
            if search_lower in (i.get("full_name") or "").lower()
            or search_lower in (i.get("candidate_id") or "").lower()
        ]

    # Score filter
    if min_score is not None:
        items = [i for i in items if i["overall_score"] >= min_score]
    if max_score is not None:
        items = [i for i in items if i["overall_score"] <= max_score]

    # Sort
    reverse = sort_order.lower() == "desc"
    if sort_by in ("overall_score", "educational_strength",
                    "professional_strength", "completeness_percentage"):
        items.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    elif sort_by == "full_name":
        items.sort(
            key=lambda x: (x.get("full_name") or "").lower(),
            reverse=reverse,
        )
    else:
        items.sort(key=lambda x: x.get("overall_score", 0), reverse=reverse)

    # Pagination
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = items[start:end]

    return {
        "candidates": paginated,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def save_assessment(candidate_id: str, data: Dict[str, Any]) -> None:
    """Save a candidate assessment to JSON."""
    settings.ASSESSMENTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = settings.ASSESSMENTS_DIR / f"{candidate_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
