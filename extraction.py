from __future__ import annotations

import hashlib
import json
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


CACHE_FILE = Path(".extraction_cache.json")


def get_file_hash(file_path: Path) -> str:
    """Generate hash of PDF file for cache key."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        sha.update(f.read())
    return sha.hexdigest()


def load_cache() -> dict:
    """Load extraction cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    """Save extraction cache to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def get_from_cache(file_hash: str, cache: dict) -> CandidateExtraction | None:
    """Retrieve cached extraction result."""
    if file_hash in cache:
        try:
            return CandidateExtraction.model_validate(cache[file_hash])
        except Exception:
            return None
    return None


def add_to_cache(file_hash: str, extraction: CandidateExtraction, cache: dict) -> None:
    """Store extraction result in cache."""
    cache[file_hash] = extraction.model_dump()


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
        "2) For university-level education institutions only (UG/PG/MPhil/PhD/Postdoc), try to find QS/THE rankings from known sources (QS/THE) and return qs_rank_reported/the_rank_reported.\n"
        "   For school-level SSC/HSSC records, leave ranking fields null.\n"
        "   If not confidently found for universities, set 'Not Found'.\n"
        "3) If publication is clearly journal or conference, set publication_type accordingly, else null.\n"
        "4) For journals/publication venues, try to identify SJR-style ranking/quartile from credible sources when possible.\n"
        "   If not confidently known, use 'Not Found' in ranking-like fields.\n"
        "5) Include SSE/SSC and HSSC records in education when present.\n\n"
        "Education guidance:\n"
        "- Populate degree_title_normalized_hint and degree_level_hint when inferable from wording.\n"
        "- Use degree_level_hint values only from: ssc, hssc, ug, pg, mphil, phd, postdoc, other.\n"
        "- If a record only says discipline (e.g., Electrical Engineering), keep it in degree_title and specialization, and still assign best-effort level hint.\n\n"
        "- If a line appears in an education table block but is ambiguous, keep it as an education row with partial fields instead of dropping it.\n\n"
        "Experience guidance:\n"
        "- If an experience table row has missing columns (e.g., only organization and duration), still keep it as an experience item with available fields.\n\n"
        "Target sections and fields (matching response schema):\n"
        "- Personal information\n"
        "- Education entries with degree title, specialization, score/CGPA, years, institution/board, and QS/THE ranking fields\n"
        "- Experience entries\n"
        "- Publications (journal/conference metadata as available in CV)\n"
        "- Books authored/co-authored\n"
        "- Patents\n\n"
        "CV Text:\n"
        f"{cv_text}"
    )


def _parse_retry_delay(err_text: str) -> float:
    """Extract retryDelay seconds from a Gemini 429 error message."""
    import re
    # Look for patterns like "retryDelay': '34s'" or "Please retry in 34.812s"
    m = re.search(r"(?:retryDelay['\"]:\s*['\"]|retry in\s+)([\d.]+)s", err_text)
    if m:
        return float(m.group(1))
    return 60.0  # conservative fallback


def extract_structured_data_with_gemini(
    client: genai.Client,
    model_name: str,
    cv_text: str,
) -> CandidateExtraction:
    """Call Gemini with response_schema and parse strict structured output."""
    prompt = build_prompt(cv_text)

    max_attempts = 6
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
            is_quota = "429" in err_text or "RESOURCE_EXHAUSTED" in err_text
            is_transient = any(code in err_text for code in ["429", "500", "502", "503", "504"])

            if is_quota:
                if attempt < max_attempts:
                    wait_seconds = _parse_retry_delay(err_text) + 2
                    print(
                        f"  Rate-limited (attempt {attempt}/{max_attempts}). "
                        f"Waiting {wait_seconds:.0f}s before retry..."
                    )
                    time.sleep(wait_seconds)
                    continue
                else:
                    raise RuntimeError(
                        f"Gemini API quota exhausted after {max_attempts} retries. "
                        f"Error: {exc}"
                    ) from exc

            if attempt == max_attempts or not is_transient:
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc

            wait_seconds = 2 ** (attempt - 1)
            print(
                f"  Gemini transient error (attempt {attempt}/{max_attempts}): {type(exc).__name__}. "
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
    cache = load_cache()

    merged_rows = {table_name: [] for table_name in TABLE_COLUMNS}

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"
        file_hash = get_file_hash(pdf_file)

        try:
            cv_text = extract_text_from_pdf(pdf_file)
            if not cv_text:
                print(f"  Skipped (no extractable text): {pdf_file}")
                continue
        except Exception as exc:
            print(f"  PDF read error: {exc}")
            continue

        # Check cache first
        cached_extraction = get_from_cache(file_hash, cache)
        if cached_extraction:
            print(f"  Using cached extraction")
            structured = cached_extraction
        else:
            try:
                structured = extract_structured_data_with_gemini(
                    client=client,
                    model_name=model_name,
                    cv_text=cv_text,
                )
                add_to_cache(file_hash, structured, cache)
                save_cache(cache)
            except Exception as exc:
                print(f"  Extraction error: {exc}")
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
