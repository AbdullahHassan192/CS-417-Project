"""
TALASH M3 - Database Seed / CSV Migration

Imports existing CSV data into SQLite database.

Usage:
    python manage.py seed
    python manage.py reset   (drop all + recreate + seed)
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.database import (
    Base, SessionLocal, engine, init_db,
    Candidate, Education, Experience, Publication, Book, Patent,
    CandidateAnalysis, MissingInfoLog, PipelineStatus,
)
from backend.auth import seed_admin_user


def _safe_val(val, default=None):
    """Return None for NaN/empty values."""
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    s = str(val).strip()
    if s in ("", "nan", "None", "NaN"):
        return default
    return s


def _safe_int(val):
    v = _safe_val(val)
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    v = _safe_val(val)
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _safe_bool(val):
    v = _safe_val(val)
    if v is None:
        return None
    return str(v).lower() in ("true", "1", "yes")


def seed_from_csvs(csv_dir: Path, assessments_dir: Path = None):
    """Import CSV data into database."""
    db = SessionLocal()

    try:
        # Seed admin
        seed_admin_user(db)
        print("[✓] Admin user seeded")

        # Load CSVs
        csv_files = {
            "candidates": csv_dir / "candidates.csv",
            "education": csv_dir / "education.csv",
            "experience": csv_dir / "experience.csv",
            "publications": csv_dir / "publications.csv",
            "books": csv_dir / "books.csv",
            "patents": csv_dir / "patents.csv",
        }

        dfs = {}
        for name, path in csv_files.items():
            if path.exists():
                dfs[name] = pd.read_csv(path)
                print(f"  Loaded {name}.csv: {len(dfs[name])} rows")
            else:
                dfs[name] = pd.DataFrame()
                print(f"  {name}.csv not found, skipping")

        # Import candidates
        if not dfs["candidates"].empty:
            for _, row in dfs["candidates"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid:
                    continue
                existing = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
                if existing:
                    continue
                c = Candidate(
                    candidate_id=cid,
                    source_file=_safe_val(row.get("source_file")),
                    full_name=_safe_val(row.get("full_name")),
                    father_guardian_name=_safe_val(row.get("father_guardian_name")),
                    date_of_birth=_safe_val(row.get("date_of_birth")),
                    nationality=_safe_val(row.get("nationality")),
                    marital_status=_safe_val(row.get("marital_status")),
                    present_employment=_safe_val(row.get("present_employment")),
                    post_applied_for=_safe_val(row.get("post_applied_for")),
                    email=_safe_val(row.get("email")),
                    phone=_safe_val(row.get("phone")),
                    uploaded_at=datetime.now(),
                )
                db.add(c)
            db.commit()
            print(f"[✓] Imported {db.query(Candidate).count()} candidates")

        # Import education
        if not dfs["education"].empty:
            for _, row in dfs["education"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid or not db.query(Candidate).filter(Candidate.candidate_id == cid).first():
                    continue
                e = Education(
                    candidate_id=cid,
                    education_stage=_safe_val(row.get("education_stage")),
                    degree_title_raw=_safe_val(row.get("degree_title_raw")),
                    degree_title_normalized=_safe_val(row.get("degree_title_normalized")),
                    degree_level=_safe_val(row.get("degree_level")),
                    specialization=_safe_val(row.get("specialization")),
                    institution_name=_safe_val(row.get("institution_name")),
                    board_or_university=_safe_val(row.get("board_or_university")),
                    admission_year=_safe_int(row.get("admission_year")),
                    completion_year=_safe_int(row.get("completion_year")),
                    passing_year=_safe_int(row.get("passing_year")),
                    score_raw=_safe_val(row.get("score_raw")),
                    score_type=_safe_val(row.get("score_type")),
                    score_value=_safe_float(row.get("score_value")),
                    score_scale=_safe_float(row.get("score_scale")),
                    score_normalized_percentage=_safe_float(row.get("score_normalized_percentage")),
                )
                db.add(e)
            db.commit()
            print(f"[✓] Imported {db.query(Education).count()} education records")

        # Import experience
        if not dfs["experience"].empty:
            for _, row in dfs["experience"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid or not db.query(Candidate).filter(Candidate.candidate_id == cid).first():
                    continue
                exp = Experience(
                    candidate_id=cid,
                    post_job_title=_safe_val(row.get("post_job_title")),
                    organization=_safe_val(row.get("organization")),
                    location=_safe_val(row.get("location")),
                    duration=_safe_val(row.get("duration")),
                    start_year=_safe_int(row.get("start_year")),
                    end_year=_safe_int(row.get("end_year")),
                    employment_type=_safe_val(row.get("employment_type")),
                )
                db.add(exp)
            db.commit()
            print(f"[✓] Imported {db.query(Experience).count()} experience records")

        # Import publications
        if not dfs["publications"].empty:
            for _, row in dfs["publications"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid or not db.query(Candidate).filter(Candidate.candidate_id == cid).first():
                    continue
                p = Publication(
                    candidate_id=cid,
                    paper_title=_safe_val(row.get("paper_title")),
                    publication_type=_safe_val(row.get("publication_type")),
                    authors=_safe_val(row.get("authors")),
                    author_count=_safe_int(row.get("author_count")),
                    candidate_author_position=_safe_int(row.get("candidate_author_position")),
                    candidate_authorship_role=_safe_val(row.get("candidate_authorship_role")),
                    candidate_is_first_author=_safe_bool(row.get("candidate_is_first_author")),
                    venue_name=_safe_val(row.get("venue_name")),
                    journal_name=_safe_val(row.get("journal_name")),
                    conference_name=_safe_val(row.get("conference_name")),
                    issn=_safe_val(row.get("issn")),
                    doi=_safe_val(row.get("doi")),
                    impact_factor_reported=_safe_float(row.get("impact_factor_reported")),
                    quartile_reported=_safe_val(row.get("quartile_reported")),
                    wos_indexed_reported=_safe_bool(row.get("wos_indexed_reported")),
                    scopus_indexed_reported=_safe_bool(row.get("scopus_indexed_reported")),
                    conference_rank=_safe_val(row.get("conference_rank_reported")),
                    publication_year=_safe_int(row.get("publication_year")),
                )
                db.add(p)
            db.commit()
            print(f"[✓] Imported {db.query(Publication).count()} publications")

        # Import books
        if not dfs["books"].empty:
            for _, row in dfs["books"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid or not db.query(Candidate).filter(Candidate.candidate_id == cid).first():
                    continue
                b = Book(
                    candidate_id=cid,
                    book_title=_safe_val(row.get("book_title")),
                    authors=_safe_val(row.get("authors")),
                    candidate_authorship_role=_safe_val(row.get("candidate_authorship_role")),
                    isbn=_safe_val(row.get("isbn")),
                    publisher=_safe_val(row.get("publisher")),
                    publication_year=_safe_int(row.get("publication_year")),
                    online_link=_safe_val(row.get("url")),
                )
                db.add(b)
            db.commit()
            print(f"[✓] Imported {db.query(Book).count()} books")

        # Import patents
        if not dfs["patents"].empty:
            for _, row in dfs["patents"].iterrows():
                cid = _safe_val(row.get("candidate_id"))
                if not cid or not db.query(Candidate).filter(Candidate.candidate_id == cid).first():
                    continue
                pt = Patent(
                    candidate_id=cid,
                    patent_number=_safe_val(row.get("patent_number")),
                    patent_title=_safe_val(row.get("patent_title")),
                    inventors=_safe_val(row.get("inventors")),
                    candidate_inventor_role=_safe_val(row.get("candidate_inventor_role")),
                    filing_country=_safe_val(row.get("filing_country")),
                    filing_year=_safe_int(row.get("filing_year")),
                    verification_link=_safe_val(row.get("url")),
                )
                db.add(pt)
            db.commit()
            print(f"[✓] Imported {db.query(Patent).count()} patents")

        # Import existing assessments if available
        if assessments_dir and assessments_dir.exists():
            count = 0
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

                    # Store full assessment
                    existing = db.query(CandidateAnalysis).filter(
                        CandidateAnalysis.candidate_id == cid,
                        CandidateAnalysis.analysis_type == "full_assessment"
                    ).first()
                    if not existing:
                        analysis = CandidateAnalysis(
                            candidate_id=cid,
                            analysis_type="full_assessment",
                            analysis_json=json.dumps(data),
                            llm_summary=data.get("summary_report", ""),
                        )
                        db.add(analysis)

                    # Store missing info
                    missing = data.get("missing_info", {})
                    email_data = data.get("missing_info_email")
                    if missing.get("total_missing_fields", 0) > 0:
                        existing_log = db.query(MissingInfoLog).filter(
                            MissingInfoLog.candidate_id == cid
                        ).first()
                        if not existing_log:
                            log = MissingInfoLog(
                                candidate_id=cid,
                                missing_fields=json.dumps(missing.get("fields", [])),
                                draft_email=json.dumps(email_data) if email_data else None,
                            )
                            db.add(log)

                    # Create pipeline status
                    existing_ps = db.query(PipelineStatus).filter(
                        PipelineStatus.candidate_id == cid
                    ).first()
                    if not existing_ps:
                        ps = PipelineStatus(
                            candidate_id=cid,
                            status="analyzed",
                        )
                        db.add(ps)

                    count += 1
                except Exception as exc:
                    print(f"  Warning: Failed to import assessment {json_file.name}: {exc}")

            db.commit()
            print(f"[✓] Imported {count} assessment files")

        print("\n✅ Database seeding complete!")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Seeding failed: {exc}")
        raise
    finally:
        db.close()


def reset_db():
    """Drop all tables and recreate."""
    Base.metadata.drop_all(bind=engine)
    print("[✓] All tables dropped")
    init_db()
    print("[✓] Tables recreated")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TALASH DB Management")
    parser.add_argument("command", choices=["seed", "reset", "init"], help="Command to run")
    parser.add_argument("--csv-dir", default="./output", help="CSV directory")
    parser.add_argument("--assessments-dir", default="./data/candidates_assessments", help="Assessments directory")
    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("Database initialized")
    elif args.command == "reset":
        reset_db()
        csv_dir = Path(args.csv_dir)
        assessments_dir = Path(args.assessments_dir)
        seed_from_csvs(csv_dir, assessments_dir)
    elif args.command == "seed":
        init_db()
        csv_dir = Path(args.csv_dir)
        assessments_dir = Path(args.assessments_dir)
        seed_from_csvs(csv_dir, assessments_dir)
