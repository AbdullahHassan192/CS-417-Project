from __future__ import annotations

import time
import uuid
from pathlib import Path

import fitz
from google import genai
from google.genai import types
from pydantic import ValidationError

from io_csv import save_relational_csvs
from models import CandidateExtraction, ExtractionResult, TABLE_COLUMNS
from normalization import flatten_to_relational_rows


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all raw text from a PDF using PyMuPDF."""
    try:
        with fitz.open(pdf_path) as doc:
            pages = [page.get_text("text") for page in doc]
        return "\n".join(pages).strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to read PDF '{pdf_path}': {exc}") from exc


def build_prompt(cv_text: str) -> str:
    """Construct extraction prompt while relying on response_schema for structure."""
    return (
        "You are extracting structured candidate data from a CV. "
        "Return only fields grounded in CV text. If data is missing, return null "
        "for scalars and [] for lists. Do not infer unstated facts.\n\n"
        "Extract comprehensive fields needed for future educational and research analysis.\n"
        "Important constraints:\n"
        "1) Keep exact reported values for marks/CGPA/percentages and publication metrics.\n"
        "2) Do not fabricate indexing/ranking verification from external sources.\n"
        "3) If publication is clearly journal or conference, set publication_type accordingly, else null.\n"
        "4) Include SSE/SSC and HSSC records in education when present.\n\n"
        "Education guidance:\n"
        "- Populate degree_title_normalized_hint and degree_level_hint when inferable from wording.\n"
        "- Use degree_level_hint values only from: ssc, hssc, ug, pg, mphil, phd, postdoc, other.\n"
        "- If a record only says discipline (e.g., Electrical Engineering), keep it in degree_title and specialization, and still assign best-effort level hint.\n\n"
        "- If a line appears in an education table block but is ambiguous, keep it as an education row with partial fields instead of dropping it.\n\n"
        "Experience guidance:\n"
        "- If an experience table row has missing columns (e.g., only organization and duration), still keep it as an experience item with available fields.\n\n"
        "Target sections and fields (matching response schema):\n"
        "- Personal information\n"
        "- Education entries with degree title, specialization, score/CGPA, years, institution/board\n"
        "- Experience entries\n"
        "- Publications (journal/conference metadata as available in CV)\n"
        "- Books authored/co-authored\n"
        "- Patents\n\n"
        "CV Text:\n"
        f"{cv_text}"
    )


def extract_structured_data_with_gemini(
    client: genai.Client,
    model_name: str,
    cv_text: str,
) -> CandidateExtraction:
    """Call Gemini with response_schema and parse strict structured output."""
    prompt = build_prompt(cv_text)

    max_attempts = 4
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CandidateExtraction,
                    temperature=0,
                ),
            )
            break
        except Exception as exc:
            err_text = str(exc)
            transient = any(code in err_text for code in ["429", "500", "502", "503", "504"])
            if attempt == max_attempts or not transient:
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc

            wait_seconds = 2 ** (attempt - 1)
            print(
                f"  Gemini transient error (attempt {attempt}/{max_attempts}): {err_text}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    if response.parsed is not None:
        return response.parsed

    try:
        return CandidateExtraction.model_validate_json(response.text)
    except ValidationError as exc:
        raise RuntimeError(f"Gemini returned invalid structured JSON: {exc}") from exc


def find_pdf_files(input_path: Path) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.rglob("*.pdf"))
    raise ValueError(f"Input path is neither a PDF file nor a directory: {input_path}")


def process_pdfs(
    input_path: Path,
    output_dir: Path,
    api_key: str,
    model_name: str,
    append: bool,
) -> None:
    pdf_files = find_pdf_files(input_path)
    if not pdf_files:
        raise ValueError(f"No PDF files found at: {input_path}")

    client = genai.Client(api_key=api_key)

    merged_rows = {table_name: [] for table_name in TABLE_COLUMNS}

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"

        try:
            cv_text = extract_text_from_pdf(pdf_file)
            if not cv_text:
                print(f"  Skipped (no extractable text): {pdf_file}")
                continue
        except Exception as exc:
            print(f"  PDF read error: {exc}")
            continue

        try:
            structured = extract_structured_data_with_gemini(
                client=client,
                model_name=model_name,
                cv_text=cv_text,
            )
        except Exception as exc:
            print(f"  Gemini extraction error: {exc}")
            continue

        result = ExtractionResult(
            candidate_id=candidate_id,
            source_file=str(pdf_file.name),
            data=structured,
        )

        rows = flatten_to_relational_rows(result)
        for table_name, items in rows.items():
            merged_rows[table_name].extend(items)

    save_relational_csvs(merged_rows, output_dir, append=append)
    print(f"\nSaved CSV tables to: {output_dir.resolve()}")
    print(f"- write mode: {'append' if append else 'overwrite'}")
    print("- candidates.csv")
    print("- education.csv")
    print("- experience.csv")
    print("- publications.csv")
    print("- books.csv")
    print("- patents.csv")
    print(f"- processed PDFs: {len(pdf_files)}")
