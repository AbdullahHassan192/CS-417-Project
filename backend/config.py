"""
TALASH M3 - Backend Configuration

Manages environment variables and application settings.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

# Load .env from project root (override=True ensures .env always wins over
# any stale env vars that may already be set in the shell process).
_project_root = Path(__file__).resolve().parent.parent
_env_file = _project_root / ".env"
_env_example = _project_root / ".env.example"

if _env_file.exists():
    load_dotenv(_env_file, override=True)
    _logger.debug("Loaded env from %s", _env_file)
elif _env_example.exists():
    load_dotenv(_env_example, override=True)
    _logger.debug("Loaded env from %s (fallback)", _env_example)
else:
    _logger.warning("No .env file found at %s", _env_file)


class Settings:
    """Application configuration loaded from environment."""

    # Paths
    PROJECT_ROOT: Path = _project_root
    CSV_OUTPUT_DIR: Path = Path(
        os.getenv("CSV_OUTPUT_DIR", str(_project_root / "output"))
    )
    ASSESSMENTS_DIR: Path = Path(
        os.getenv("ASSESSMENTS_DIR", str(_project_root / "data" / "candidates_assessments"))
    )
    INPUT_CVS_DIR: Path = Path(
        os.getenv("INPUT_CVS_DIR", str(_project_root / "data" / "input_cvs"))
    )

    # API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Frontend
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # JWT Auth (M3)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "talash-m3-secret-key-change-in-prod")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # Database (M3)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{_project_root / 'talash.db'}"
    )


settings = Settings()

# Warn loudly at startup if the API key is missing so it's obvious in logs
if not settings.GEMINI_API_KEY:
    _logger.warning(
        "GEMINI_API_KEY is not set! Expected .env at: %s", _env_file
    )
