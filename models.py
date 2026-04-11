from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


TABLE_COLUMNS: dict[str, list[str]] = {
    "candidates": [
        "candidate_id",
        "source_file",
        "full_name",
        "father_guardian_name",
        "spouse_name",
        "date_of_birth",
        "nationality",
        "marital_status",
        "current_salary",
        "expected_salary",
        "present_employment",
        "post_applied_for",
    ],
    "education": [
        "candidate_id",
        "education_stage",
        "degree_title_raw",
        "degree_title_normalized",
        "degree_level",
        "specialization",
        "institution_name",
        "board_or_university",
        "admission_year",
        "completion_year",
        "passing_year",
        "score_raw",
        "score_type",
        "score_value",
        "score_scale",
        "score_normalized_percentage",
        "score_normalization_basis",
    ],
    "experience": [
        "candidate_id",
        "post_job_title",
        "organization",
        "location",
        "duration",
        "start_year",
        "end_year",
    ],
    "publications": [
        "candidate_id",
        "paper_title",
        "publication_type",
        "authors",
        "author_count",
        "candidate_author_position",
        "candidate_authorship_role",
        "candidate_is_first_author",
        "candidate_is_corresponding_author",
        "venue_name",
        "journal_name",
        "conference_name",
        "published_in",
        "publisher",
        "issn",
        "isbn",
        "doi",
        "volume",
        "issue",
        "pages",
        "impact_factor_reported",
        "quartile_reported",
        "wos_indexed_reported",
        "scopus_indexed_reported",
        "conference_rank_reported",
        "conference_series_edition",
        "proceedings_indexed_in",
        "date_text",
        "publication_year",
        "url",
        "verification_notes",
    ],
    "books": [
        "candidate_id",
        "book_title",
        "authors",
        "candidate_authorship_role",
        "isbn",
        "publisher",
        "publication_year",
        "url",
    ],
    "patents": [
        "candidate_id",
        "patent_number",
        "patent_title",
        "inventors",
        "candidate_inventor_role",
        "filing_country",
        "date_text",
        "filing_year",
        "url",
    ],
}


class EducationItem(BaseModel):
    degree_title: Optional[str] = Field(default=None, description="Degree title as written")
    degree_title_normalized_hint: Optional[str] = Field(
        default=None,
        description="Canonical degree title hint, e.g., SSC/HSSC/BS/MS/MPhil/PhD",
    )
    degree_level_hint: Optional[str] = Field(
        default=None,
        description="Degree level hint: ssc/hssc/ug/pg/mphil/phd/postdoc/other",
    )
    education_stage_hint: Optional[str] = Field(
        default=None,
        description="Education stage hint: sse/hssc/ug/pg/doctorate/postdoc/other",
    )
    specialization: Optional[str] = Field(default=None, description="Specialization/discipline")
    score_or_cgpa: Optional[str] = Field(default=None, description="Marks/CGPA/%/grade/division")
    passing_year: Optional[str] = Field(default=None, description="Passing/completion year")
    admission_year: Optional[str] = Field(default=None, description="Admission/start year")
    completion_year: Optional[str] = Field(default=None, description="Completion/end year")
    institution_name: Optional[str] = Field(default=None, description="University/institute")
    board_name: Optional[str] = Field(default=None, description="Board name for school records")


class ExperienceItem(BaseModel):
    post_job_title: Optional[str] = Field(default=None, description="Post/Job Title")
    organization: Optional[str] = Field(default=None, description="Organization")
    location: Optional[str] = Field(default=None, description="Location")
    duration: Optional[str] = Field(default=None, description="Duration text")


class PublicationItem(BaseModel):
    paper_title: Optional[str] = Field(default=None, description="Paper title")
    publication_type: Optional[str] = Field(
        default=None,
        description="journal/conference/other where explicitly known",
    )
    authors: Optional[str] = Field(default=None, description="Author list")
    published_in: Optional[str] = Field(default=None, description="Venue as reported")
    journal_name: Optional[str] = Field(default=None, description="Journal name if explicit")
    conference_name: Optional[str] = Field(default=None, description="Conference name if explicit")
    publisher: Optional[str] = Field(default=None, description="Publisher/proceedings source")
    issn: Optional[str] = Field(default=None, description="ISSN if present")
    isbn: Optional[str] = Field(default=None, description="ISBN if present")
    doi: Optional[str] = Field(default=None, description="DOI if present")
    volume: Optional[str] = Field(default=None, description="Volume")
    issue: Optional[str] = Field(default=None, description="Issue")
    pages: Optional[str] = Field(default=None, description="Pages")
    impact_factor_reported: Optional[str] = Field(default=None, description="IF as reported in CV")
    quartile_reported: Optional[str] = Field(default=None, description="Quartile as reported in CV")
    wos_indexed_reported: Optional[str] = Field(default=None, description="WoS status as reported")
    scopus_indexed_reported: Optional[str] = Field(default=None, description="Scopus status as reported")
    conference_rank_reported: Optional[str] = Field(default=None, description="A*/A/B rank as reported")
    conference_series_edition: Optional[str] = Field(default=None, description="e.g., 13th International")
    proceedings_indexed_in: Optional[str] = Field(default=None, description="IEEE Xplore/ACM/Springer/etc")
    date_text: Optional[str] = Field(default=None, description="Date or month-year text")
    publication_year: Optional[str] = Field(default=None, description="Publication year")
    url: Optional[str] = Field(default=None, description="Online link")


class BookItem(BaseModel):
    book_title: Optional[str] = Field(default=None, description="Book title")
    authors: Optional[str] = Field(default=None, description="Authors")
    isbn: Optional[str] = Field(default=None, description="ISBN")
    publisher: Optional[str] = Field(default=None, description="Publisher")
    publication_year: Optional[str] = Field(default=None, description="Publication year")
    url: Optional[str] = Field(default=None, description="Link")


class PatentItem(BaseModel):
    patent_number: Optional[str] = Field(default=None, description="Patent number")
    patent_title: Optional[str] = Field(default=None, description="Patent title")
    inventors: Optional[str] = Field(default=None, description="Inventors list")
    date_text: Optional[str] = Field(default=None, description="Date text")
    filing_year: Optional[str] = Field(default=None, description="Filing year")
    filing_country: Optional[str] = Field(default=None, description="Country of filing")
    url: Optional[str] = Field(default=None, description="Verification link")


class PersonalInformation(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Full Name")
    father_guardian_name: Optional[str] = Field(default=None, description="Father/Guardian Name")
    spouse_name: Optional[str] = Field(default=None, description="Spouse Name")
    date_of_birth: Optional[str] = Field(default=None, description="Date of Birth")
    nationality: Optional[str] = Field(default=None, description="Nationality")
    marital_status: Optional[str] = Field(default=None, description="Marital Status")
    current_salary: Optional[str] = Field(default=None, description="Current Salary")
    expected_salary: Optional[str] = Field(default=None, description="Expected Salary")
    present_employment: Optional[str] = Field(default=None, description="Current employment summary")
    post_applied_for: Optional[str] = Field(default=None, description="Post Applied For")


class CandidateExtraction(BaseModel):
    personal_information: PersonalInformation
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    publications: list[PublicationItem] = Field(default_factory=list)
    books: list[BookItem] = Field(default_factory=list)
    patents: list[PatentItem] = Field(default_factory=list)


@dataclass
class ExtractionResult:
    candidate_id: str
    source_file: str
    data: CandidateExtraction
