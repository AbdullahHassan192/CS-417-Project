"""
TALASH M3 - Database Setup (SQLite via SQLAlchemy)

Creates all tables and provides session management.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

_project_root = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_project_root / 'talash.db'}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

# Enable WAL mode and foreign keys for SQLite
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── ORM Models ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="recruiter")
    created_at = Column(DateTime, server_default=func.now())


class Candidate(Base):
    __tablename__ = "candidates"
    candidate_id = Column(String(50), primary_key=True)
    source_file = Column(String(500))
    full_name = Column(String(255))
    father_guardian_name = Column(String(255))
    date_of_birth = Column(String(50))
    nationality = Column(String(100))
    marital_status = Column(String(50))
    present_employment = Column(String(255))
    post_applied_for = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    uploaded_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)
    overall_score = Column(Float, default=0.0)
    rank_position = Column(Integer)

    education = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    experience = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="candidate", cascade="all, delete-orphan")
    books = relationship("Book", back_populates="candidate", cascade="all, delete-orphan")
    patents = relationship("Patent", back_populates="candidate", cascade="all, delete-orphan")
    analyses = relationship("CandidateAnalysis", back_populates="candidate", cascade="all, delete-orphan")
    missing_info_logs = relationship("MissingInfoLog", back_populates="candidate", cascade="all, delete-orphan")
    pipeline_statuses = relationship("PipelineStatus", back_populates="candidate", cascade="all, delete-orphan")


class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    education_stage = Column(String(50))
    degree_title_raw = Column(String(255))
    degree_title_normalized = Column(String(100))
    degree_level = Column(String(50))
    specialization = Column(String(255))
    institution_name = Column(String(500))
    board_or_university = Column(String(500))
    admission_year = Column(Integer)
    completion_year = Column(Integer)
    passing_year = Column(Integer)
    score_raw = Column(String(100))
    score_type = Column(String(50))
    score_value = Column(Float)
    score_scale = Column(Float)
    score_normalized_percentage = Column(Float)

    candidate = relationship("Candidate", back_populates="education")


class Experience(Base):
    __tablename__ = "experience"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    post_job_title = Column(String(255))
    organization = Column(String(500))
    location = Column(String(255))
    duration = Column(String(100))
    start_year = Column(Integer)
    end_year = Column(Integer)
    employment_type = Column(String(50))

    candidate = relationship("Candidate", back_populates="experience")


class Publication(Base):
    __tablename__ = "publications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    paper_title = Column(Text)
    publication_type = Column(String(50))
    authors = Column(Text)
    author_count = Column(Integer)
    candidate_author_position = Column(Integer)
    candidate_authorship_role = Column(String(50))
    candidate_is_first_author = Column(Boolean)
    venue_name = Column(String(500))
    journal_name = Column(String(500))
    conference_name = Column(String(500))
    issn = Column(String(50))
    doi = Column(String(255))
    impact_factor_reported = Column(Float)
    impact_factor_verified = Column(Float)
    quartile_reported = Column(String(10))
    quartile_verified = Column(String(10))
    wos_indexed_reported = Column(Boolean)
    wos_indexed_verified = Column(Boolean)
    scopus_indexed_reported = Column(Boolean)
    scopus_indexed_verified = Column(Boolean)
    conference_rank = Column(String(10))
    publication_year = Column(Integer)

    candidate = relationship("Candidate", back_populates="publications")


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    book_title = Column(Text)
    authors = Column(Text)
    candidate_authorship_role = Column(String(50))
    isbn = Column(String(50))
    publisher = Column(String(255))
    publication_year = Column(Integer)
    online_link = Column(Text)

    candidate = relationship("Candidate", back_populates="books")


class Patent(Base):
    __tablename__ = "patents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    patent_number = Column(String(100))
    patent_title = Column(Text)
    inventors = Column(Text)
    candidate_inventor_role = Column(String(50))
    filing_country = Column(String(100))
    filing_year = Column(Integer)
    verification_link = Column(Text)

    candidate = relationship("Candidate", back_populates="patents")


class CandidateAnalysis(Base):
    __tablename__ = "candidate_analysis"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    analysis_type = Column(String(100), nullable=False)
    analysis_json = Column(Text)  # JSON string
    generated_at = Column(DateTime, server_default=func.now())
    llm_summary = Column(Text)

    candidate = relationship("Candidate", back_populates="analyses")


class MissingInfoLog(Base):
    __tablename__ = "missing_info_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    missing_fields = Column(Text)  # JSON string
    draft_email = Column(Text)
    email_sent = Column(Boolean, default=False)
    flagged_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="missing_info_logs")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(50), primary_key=True)
    title = Column(String(255))
    department = Column(String(255))
    location = Column(String(255))
    employment_type = Column(String(50))
    description = Column(Text)
    required_skills = Column(Text)  # JSON string
    status = Column(String(50), default="active")
    created_at = Column(DateTime, server_default=func.now())

    alignments = relationship("JobAlignment", back_populates="job", cascade="all, delete-orphan")


class JobAlignment(Base):
    __tablename__ = "job_alignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=False, index=True)
    alignment_score = Column(Float)
    rank_position = Column(Integer)
    score_breakdown = Column(Text)  # JSON string
    computed_at = Column(DateTime, server_default=func.now())

    job = relationship("Job", back_populates="alignments")


class PipelineStatus(Base):
    __tablename__ = "pipeline_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=True)
    status = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50), ForeignKey("users.id"), nullable=True)
    notes = Column(Text)

    candidate = relationship("Candidate", back_populates="pipeline_statuses")


# ── DB helpers ──────────────────────────────────────────────────────────────

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def get_db():
    """FastAPI dependency for DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
