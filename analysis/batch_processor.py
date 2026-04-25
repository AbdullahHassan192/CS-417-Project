"""
TALASH M2 - Batch Processor

Runs the full M2 analysis pipeline on all candidates from M1 CSV outputs.
Generates JSON assessment files for each candidate.

Usage:
  python -m analysis.batch_processor --input-csvs ./output --output ./data/candidates_assessments
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.data_loader import (
    get_candidate_data,
    get_candidate_ids,
    get_candidate_personal_info,
    load_all_csvs,
)
from analysis.educational_analysis import generate_educational_assessment
from analysis.employment_analysis import generate_employment_assessment
from analysis.missing_info_analysis import (
    detect_missing_information,
    draft_missing_info_email,
    generate_missing_info_summary,
)
from analysis.summary_generation import (
    calculate_candidate_overall_score,
    generate_candidate_summary,
    generate_strengths_and_concerns,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def process_single_candidate(
    candidate_id: str,
    candidate_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the complete M2 analysis pipeline for a single candidate.

    Returns: full assessment dict ready for JSON serialization.
    """
    personal_info = get_candidate_personal_info(
        candidate_data.get("candidates")
    )

    logger.info(
        f"  Analyzing: {personal_info.get('full_name', candidate_id)}"
    )

    # 1. Educational assessment
    edu_assessment = generate_educational_assessment(
        education_df=candidate_data.get("education"),
        experience_df=candidate_data.get("experience"),
    )

    # 2. Employment assessment
    emp_assessment = generate_employment_assessment(
        experience_df=candidate_data.get("experience"),
        education_df=candidate_data.get("education"),
    )

    # 3. Missing info detection
    missing_fields = detect_missing_information(
        candidate_data=candidate_data,
        educational_assessment=edu_assessment,
        employment_assessment=emp_assessment,
    )
    missing_summary = generate_missing_info_summary(missing_fields)

    # 4. Overall score
    overall_score_data = calculate_candidate_overall_score(
        educational_strength=edu_assessment.get("overall_educational_strength", 0),
        professional_strength=emp_assessment.get("overall_professional_strength", 0),
        completeness_score=missing_summary.get("completeness_percentage", 0),
    )

    # 5. Strengths & concerns
    strengths_concerns = generate_strengths_and_concerns(
        educational_assessment=edu_assessment,
        employment_assessment=emp_assessment,
        missing_summary=missing_summary,
    )

    # 6. Summary report
    summary = generate_candidate_summary(
        personal_info=personal_info,
        educational_assessment=edu_assessment,
        employment_assessment=emp_assessment,
        missing_summary=missing_summary,
        overall_score_data=overall_score_data,
        strengths_concerns=strengths_concerns,
    )

    # 7. Draft missing info email (if needed)
    email_data = None
    if missing_summary.get("total_missing_fields", 0) > 0:
        email_data = draft_missing_info_email(
            candidate_name=personal_info.get("full_name"),
            candidate_email=personal_info.get("email"),
            missing_summary=missing_summary,
            source_file=personal_info.get("source_file"),
        )

    # Assemble final assessment JSON
    assessment = {
        "candidate_id": candidate_id,
        "source_file": personal_info.get("source_file"),
        "processed_date": datetime.now().isoformat(),
        "personal_info": personal_info,
        "educational_assessment": edu_assessment,
        "employment_assessment": emp_assessment,
        "timeline_analysis": {
            "overlaps": emp_assessment.get("timeline_overlaps", []),
            "gaps": emp_assessment.get("timeline_gaps", []),
            "consistency_score": emp_assessment.get("timeline_consistency_score", 100),
            "anomalies": emp_assessment.get("timeline_anomalies", []),
        },
        "missing_info": {
            "total_missing_fields": missing_summary.get("total_missing_fields", 0),
            "critical_count": missing_summary.get("critical_count", 0),
            "completeness_percentage": missing_summary.get("completeness_percentage", 100),
            "fields": missing_fields,
        },
        "overall_score": overall_score_data["overall_score"],
        "overall_tier": overall_score_data["tier"],
        "score_breakdown": overall_score_data.get("score_breakdown", {}),
        "summary_report": summary.get("quick_profile", ""),
        "recommendation": summary.get("recommendation", ""),
        "strengths": strengths_concerns["strengths"],
        "concerns": strengths_concerns["concerns"],
        "missing_info_email": email_data,
        "educational_narrative": edu_assessment.get("narrative_summary", ""),
        "employment_narrative": emp_assessment.get("narrative_summary", ""),
    }

    return assessment


def run_batch_processing(
    input_csvs_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """
    Run M2 analysis on all candidates from M1 CSV outputs.
    Saves individual JSON assessment files.
    """
    input_dir = Path(input_csvs_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading M1 CSV data from: {input_dir}")
    tables = load_all_csvs(input_dir)

    candidate_ids = get_candidate_ids(tables)
    logger.info(f"Found {len(candidate_ids)} candidate(s) to process")

    if not candidate_ids:
        logger.warning("No candidates found in CSV data. Exiting.")
        return

    results_summary = []
    for idx, cid in enumerate(candidate_ids, 1):
        logger.info(f"Processing candidate {idx}/{len(candidate_ids)}: {cid}")

        candidate_data = get_candidate_data(tables, cid)
        try:
            assessment = process_single_candidate(cid, candidate_data)

            # Save JSON
            json_path = output_path / f"{cid}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(assessment, f, indent=2, default=str)

            results_summary.append({
                "candidate_id": cid,
                "name": assessment.get("personal_info", {}).get("full_name"),
                "score": assessment["overall_score"],
                "tier": assessment["overall_tier"],
                "status": "success",
            })
            logger.info(
                f"  ✓ Score: {assessment['overall_score']} "
                f"({assessment['overall_tier']})"
            )

        except Exception as exc:
            logger.error(f"  ✗ Error processing {cid}: {exc}")
            results_summary.append({
                "candidate_id": cid,
                "status": "error",
                "error": str(exc),
            })

    # Save batch summary
    summary_path = output_path / "_batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "processed_at": datetime.now().isoformat(),
            "total_candidates": len(candidate_ids),
            "successful": sum(1 for r in results_summary if r["status"] == "success"),
            "failed": sum(1 for r in results_summary if r["status"] == "error"),
            "results": results_summary,
        }, f, indent=2, default=str)

    logger.info(f"\nBatch processing complete!")
    logger.info(f"  Results saved to: {output_path}")
    logger.info(
        f"  Successful: "
        f"{sum(1 for r in results_summary if r['status'] == 'success')}/"
        f"{len(candidate_ids)}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="TALASH M2: Batch process candidate assessments"
    )
    parser.add_argument(
        "--input-csvs",
        default="./output",
        help="Directory containing M1 CSV outputs (default: ./output)",
    )
    parser.add_argument(
        "--output",
        default="./data/candidates_assessments",
        help="Directory for M2 JSON assessments (default: ./data/candidates_assessments)",
    )
    args = parser.parse_args()

    run_batch_processing(args.input_csvs, args.output)


if __name__ == "__main__":
    main()
