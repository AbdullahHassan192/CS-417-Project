from __future__ import annotations

from pathlib import Path

import pandas as pd

from models import TABLE_COLUMNS


def _normalize_table_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Align columns and normalize numeric year fields for CSV output."""
    df = df.reindex(columns=columns)

    for year_col in [
        "admission_year",
        "completion_year",
        "passing_year",
        "start_year",
        "end_year",
        "publication_year",
        "filing_year",
    ]:
        if year_col in df.columns:
            df[year_col] = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")

    return df


def save_relational_csvs(
    table_rows: dict[str, list[dict]],
    output_dir: Path,
    append: bool = True,
) -> None:
    """Save relational tables as separate CSV files with stable schemas.

    When append=True (default), previous rows are preserved and new rows are appended.
    When append=False, files are overwritten with only current run output.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    table_to_file = {
        "candidates": "candidates.csv",
        "education": "education.csv",
        "experience": "experience.csv",
        "publications": "publications.csv",
        "books": "books.csv",
        "patents": "patents.csv",
    }

    for table_name, filename in table_to_file.items():
        rows = table_rows.get(table_name, [])
        columns = TABLE_COLUMNS[table_name]
        new_df = _normalize_table_dataframe(pd.DataFrame(rows), columns)
        file_path = output_dir / filename

        if append and file_path.exists():
            try:
                existing_df = pd.read_csv(file_path)
            except pd.errors.EmptyDataError:
                existing_df = pd.DataFrame(columns=columns)
            existing_df = _normalize_table_dataframe(existing_df, columns)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = _normalize_table_dataframe(combined_df, columns)
            combined_df.to_csv(file_path, index=False, encoding="utf-8")
        else:
            new_df.to_csv(file_path, index=False, encoding="utf-8")
