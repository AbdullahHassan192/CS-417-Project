"""
TALASH M2 - Unit Tests for Analysis Functions

Tests all 20 M2 analysis functions with sample data.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.educational_analysis import (
    analyze_educational_progression,
    assess_institution_quality,
    detect_educational_gaps,
    extract_higher_education,
    extract_school_education,
    generate_educational_assessment,
    normalize_academic_scores,
    normalize_degree_levels,
)
from analysis.employment_analysis import (
    analyze_timeline_consistency,
    assess_career_progression,
    extract_professional_experience,
    generate_employment_assessment,
    justify_employment_gaps,
)
from analysis.missing_info_analysis import (
    detect_missing_information,
    draft_missing_info_email,
    generate_batch_missing_info_emails,
    generate_missing_info_summary,
)
import analysis.research_analysis as research_analysis
from analysis.research_analysis import generate_research_assessment
from analysis.summary_generation import (
    calculate_candidate_overall_score,
    generate_candidate_summary,
    generate_strengths_and_concerns,
)


# ── Sample data fixtures ───────────────────────────────────────

@pytest.fixture
def sample_education_df():
    return pd.DataFrame([
        {
            "candidate_id": "cand_test001",
            "education_stage": "sse",
            "degree_title_raw": "SSC",
            "degree_title_normalized": "SSC/SSE/Matric",
            "degree_level": "ssc",
            "specialization": None,
            "institution_name": "Govt High School",
            "board_or_university": "BISE Lahore",
            "admission_year": None,
            "completion_year": None,
            "passing_year": 2010,
            "score_raw": "85%",
            "score_type": "percentage",
            "score_value": 85.0,
            "score_scale": "100",
            "score_normalized_percentage": 85.0,
            "score_normalization_basis": "explicit_percentage",
        },
        {
            "candidate_id": "cand_test001",
            "education_stage": "hssc",
            "degree_title_raw": "HSSC Pre-Engineering",
            "degree_title_normalized": "HSSC/Intermediate",
            "degree_level": "hssc",
            "specialization": "Pre-Engineering",
            "institution_name": "Govt College",
            "board_or_university": "BISE Lahore",
            "admission_year": 2010,
            "completion_year": 2012,
            "passing_year": 2012,
            "score_raw": "78%",
            "score_type": "percentage",
            "score_value": 78.0,
            "score_scale": "100",
            "score_normalized_percentage": 78.0,
            "score_normalization_basis": "explicit_percentage",
        },
        {
            "candidate_id": "cand_test001",
            "education_stage": "ug",
            "degree_title_raw": "BS Computer Science",
            "degree_title_normalized": "Bachelor's",
            "degree_level": "bachelors",
            "specialization": "Computer Science",
            "institution_name": "COMSATS University Islamabad",
            "board_or_university": "COMSATS University Islamabad",
            "admission_year": 2012,
            "completion_year": 2016,
            "passing_year": 2016,
            "score_raw": "3.5/4.0",
            "score_type": "fraction",
            "score_value": 3.5,
            "score_scale": "4",
            "score_normalized_percentage": 87.5,
            "score_normalization_basis": "value_divided_by_scale",
        },
        {
            "candidate_id": "cand_test001",
            "education_stage": "pg",
            "degree_title_raw": "MS Computer Science",
            "degree_title_normalized": "Master's",
            "degree_level": "masters",
            "specialization": "Computer Science",
            "institution_name": "NUST Islamabad",
            "board_or_university": "NUST",
            "admission_year": 2017,
            "completion_year": 2019,
            "passing_year": 2019,
            "score_raw": "3.8/4.0",
            "score_type": "fraction",
            "score_value": 3.8,
            "score_scale": "4",
            "score_normalized_percentage": 95.0,
            "score_normalization_basis": "value_divided_by_scale",
        },
    ])


@pytest.fixture
def sample_experience_df():
    return pd.DataFrame([
        {
            "candidate_id": "cand_test001",
            "post_job_title": "Software Engineer",
            "organization": "TechCorp Pakistan",
            "location": "Islamabad",
            "duration": "2016-2017",
            "start_year": 2016,
            "end_year": 2017,
        },
        {
            "candidate_id": "cand_test001",
            "post_job_title": "Senior Software Engineer",
            "organization": "DataSoft",
            "location": "Lahore",
            "duration": "2019-2022",
            "start_year": 2019,
            "end_year": 2022,
        },
        {
            "candidate_id": "cand_test001",
            "post_job_title": "Lead Developer",
            "organization": "InnoTech",
            "location": "Islamabad",
            "duration": "2022-Present",
            "start_year": 2022,
            "end_year": None,
        },
    ])


@pytest.fixture
def sample_candidates_df():
    return pd.DataFrame([
        {
            "candidate_id": "cand_test001",
            "source_file": "test_cv.pdf",
            "full_name": "Ahmed Khan",
            "date_of_birth": "1995-03-15",
            "nationality": "Pakistani",
            "marital_status": "Single",
            "current_salary": None,
            "expected_salary": None,
            "present_employment": "Lead Developer at InnoTech",
            "post_applied_for": "Assistant Professor",
        },
    ])


# ── Educational Analysis Tests ─────────────────────────────────

class TestEducationalAnalysis:

    def test_extract_school_education(self, sample_education_df):
        records = extract_school_education(sample_education_df)
        assert len(records) == 2
        assert records[0]["degree_level"] in ("ssc", "sse")
        assert records[1]["degree_level"] == "hssc"

    def test_extract_higher_education(self, sample_education_df):
        records = extract_higher_education(sample_education_df)
        assert len(records) == 2
        assert any(r["degree_level"] == "bachelors" for r in records)
        assert any(r["degree_level"] == "masters" for r in records)

    def test_normalize_degree_levels_bs(self):
        result = normalize_degree_levels("BS Computer Science")
        assert result["normalized"] == "ug"

    def test_normalize_degree_levels_phd(self):
        result = normalize_degree_levels("PhD Electrical Engineering")
        assert result["normalized"] == "phd"

    def test_normalize_degree_levels_matric(self):
        result = normalize_degree_levels("Matric")
        assert result["normalized"] == "ssc"

    def test_normalize_degree_levels_none(self):
        result = normalize_degree_levels(None)
        assert result["raw"] is None

    def test_normalize_academic_scores_percentage(self):
        result = normalize_academic_scores("85%", "percentage")
        assert result["normalized_percentage"] == 85.0

    def test_normalize_academic_scores_cgpa(self):
        result = normalize_academic_scores(None, None, 3.5, "4.0")
        assert result["normalized_percentage"] == 87.5

    def test_normalize_academic_scores_fraction(self):
        result = normalize_academic_scores("3.8/4.0")
        assert result["normalized_percentage"] == 95.0

    def test_assess_institution_quality(self):
        result = assess_institution_quality("NUST Islamabad")
        assert result["ranking_status"] == "found"
        assert result["institution_name"] == "NUST Islamabad"
        assert result["qs_rank"] is not None
        assert result["ranking_source"] in ("llm+fallback", "fallback")

    def test_assess_institution_quality_not_found(self):
        result = assess_institution_quality("Unknown Institute of Placeholder City")
        assert result["ranking_status"] == "not_found"
        assert result["qs_display"] == "Not Found"
        assert result["the_display"] == "Not Found"

    def test_assess_institution_quality_no_harvard_false_match(self):
        result = assess_institution_quality("Hamdard University Karachi")
        matched_name = (result.get("matched_name") or "").lower()
        assert "harvard" not in matched_name

    def test_assess_institution_quality_llm_preferred(self):
        result = assess_institution_quality(
            "Hamdard University Karachi",
            llm_qs_rank="901",
            llm_the_rank="1201",
        )
        assert result["ranking_source"] == "llm"
        assert result["qs_rank"] == 901
        assert result["the_rank"] == 1201

    def test_analyze_educational_progression(self, sample_education_df):
        school = extract_school_education(sample_education_df)
        higher = extract_higher_education(sample_education_df)
        all_records = school + higher
        result = analyze_educational_progression(all_records)
        assert result["progression_score"] > 0
        assert result["performance_trend"] in ("improving", "stable", "declining", "variable")

    def test_detect_educational_gaps(self, sample_education_df):
        school = extract_school_education(sample_education_df)
        higher = extract_higher_education(sample_education_df)
        all_records = school + higher
        gaps = detect_educational_gaps(all_records)
        assert isinstance(gaps, list)
        # Sample has HSSC 2012 -> UG 2016 and UG 2016 -> PG 2019; no excess gap.
        assert len(gaps) == 0

    def test_detect_educational_gaps_excess_only(self):
        records = [
            {"degree_level": "hssc", "passing_year": 2006, "completion_year": 2006},
            {"degree_level": "ug", "passing_year": 2011, "completion_year": 2011},
        ]
        gaps = detect_educational_gaps(records)
        assert len(gaps) == 1
        assert gaps[0]["duration_years"] == 1.0
        assert gaps[0]["start_date"] == 2010
        assert gaps[0]["end_date"] == 2011

    def test_detect_educational_gaps_justified_by_professional_activity(self):
        records = [
            {"degree_level": "hssc", "passing_year": 2006, "completion_year": 2006},
            {"degree_level": "ug", "passing_year": 2011, "completion_year": 2011},
        ]
        exp = [
            {
                "post_job_title": "Lecturer",
                "organization": "XYZ University",
                "start_year": 2010,
                "end_year": 2011,
            }
        ]
        gaps = detect_educational_gaps(records, exp)
        assert len(gaps) == 1
        assert gaps[0]["justified_by_experience"] is True
        assert gaps[0]["status"] == "Justified"

    def test_generate_educational_assessment(self, sample_education_df, sample_experience_df):
        result = generate_educational_assessment(sample_education_df, sample_experience_df)
        assert "overall_educational_strength" in result
        assert result["overall_educational_strength"] >= 0
        assert result["highest_qualification_level"] in ("masters", "pg")
        assert result["narrative_summary"]
        for rec in result.get("school_records", []):
            assert rec.get("institution_ranking") is None

    def test_empty_education(self):
        result = generate_educational_assessment(pd.DataFrame())
        assert result["overall_educational_strength"] == 0.0


# ── Employment Analysis Tests ──────────────────────────────────

class TestEmploymentAnalysis:

    def test_extract_professional_experience(self, sample_experience_df):
        records = extract_professional_experience(sample_experience_df)
        assert len(records) == 3
        assert records[0]["start_year"] <= records[1]["start_year"]

    def test_analyze_timeline_consistency(self, sample_experience_df):
        records = extract_professional_experience(sample_experience_df)
        result = analyze_timeline_consistency(records)
        assert "timeline_consistency_score" in result
        assert isinstance(result["overlaps"], list)
        assert isinstance(result["gaps"], list)

    def test_assess_career_progression(self, sample_experience_df):
        records = extract_professional_experience(sample_experience_df)
        result = assess_career_progression(records)
        assert result["seniority_trajectory"] in ("ascending", "stable", "declining", "variable")

    def test_justify_employment_gaps(self):
        gaps = [{"gap_start_year": 2017, "gap_end_year": 2019, "duration_months": 24}]
        edu = [{"admission_year": 2017, "completion_year": 2019, "degree_title_raw": "MS CS", "institution_name": "NUST"}]
        result = justify_employment_gaps(gaps, edu)
        assert len(result) == 1
        assert result[0]["justification_type"] == "education"

    def test_justify_employment_gaps_with_missing_admission_year(self):
        gaps = [{"gap_start_year": 2015, "gap_end_year": 2023, "duration_months": 96}]
        edu = [{"admission_year": None, "completion_year": 2019, "passing_year": 2019, "degree_title_raw": "MS CS", "institution_name": "NUST"}]
        result = justify_employment_gaps(gaps, edu)
        assert len(result) == 1
        assert result[0]["justification_type"] == "education"

    def test_generate_employment_assessment(self, sample_experience_df, sample_education_df):
        result = generate_employment_assessment(sample_experience_df, sample_education_df)
        assert result["total_years_of_experience"] > 0
        assert result["overall_professional_strength"] >= 0
        assert result["narrative_summary"]

    def test_generate_employment_assessment_no_double_count_on_overlaps(self):
        exp = pd.DataFrame([
            {
                "candidate_id": "cand_test001",
                "post_job_title": "Engineer",
                "organization": "A",
                "start_year": 2015,
                "end_year": 2018,
            },
            {
                "candidate_id": "cand_test001",
                "post_job_title": "Consultant",
                "organization": "B",
                "start_year": 2017,
                "end_year": 2023,
            },
        ])
        result = generate_employment_assessment(exp)
        # Unique span is 2015-2023 = 8 years (not 9).
        assert result["total_years_of_experience"] == 8.0

    def test_empty_experience(self):
        result = generate_employment_assessment(pd.DataFrame())
        assert result["total_years_of_experience"] == 0.0


# ── Missing Info Tests ─────────────────────────────────────────

class TestMissingInfoAnalysis:

    def test_detect_missing_information(self, sample_candidates_df, sample_education_df, sample_experience_df):
        data = {
            "candidates": sample_candidates_df,
            "education": sample_education_df,
            "experience": sample_experience_df,
        }
        fields = detect_missing_information(data)
        assert isinstance(fields, list)
        # Some fields should be missing (e.g., current_salary)
        assert any(f["field_name"] == "current_salary" for f in fields)

    def test_generate_missing_info_summary(self):
        fields = [
            {"section": "personal", "field_name": "email", "severity": "critical", "missing_detail": "Missing email", "impact": "test"},
            {"section": "education", "field_name": "score", "severity": "important", "missing_detail": "Missing score", "impact": "test"},
        ]
        result = generate_missing_info_summary(fields)
        assert result["total_missing_fields"] == 2
        assert result["critical_count"] == 1
        assert result["completeness_percentage"] < 100

    def test_draft_missing_info_email(self):
        summary = {
            "total_missing_fields": 2,
            "fields_by_severity": {
                "critical": [{"missing_detail": "Missing email", "impact": "Required"}],
                "important": [{"missing_detail": "Missing score"}],
                "useful": [],
            },
        }
        result = draft_missing_info_email("Ahmed Khan", "ahmed@test.com", summary)
        assert "Ahmed Khan" in result["body"]
        assert result["tone"] == "professional"
        assert result["recipient"] == "ahmed@test.com"
        assert "(Reason:" not in result["body"]

    def test_generate_batch_emails(self):
        candidates = [
            {"candidate_name": "Test", "candidate_email": "t@t.com", "missing_summary": {"total_missing_fields": 1, "critical_count": 1, "important_count": 0, "fields_by_severity": {"critical": [{"missing_detail": "test", "impact": "test"}], "important": [], "useful": []}}},
        ]
        result = generate_batch_missing_info_emails(candidates)
        assert result["batch_summary"]["total_emails_drafted"] == 1


# ── Summary Generation Tests ──────────────────────────────────

class TestSummaryGeneration:

    def test_calculate_overall_score(self):
        result = calculate_candidate_overall_score(
            educational_strength=80,
            professional_strength=75,
            completeness_score=90,
            basic_skill_relevance=60,
        )
        assert result["overall_score"] > 0
        assert result["tier"] in ("excellent", "very_good", "good", "fair", "below_average")
        # 80*0.3 + 75*0.35 + 90*0.15 + 60*0.20 = 24+26.25+13.5+12 = 75.75
        assert abs(result["overall_score"] - 75.8) < 0.5

    def test_score_tier_classification(self):
        assert calculate_candidate_overall_score(90, 90, 90, 90)["tier"] == "excellent"
        assert calculate_candidate_overall_score(50, 50, 50, 50)["tier"] == "fair"
        assert calculate_candidate_overall_score(20, 20, 20, 20)["tier"] == "below_average"

    def test_generate_strengths_and_concerns(self):
        edu = {"overall_educational_strength": 85, "academic_performance_level": "excellent", "highest_qualification_level": "phd", "performance_trend": "improving", "average_score": 90, "academic_consistency_score": 90, "gaps": []}
        emp = {"overall_professional_strength": 70, "total_years_of_experience": 8, "seniority_trajectory": "ascending", "career_growth_rate": "strong", "employment_continuity_score": 90, "justified_gaps": [], "timeline_anomalies": []}
        missing = {"completeness_percentage": 85, "critical_count": 0}
        result = generate_strengths_and_concerns(edu, emp, missing)
        assert len(result["strengths"]) <= 3
        assert len(result["concerns"]) <= 3

    def test_generate_candidate_summary(self):
        pi = {"candidate_id": "cand_test", "full_name": "Test User", "post_applied_for": "Lecturer"}
        edu = {"overall_educational_strength": 80, "highest_qualification_level": "pg", "academic_performance_level": "good", "average_score": 75, "institution_quality_average": None, "educational_continuity_score": 90, "narrative_summary": "Test narrative."}
        emp = {"overall_professional_strength": 70, "total_years_of_experience": 5, "experience_level": "mid_level", "seniority_trajectory": "ascending", "employment_continuity_score": 85, "experience_records": [{"post_job_title": "Engineer", "organization": "Corp"}], "narrative_summary": "Emp narrative."}
        missing = {"completeness_percentage": 80, "critical_count": 0, "total_missing_fields": 3}
        result = generate_candidate_summary(pi, edu, emp, missing)
        assert result["candidate_name"] == "Test User"
        assert result["overall_score"] > 0
        assert result["recommendation"]


class TestResearchAnalysis:

    def test_generate_research_assessment_evidence_backed(self, monkeypatch):
        monkeypatch.setenv("TALASH_RESEARCH_EXTERNAL_VERIFY", "false")

        def fake_ref(issn, venue_name):
            if issn == "1234-5678" or (venue_name and "journal of ai" in venue_name.lower()):
                return {
                    "quartile": "Q1",
                    "impact_factor": 4.3,
                    "wos_indexed": True,
                    "scopus_indexed": True,
                }
            return None

        monkeypatch.setattr(research_analysis, "_lookup_journal_reference", fake_ref)

        pubs = pd.DataFrame([
            {
                "paper_title": "Graph Neural Networks for Fraud Detection",
                "publication_type": "journal",
                "authors": "Ayesha Malik*, Bilal Khan",
                "author_count": 2,
                "candidate_author_position": 1,
                "journal_name": "Journal of AI Systems",
                "venue_name": "Journal of AI Systems",
                "issn": "1234-5678",
                "doi": "10.1234/example.doi",
                "publisher": "Elsevier",
                "publication_year": 2023,
                "quartile_reported": "Q1",
                "wos_indexed_reported": "true",
                "scopus_indexed_reported": "true",
            },
            {
                "paper_title": "A Lightweight Security Architecture for IoT",
                "publication_type": "conference",
                "authors": "Ayesha Malik, Hamza Tariq, Noor Ali",
                "author_count": 3,
                "candidate_author_position": 1,
                "conference_name": "28th IEEE International Conference on IoT",
                "venue_name": "28th IEEE International Conference on IoT",
                "publisher": "IEEE",
                "conference_rank_reported": "A",
                "conference_series_edition": "28th",
                "proceedings_indexed_in": "IEEE Xplore, Scopus",
                "publication_year": 2022,
            },
        ])

        result = generate_research_assessment(
            publications_df=pubs,
            books_df=pd.DataFrame(),
            patents_df=pd.DataFrame(),
            candidate_name="Ayesha Malik",
        )

        assert result["total_publications"] == 2
        assert result["journal_analysis"]["total_journal_papers"] == 1
        assert result["conference_analysis"]["total_conference_papers"] == 1
        assert result["publication_analysis"]["q1_count"] >= 1
        assert "recruiter_summary" in result
        assert result["recruiter_summary"]["profile_level"] in {
            "strong_evidence_backed_profile",
            "moderate_profile_with_mixed_evidence",
            "limited_or_uncertain_profile",
        }
        assert result["publications"][0]["candidate_authorship_role"] in {
            "first_author",
            "first_and_corresponding_author",
        }
        assert result["publications"][0]["verification_confidence"] > 0

    def test_generate_research_assessment_handles_incomplete_publications(self, monkeypatch):
        monkeypatch.setenv("TALASH_RESEARCH_EXTERNAL_VERIFY", "false")
        monkeypatch.setattr(research_analysis, "_lookup_journal_reference", lambda issn, venue_name: None)

        pubs = pd.DataFrame([
            {
                "paper_title": "Unspecified Venue Study",
                "publication_type": "journal",
                "authors": "Ayesha Malik, Z. Ahmed",
                "author_count": 2,
                "publication_year": 2021,
            },
        ])

        result = generate_research_assessment(
            publications_df=pubs,
            books_df=pd.DataFrame(),
            patents_df=pd.DataFrame(),
            candidate_name="Ayesha Malik",
        )

        rec = result["publications"][0]
        assert rec["venue_quality_interpretation"] in {
            "unverified_venue",
            "insufficient_evidence",
            "predatory_risk_indicators",
        }
        assert "doi_missing" in rec["evidence_gaps"]
        assert "issn_missing" in rec["evidence_gaps"]
        assert result["journal_analysis"]["verification_coverage"] >= 0

    def test_topic_variability_and_collaboration_depth(self, monkeypatch):
        monkeypatch.setenv("TALASH_RESEARCH_EXTERNAL_VERIFY", "false")
        monkeypatch.setattr(research_analysis, "_lookup_journal_reference", lambda issn, venue_name: None)

        pubs = pd.DataFrame([
            {
                "paper_title": "Deep Learning for Medical Image Segmentation",
                "publication_type": "journal",
                "authors": "Ayesha Malik, Bilal Khan, Sara Noor",
                "author_count": 3,
                "candidate_author_position": 1,
                "venue_name": "Medical AI Journal",
                "publication_year": 2020,
                "abstract": "We propose a neural network based segmentation model for MRI images.",
                "keywords": "deep learning, segmentation, medical image",
            },
            {
                "paper_title": "Intrusion Detection in IoT Networks using Machine Learning",
                "publication_type": "conference",
                "authors": "Ayesha Malik, Bilal Khan, Hamza Tariq",
                "author_count": 3,
                "candidate_author_position": 2,
                "venue_name": "12th International Conference on IoT Security",
                "conference_series_edition": "12th",
                "publication_year": 2022,
                "abstract": "A security model for IoT network anomaly detection.",
                "keywords": "iot, intrusion detection, security, machine learning",
            },
            {
                "paper_title": "Curriculum Design for AI Ethics in Engineering Education",
                "publication_type": "journal",
                "authors": "Ayesha Malik, Zara Ali",
                "author_count": 2,
                "candidate_author_position": 1,
                "venue_name": "Engineering Education Review",
                "publication_year": 2024,
                "abstract": "This work studies curriculum and pedagogy for AI ethics education.",
                "keywords": "education, curriculum, ai ethics",
            },
        ])

        result = generate_research_assessment(
            publications_df=pubs,
            books_df=pd.DataFrame(),
            patents_df=pd.DataFrame(),
            candidate_name="Ayesha Malik",
        )

        tv = result["topic_variability"]
        ca = result["coauthor_analysis"]
        assert tv["dominant_topic_area"] is not None
        assert len(tv["topic_percentages"]) >= 1
        assert len(tv["topic_clusters"]) >= 1
        assert tv["profile_classification"] in {
            "highly_specialized",
            "moderately_diversified",
            "strongly_interdisciplinary",
            "insufficient_data",
        }
        assert len(tv["variability_explanation"]) >= 1
        assert ca["total_unique_coauthors"] >= 2
        assert "leadership_pattern" in ca
        assert "collaboration_patterns" in ca
        assert ca["collaboration_score"] >= 0

    def test_books_and_patents_analysis_enriched(self, monkeypatch):
        monkeypatch.setenv("TALASH_RESEARCH_EXTERNAL_VERIFY", "false")
        monkeypatch.setattr(research_analysis, "_lookup_journal_reference", lambda issn, venue_name: None)

        books = pd.DataFrame([
            {
                "book_title": "Applied Machine Learning for Engineers",
                "authors": "Ayesha Malik, Bilal Khan",
                "candidate_authorship_role": "lead_author",
                "isbn": "9780132350884",
                "publisher": "Pearson",
                "publication_year": 2021,
                "url": "https://example.com/book",
            },
            {
                "book_title": "Intro to Data Ethics",
                "authors": "Ayesha Malik",
                "candidate_authorship_role": "sole_author",
                "isbn": "invalid-isbn",
                "publisher": "Independently Published",
                "publication_year": 2023,
            },
        ])
        patents = pd.DataFrame([
            {
                "patent_title": "IoT Based Smart Irrigation Device",
                "patent_number": "US 1234567",
                "inventors": "Ayesha Malik; Hamza Tariq",
                "candidate_inventor_role": "lead_inventor",
                "filing_country": "US",
                "filing_year": 2022,
                "url": "https://patents.google.com/patent/US1234567",
            },
            {
                "patent_title": "AI Risk Scoring System (Pending Application)",
                "patent_number": "",
                "inventors": "Ayesha Malik; Sara Noor",
                "candidate_inventor_role": "co_inventor",
                "filing_country": "PK",
                "filing_year": 2024,
            },
        ])

        result = generate_research_assessment(
            publications_df=pd.DataFrame(),
            books_df=books,
            patents_df=patents,
            candidate_name="Ayesha Malik",
        )

        ba = result["books_analysis"]
        pa = result["patents_analysis"]
        assert ba["book_count"] == 2
        assert "authorship_distribution" in ba
        assert ba["publisher_quality_interpretation"] in {
            "mostly_academic_publishers",
            "mixed_publishers",
            "limited_publisher_evidence",
        }
        assert pa["patent_count"] == 2
        assert pa["verified_patent_count"] >= 0
        assert pa["research_translation_capability"] in {"strong", "moderate", "limited"}
        assert "missing_evidence_summary" in result
        assert "counts" in result["missing_evidence_summary"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
