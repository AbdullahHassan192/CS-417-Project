"""
TALASH M3 - FastAPI Application

Main entry point for the M3 backend server.
Serves candidate assessment, jobs, analytics, and auth via REST API.

Usage:
  cd CS-417-Project
  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for M1 module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.database import init_db, SessionLocal
from backend.auth import seed_admin_user
from backend.routes.candidates import router as candidates_router
from backend.routes.auth import router as auth_router
from backend.routes.jobs import router as jobs_router
from backend.routes.analytics import router as analytics_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# FastAPI app
app = FastAPI(
    title="TALASH - Smart HR Recruitment System",
    description=(
        "Milestone 3 API: Full integrated system with auth, candidate assessment, "
        "jobs management, analytics, and candidate ranking."
    ),
    version="3.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(candidates_router)
app.include_router(jobs_router)
app.include_router(analytics_router)


@app.on_event("startup")
def startup_event():
    """Initialize database and seed admin user on startup."""
    init_db()
    db = SessionLocal()
    try:
        seed_admin_user(db)
    finally:
        db.close()
    logging.getLogger(__name__).info("TALASH M3 database initialized and admin seeded")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "TALASH M3 API",
        "version": "3.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """API health check."""
    csv_dir = settings.CSV_OUTPUT_DIR
    assessments_dir = settings.ASSESSMENTS_DIR

    return {
        "status": "healthy",
        "csv_output_dir": str(csv_dir),
        "csv_dir_exists": csv_dir.exists(),
        "assessments_dir": str(assessments_dir),
        "assessments_dir_exists": assessments_dir.exists(),
    }

