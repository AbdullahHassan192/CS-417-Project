"""
TALASH M2 - Data Loader

Loads M1 CSV outputs into Python objects for M2 analysis.
Handles missing files and malformed data gracefully.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def load_csv_safe(file_path: Path) -> pd.DataFrame:
    """Load a CSV file safely, returning empty DataFrame on error."""
    if not file_path.exists():
        logger.warning(f"CSV file not found: {file_path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, dtype=str)
        # Convert year columns to nullable integers
        year_cols = [
            "admission_year", "completion_year", "passing_year",
            "start_year", "end_year", "publication_year", "filing_year",
        ]
        for col in year_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        # Convert score_value and score_normalized_percentage to float
        float_cols = ["score_value", "score_normalized_percentage"]
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as exc:
        logger.error(f"Error loading CSV {file_path}: {exc}")
        return pd.DataFrame()


def load_all_csvs(output_dir: str | Path) -> Dict[str, pd.DataFrame]:
    """
    Load all 6 M1 CSV files from the output directory.

    Returns: dict with keys: candidates, education, experience,
             publications, books, patents
    """
    output_dir = Path(output_dir)
    tables = {}
    file_map = {
        "candidates": "candidates.csv",
        "education": "education.csv",
        "experience": "experience.csv",
        "publications": "publications.csv",
        "books": "books.csv",
        "patents": "patents.csv",
    }
    for table_name, filename in file_map.items():
        tables[table_name] = load_csv_safe(output_dir / filename)
        logger.info(f"Loaded {table_name}: {len(tables[table_name])} rows")
    return tables


def get_candidate_ids(tables: Dict[str, pd.DataFrame]) -> List[str]:
    """Get list of unique candidate IDs from the candidates table."""
    candidates_df = tables.get("candidates", pd.DataFrame())
    if candidates_df.empty or "candidate_id" not in candidates_df.columns:
        return []
    return candidates_df["candidate_id"].dropna().unique().tolist()


def get_candidate_data(
    tables: Dict[str, pd.DataFrame],
    candidate_id: str,
) -> Dict[str, pd.DataFrame]:
    """
    Extract all data for a single candidate across all tables.

    Returns: dict with filtered DataFrames for the given candidate_id
    """
    result = {}
    for table_name, df in tables.items():
        if df.empty or "candidate_id" not in df.columns:
            result[table_name] = pd.DataFrame()
        else:
            result[table_name] = df[df["candidate_id"] == candidate_id].copy()
    return result


def get_candidate_personal_info(candidate_df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Extract personal info dict from a single-row candidates DataFrame."""
    if candidate_df.empty:
        return {}
    row = candidate_df.iloc[0]
    fields = [
        "candidate_id", "source_file", "full_name", "father_guardian_name",
        "spouse_name", "date_of_birth", "nationality", "marital_status",
        "current_salary", "expected_salary", "present_employment", "post_applied_for",
    ]
    return {f: row.get(f, None) if pd.notna(row.get(f, None)) else None for f in fields}
