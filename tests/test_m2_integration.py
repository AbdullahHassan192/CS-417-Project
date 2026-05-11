"""
TALASH M2 - Integration Tests

End-to-end tests for the M2 analysis pipeline.
"""
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.batch_processor import process_single_candidate
from analysis.data_loader import get_candidate_data, get_candidate_ids, load_all_csvs


@pytest.fixture
def sample_csv_dir(tmp_path):
    """Create sample M1 CSV outputs for testing."""
    # candidates.csv
    candidates = pd.DataFrame([
        {
            "candidate_id": "cand_integration01",
            "source_file": "integration_test.pdf",
            "full_name": "Integration Test User",
            "date_of_birth": "1990-01-01",
            "nationality": "Pakistani",
            "marital_status": "Single",
            "current_salary": None,
            "expected_salary": None,
            "present_employment": "Software Engineer",
            "post_applied_for": "Senior Developer",
        },
    ])
    candidates.to_csv(tmp_path / "candidates.csv", index=False)

    # education.csv
    education = pd.DataFrame([
        {
            "candidate_id": "cand_integration01",
            "education_stage": "sse",
            "degree_title_raw": "Matric",
            "degree_title_normalized": "SSC/SSE/Matric",
            "degree_level": "ssc",
            "specialization": None,
            "institution_name": "Test School",
            "board_or_university": "BISE",
            "admission_year": None,
            "completion_year": None,
            "passing_year": 2006,
            "score_raw": "80%",
            "score_type": "percentage",
            "score_value": 80.0,
            "score_scale": "100",
            "score_normalized_percentage": 80.0,
            "score_normalization_basis": "explicit_percentage",
        },
        {
            "candidate_id": "cand_integration01",
            "education_stage": "ug",
            "degree_title_raw": "BS Computer Science",
            "degree_title_normalized": "Bachelor's",
            "degree_level": "bachelors",
            "specialization": "Computer Science",
            "institution_name": "FAST NUCES",
            "board_or_university": "FAST NUCES",
            "admission_year": 2008,
            "completion_year": 2012,
            "passing_year": 2012,
            "score_raw": "3.2/4.0",
            "score_type": "fraction",
            "score_value": 3.2,
            "score_scale": "4",
            "score_normalized_percentage": 80.0,
            "score_normalization_basis": "value_divided_by_scale",
        },
    ])
    education.to_csv(tmp_path / "education.csv", index=False)

    # experience.csv
    experience = pd.DataFrame([
        {
            "candidate_id": "cand_integration01",
            "post_job_title": "Junior Developer",
            "organization": "StartupXYZ",
            "location": "Lahore",
            "duration": "2012-2015",
            "start_year": 2012,
            "end_year": 2015,
        },
        {
            "candidate_id": "cand_integration01",
            "post_job_title": "Software Engineer",
            "organization": "TechCorp",
            "location": "Islamabad",
            "duration": "2015-2020",
            "start_year": 2015,
            "end_year": 2020,
        },
    ])
    experience.to_csv(tmp_path / "experience.csv", index=False)

    # Empty tables
    pd.DataFrame(columns=["candidate_id"]).to_csv(tmp_path / "publications.csv", index=False)
    pd.DataFrame(columns=["candidate_id"]).to_csv(tmp_path / "books.csv", index=False)
    pd.DataFrame(columns=["candidate_id"]).to_csv(tmp_path / "patents.csv", index=False)

    return tmp_path


class TestIntegration:

    def test_full_pipeline(self, sample_csv_dir):
        """Test complete M1 CSV → M2 analysis pipeline."""
        # Load CSVs
        tables = load_all_csvs(sample_csv_dir)
        assert "candidates" in tables
        assert len(tables["candidates"]) == 1

        # Get candidate IDs
        ids = get_candidate_ids(tables)
        assert len(ids) == 1
        assert ids[0] == "cand_integration01"

        # Get single candidate data
        data = get_candidate_data(tables, ids[0])
        assert not data["candidates"].empty
        assert not data["education"].empty
        assert not data["experience"].empty

        # Run full analysis
        assessment = process_single_candidate(ids[0], data)

        # Verify structure
        assert assessment["candidate_id"] == "cand_integration01"
        assert "personal_info" in assessment
        assert "educational_assessment" in assessment
        assert "employment_assessment" in assessment
        assert "missing_info" in assessment
        assert "overall_score" in assessment
        assert "overall_tier" in assessment
        assert "strengths" in assessment
        assert "concerns" in assessment

        # Verify scores are reasonable
        assert 0 <= assessment["overall_score"] <= 100
        assert assessment["overall_tier"] in (
            "excellent", "very_good", "good", "fair", "below_average"
        )

        # Verify educational assessment
        edu = assessment["educational_assessment"]
        assert edu["highest_qualification_level"] in ("bachelors", "ug")
        assert edu["overall_educational_strength"] >= 0

        # Verify employment assessment
        emp = assessment["employment_assessment"]
        assert emp["total_years_of_experience"] > 0
        assert emp["overall_professional_strength"] >= 0

        # Verify JSON serializable
        json_str = json.dumps(assessment, default=str)
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert parsed["candidate_id"] == "cand_integration01"

    def test_missing_info_email_generation(self, sample_csv_dir):
        """Test that missing info emails are generated correctly."""
        tables = load_all_csvs(sample_csv_dir)
        ids = get_candidate_ids(tables)
        data = get_candidate_data(tables, ids[0])
        assessment = process_single_candidate(ids[0], data)

        if assessment.get("missing_info_email"):
            email = assessment["missing_info_email"]
            assert "subject" in email
            assert "body" in email
            assert "Integration Test User" in email["body"]
            assert email["tone"] == "professional"

    def test_empty_data_handling(self):
        """Test pipeline handles empty data gracefully."""
        tables = {
            "candidates": pd.DataFrame(columns=["candidate_id"]),
            "education": pd.DataFrame(columns=["candidate_id"]),
            "experience": pd.DataFrame(columns=["candidate_id"]),
            "publications": pd.DataFrame(columns=["candidate_id"]),
            "books": pd.DataFrame(columns=["candidate_id"]),
            "patents": pd.DataFrame(columns=["candidate_id"]),
        }
        ids = get_candidate_ids(tables)
        assert len(ids) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
