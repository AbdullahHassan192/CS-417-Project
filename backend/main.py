"""
TALASH M2 - FastAPI Application

Main entry point for the M2 backend server.
Serves candidate assessment data via REST API.

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
from backend.routes.candidates import router as candidates_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# FastAPI app
app = FastAPI(
    title="TALASH - Smart HR Recruitment System",
    description=(
        "Milestone 2 API: Candidate assessment, educational & employment "
        "profile analysis, missing information detection, and summary generation."
    ),
    version="2.0.0",
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
app.include_router(candidates_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "TALASH M2 API",
        "version": "2.0.0",
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
