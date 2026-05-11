"""
TALASH M3 - Full Research Profile Analysis

Research profile module focused on evidence-backed academic assessment:
- Journal publication quality and legitimacy
- Conference quality and maturity
- Authorship significance and collaboration structure
- Trend and productivity indicators
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus
from urllib.request import urlopen

import pandas as pd

from analysis.groq_fallback import (
    infer_publication_topics_with_groq,
)
from analysis.regex_rank_lookup import resolve_journal_rank_regex

logger = logging.getLogger(__name__)

_project_root = Path(__file__).resolve().parent.parent
_verification_cache_file = _project_root / "data" / "research_verification_cache.json"
_journal_ref_file = _project_root / "data" / "journal_indexing_reference.json"
_conference_ref_file = _project_root / "data" / "conference_rankings.json"

KNOWN_REPUTED_PUBLISHERS = {
    "ieee",
    "acm",
    "springer",
    "elsevier",
    "wiley",
    "taylor",
    "francis",
    "oxford university press",
    "cambridge university press",
    "nature",
    "sage",
    "mdpi",
}

PREDATORY_RISK_TERMS = {
    "global journal",
    "international journal of advanced",
    "open access international",
    "worldwide journal",
    "impact factor 7",
}

TOPIC_STOPWORDS = {
    "with", "from", "this", "that", "which", "their", "using", "based",
    "approach", "method", "study", "analysis", "paper", "results", "proposed",
    "model", "system", "data", "performance", "towards", "through", "using",
    "evaluation", "framework", "novel", "efficient", "application",
}

TOPIC_DOMAIN_KEYWORDS: Dict[str, set[str]] = {
    "artificial_intelligence_ml": {"machine", "learning", "deep", "neural", "ai", "classification", "prediction", "transformer"},
    "computer_vision": {"image", "vision", "segmentation", "detection", "video", "cnn", "object"},
    "nlp_text_mining": {"language", "text", "nlp", "sentiment", "token", "embedding", "translation"},
    "data_mining_analytics": {"mining", "analytics", "clustering", "pattern", "regression", "dataset", "feature"},
    "networks_security_iot": {"network", "security", "iot", "wireless", "intrusion", "crypt", "blockchain"},
    "software_systems": {"software", "architecture", "testing", "quality", "distributed", "microservice", "devops"},
    "hci_education": {"human", "interaction", "usability", "education", "learning", "curriculum", "pedagogy"},
    "control_robotics": {"robot", "control", "autonomous", "sensor", "actuator", "navigation"},
}

ACADEMIC_BOOK_PUBLISHER_TERMS = {
    "springer", "wiley", "elsevier", "cambridge university press", "oxford university press",
    "crc press", "taylor", "routledge", "sage", "pearson", "mcgraw", "ieee",
}
COMMERCIAL_BOOK_PUBLISHER_TERMS = {
    "packt", "oreilly", "manning", "apress", "amazon", "self", "independently published",
}
VANITY_BOOK_INDICATORS = {"authorhouse", "xlibris", "notion press", "lulu", "kindle direct", "self-published"}


def generate_research_assessment(
    publications_df: Optional[pd.DataFrame] = None,
    books_df: Optional[pd.DataFrame] = None,
    patents_df: Optional[pd.DataFrame] = None,
    candidate_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate full research profile analysis with grounded verification signals.
    """
    verification_cache = _load_verification_cache()

    publication_records = _build_publication_records(
        publications_df=publications_df,
        candidate_name=candidate_name,
        verification_cache=verification_cache,
    )
    _save_verification_cache(verification_cache)

    journal_records = [p for p in publication_records if p.get("publication_type_normalized") == "journal"]
    conference_records = [p for p in publication_records if p.get("publication_type_normalized") == "conference"]

    journal_analysis = _analyze_journal_publications(journal_records)
    conference_analysis = _analyze_conference_publications(conference_records)
    publication_analysis = _build_publication_analysis(
        publication_records,
        journal_analysis,
        conference_analysis,
    )
    coauthor_analysis = _analyze_coauthors(publication_records, candidate_name)
    topic_variability = _analyze_topic_variability(publication_records)
    books_analysis = _analyze_books(_build_book_records(books_df, candidate_name))
    patents_analysis = _analyze_patents(_build_patent_records(patents_df))

    overall_research_strength, score_breakdown = _compute_research_score(
        publication_analysis=publication_analysis,
        journal_analysis=journal_analysis,
        conference_analysis=conference_analysis,
        coauthor_analysis=coauthor_analysis,
        topic_variability=topic_variability,
        books_analysis=books_analysis,
        patents_analysis=patents_analysis,
    )

    narrative = _build_narrative(
        candidate_name=candidate_name,
        publication_analysis=publication_analysis,
        journal_analysis=journal_analysis,
        conference_analysis=conference_analysis,
        coauthor_analysis=coauthor_analysis,
        topic_variability=topic_variability,
        books_analysis=books_analysis,
        patents_analysis=patents_analysis,
    )
    recruiter_summary = _build_recruiter_summary(
        publication_analysis=publication_analysis,
        journal_analysis=journal_analysis,
        conference_analysis=conference_analysis,
        coauthor_analysis=coauthor_analysis,
        topic_variability=topic_variability,
        books_analysis=books_analysis,
        patents_analysis=patents_analysis,
    )
    missing_evidence = _summarize_missing_research_evidence(
        publications=publication_records,
        books=books_analysis.get("books", []),
        patents=patents_analysis.get("patents", []),
    )

    return {
        "overall_research_strength": round(overall_research_strength, 1),
        "research_score_breakdown": score_breakdown,
        "total_publications": len(publication_records),
        "total_books": books_analysis.get("book_count", 0),
        "total_patents": patents_analysis.get("patent_count", 0),
        "publications": publication_records,
        "books": books_analysis.get("books", []),
        "patents": patents_analysis.get("patents", []),
        "publication_analysis": publication_analysis,
        "journal_analysis": journal_analysis,
        "conference_analysis": conference_analysis,
        "coauthor_analysis": coauthor_analysis,
        "topic_variability": topic_variability,
        "books_analysis": books_analysis,
        "patents_analysis": patents_analysis,
        "missing_evidence_summary": missing_evidence,
        "recruiter_summary": recruiter_summary,
        "narrative_summary": narrative,
    }


def _build_publication_records(
    publications_df: Optional[pd.DataFrame],
    candidate_name: Optional[str],
    verification_cache: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if publications_df is None or publications_df.empty:
        return []

    records: List[Dict[str, Any]] = []
    for _, row in publications_df.iterrows():
        title = _safe(row.get("paper_title"))
        authors_raw = _safe(row.get("authors"), "")
        authors = _split_authors(authors_raw)
        author_count = _safe_int(row.get("author_count")) or len(authors) or 1
        position_reported = _safe_int(row.get("candidate_author_position"))
        position_inferred = _infer_author_position(candidate_name, authors)
        candidate_position = position_reported or position_inferred
        corresponding_flag = _infer_corresponding_flag(
            authors_raw=authors_raw,
            candidate_name=candidate_name,
            candidate_position=candidate_position,
        )
        authorship_role = _classify_authorship_role(
            candidate_position=candidate_position,
            author_count=author_count,
            corresponding=corresponding_flag,
        )

        pub_type = _normalize_publication_type(
            _safe(row.get("publication_type")),
            _safe(row.get("journal_name")),
            _safe(row.get("conference_name")),
            _safe(row.get("venue_name")),
        )
        doi = _normalize_doi(_safe(row.get("doi")))
        issn = _normalize_issn(_safe(row.get("issn")))
        venue_name = _safe(row.get("venue_name")) or _safe(row.get("journal_name")) or _safe(row.get("conference_name"))
        publisher = _safe(row.get("publisher"))
        year = _safe_int(row.get("publication_year"))
        abstract_text = _safe(row.get("abstract")) or _safe(row.get("summary")) or ""
        keywords_text = _safe(row.get("keywords")) or _safe(row.get("keyword")) or ""
        semantic_tokens = _tokenize_topic_text(
            " ".join(
                [
                    _safe(row.get("paper_title"), "") or "",
                    abstract_text,
                    keywords_text,
                    _safe(row.get("venue_name"), "") or "",
                    _safe(row.get("journal_name"), "") or "",
                    _safe(row.get("conference_name"), "") or "",
                ]
            )
        )
        domain_scores = _infer_topic_domains(semantic_tokens)

        verification = _verify_publication_metadata(
            doi=doi,
            issn=issn,
            venue_name=venue_name,
            publisher=publisher,
            verification_cache=verification_cache,
        )

        reported_scopus = _safe_bool(row.get("scopus_indexed_reported"))
        reported_wos = _safe_bool(row.get("wos_indexed_reported"))
        reported_if = _safe_float(row.get("impact_factor_reported"))
        reported_quartile = _normalize_quartile(_safe(row.get("quartile_reported")))

        indexed_status = _determine_indexing_status(
            verification=verification,
            reported_scopus=reported_scopus,
            reported_wos=reported_wos,
            reported_quartile=reported_quartile,
        )

        impact_factor = verification.get("impact_factor") or reported_if
        quartile = verification.get("quartile") or reported_quartile
        sjr_rank = _safe_int(row.get("sjr_rank"))
        ranking_source = "verified_or_reported"
        if pub_type == "journal" and (quartile is None or sjr_rank is None):
            journal_rank = resolve_journal_rank_regex(_safe(row.get("journal_name")) or venue_name or "")
            if quartile is None:
                quartile = _normalize_quartile((journal_rank or {}).get("quartile"))
            if sjr_rank is None:
                sjr_rank = _safe_int((journal_rank or {}).get("rank"))
            if journal_rank:
                ranking_source = "regex_journal_rank"

        publisher_credibility = _classify_publisher_credibility(
            publisher=verification.get("publisher") or publisher,
            venue_name=venue_name,
        )
        predatory_risk = _estimate_predatory_risk(
            venue_name=venue_name,
            publisher=verification.get("publisher") or publisher,
            has_doi=doi is not None,
            has_issn=issn is not None,
            indexed_status=indexed_status,
        )
        indexing_evidence = _build_indexing_evidence(
            verification=verification,
            reported_scopus=reported_scopus,
            reported_wos=reported_wos,
            reported_quartile=reported_quartile,
        )
        verification_confidence = _verification_confidence_score(
            verification=verification,
            indexing_status=indexed_status,
            doi=doi,
            issn=issn,
        )
        evidence_gaps = _evidence_gaps(
            verification=verification,
            indexing_status=indexed_status,
            doi=doi,
            issn=issn,
        )
        conference_rank = _resolve_core_rank({
            "conference_rank_reported": _safe(row.get("conference_rank_reported")),
            "conference_name": _safe(row.get("conference_name")),
            "venue_name": venue_name,
        })
        conference_series = _series_number({
            "conference_series_edition": _safe(row.get("conference_series_edition")),
            "conference_name": _safe(row.get("conference_name")),
            "venue_name": venue_name,
        })
        conference_maturity = _classify_conference_maturity(conference_series)
        conference_reputable = _is_reputable_proceedings({
            "publisher": verification.get("publisher") or publisher,
            "proceedings_indexed_in": _safe(row.get("proceedings_indexed_in")),
            "conference_name": _safe(row.get("conference_name")),
            "venue_name": venue_name,
        })
        venue_quality_interpretation = _interpret_venue_quality(
            publication_type=pub_type,
            indexing_status=indexed_status,
            quartile=quartile,
            impact_factor=impact_factor,
            predatory_risk=predatory_risk,
        )
        journal_legitimacy = _classify_journal_legitimacy(
            indexing_status=indexed_status,
            publisher_credibility=publisher_credibility,
            predatory_risk=predatory_risk,
            verification_confidence=verification_confidence,
        )
        contribution_significance = _authorship_significance(
            authorship_role=authorship_role,
            author_count=author_count,
        )

        record = {
            "paper_title": title,
            "publication_type": _safe(row.get("publication_type")),
            "publication_type_normalized": pub_type,
            "publication_year": year,
            "authors": authors_raw,
            "authors_list": authors,
            "author_count": author_count,
            "candidate_author_position": candidate_position,
            "candidate_authorship_role": authorship_role,
            "candidate_is_first_author": authorship_role in {"first_author", "first_and_corresponding_author", "sole_author"},
            "candidate_is_corresponding_author": corresponding_flag,
            "venue_name": venue_name,
            "journal_name": _safe(row.get("journal_name")),
            "conference_name": _safe(row.get("conference_name")),
            "issn": issn,
            "doi": doi,
            "publisher": verification.get("publisher") or publisher,
            "volume": _safe(row.get("volume")),
            "issue": _safe(row.get("issue")),
            "pages": _safe(row.get("pages")),
            "conference_rank_reported": _safe(row.get("conference_rank_reported")),
            "conference_rank_resolved": conference_rank,
            "conference_series_edition": _safe(row.get("conference_series_edition")),
            "conference_series_number": conference_series,
            "conference_maturity": conference_maturity,
            "proceedings_indexed_in": _safe(row.get("proceedings_indexed_in")),
            "conference_reputable_proceedings": conference_reputable,
            "scopus_indexed_reported": reported_scopus,
            "wos_indexed_reported": reported_wos,
            "indexing_status": indexed_status,
            "indexing_evidence": indexing_evidence,
            "impact_factor": impact_factor,
            "quartile": quartile,
            "sjr_rank": sjr_rank,
            "ranking_source": ranking_source,
            "publisher_credibility": publisher_credibility,
            "predatory_risk": predatory_risk,
            "journal_legitimacy_status": journal_legitimacy,
            "verification_confidence": verification_confidence,
            "evidence_gaps": evidence_gaps,
            "verification": verification,
            "candidate_contribution_significance": contribution_significance,
            "abstract_text": abstract_text,
            "keywords_text": keywords_text,
            "semantic_tokens": semantic_tokens,
            "domain_scores": domain_scores,
            "dominant_domain": _dominant_domain(domain_scores),
            "venue_quality_interpretation": venue_quality_interpretation,
            "conference_quality_interpretation": _interpret_conference_quality(
                core_rank=conference_rank,
                conference_maturity=conference_maturity,
                reputable_proceedings=conference_reputable,
            ) if pub_type == "conference" else None,
        }
        records.append(record)
    return records


def _analyze_journal_publications(journals: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not journals:
        return {
            "total_journal_papers": 0,
            "indexed_count": 0,
            "indexed_ratio": 0.0,
            "wos_verified_count": 0,
            "scopus_verified_count": 0,
            "first_author_percentage": 0.0,
            "avg_impact_factor": 0.0,
            "quartile_distribution": {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "Unknown": 0},
            "publication_trend": "insufficient_data",
            "research_productivity_trend": "insufficient_data",
            "publication_consistency": 0.0,
            "research_visibility_score": 0.0,
            "predatory_risk_count": 0,
            "verification_coverage": 0.0,
            "quality_interpretation_distribution": {},
            "legitimacy_distribution": {},
        }

    indexed = [
        j for j in journals if j.get("indexing_status") in {
            "verified_wos_and_scopus", "verified_wos", "verified_scopus", "reported_indexed_unverified",
        }
    ]
    wos_verified = [j for j in journals if j.get("indexing_status") in {"verified_wos_and_scopus", "verified_wos"}]
    scopus_verified = [j for j in journals if j.get("indexing_status") in {"verified_wos_and_scopus", "verified_scopus"}]
    first_author = [j for j in journals if j.get("candidate_authorship_role") in {"first_author", "first_and_corresponding_author", "sole_author"}]
    verified = [j for j in journals if j.get("verification", {}).get("verified")]
    predatory = [j for j in journals if j.get("predatory_risk") in {"high", "medium"}]
    quality_interpretation = Counter(j.get("venue_quality_interpretation") or "insufficient_evidence" for j in journals)
    legitimacy = Counter(j.get("journal_legitimacy_status") or "insufficient_evidence" for j in journals)

    impact_factors = [float(j["impact_factor"]) for j in journals if j.get("impact_factor") is not None]
    quartiles = Counter([j.get("quartile") or "Unknown" for j in journals])

    by_year = Counter(j["publication_year"] for j in journals if j.get("publication_year"))
    trend = _classify_yearly_trend(by_year)
    consistency = _compute_publication_consistency(by_year)

    visibility_score = _compute_research_visibility_score(
        indexed_ratio=len(indexed) / len(journals),
        q1_count=quartiles.get("Q1", 0),
        avg_if=mean(impact_factors) if impact_factors else 0.0,
        first_author_ratio=len(first_author) / len(journals),
    )

    return {
        "total_journal_papers": len(journals),
        "indexed_count": len(indexed),
        "indexed_ratio": round(len(indexed) / len(journals), 3),
        "wos_verified_count": len(wos_verified),
        "scopus_verified_count": len(scopus_verified),
        "first_author_percentage": round((len(first_author) / len(journals)) * 100, 1),
        "avg_impact_factor": round(mean(impact_factors), 2) if impact_factors else 0.0,
        "quartile_distribution": {
            "Q1": quartiles.get("Q1", 0),
            "Q2": quartiles.get("Q2", 0),
            "Q3": quartiles.get("Q3", 0),
            "Q4": quartiles.get("Q4", 0),
            "Unknown": quartiles.get("Unknown", 0),
        },
        "publication_trend": trend,
        "research_productivity_trend": trend,
        "publication_consistency": consistency,
        "research_visibility_score": visibility_score,
        "predatory_risk_count": len(predatory),
        "verification_coverage": round((len(verified) / len(journals)) * 100, 1),
        "quality_interpretation_distribution": dict(quality_interpretation),
        "legitimacy_distribution": dict(legitimacy),
    }


def _analyze_conference_publications(conferences: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not conferences:
        return {
            "total_conference_papers": 0,
            "core_distribution": {"A*": 0, "A": 0, "B": 0, "C": 0, "Unknown": 0},
            "mature_series_count": 0,
            "reputable_proceedings_count": 0,
            "first_author_percentage": 0.0,
            "conference_quality_score": 0.0,
            "verification_coverage": 0.0,
            "maturity_distribution": {"established": 0, "growing": 0, "early_stage": 0, "unknown": 0},
            "quality_interpretation_distribution": {},
        }

    core_dist = Counter()
    maturity_dist = Counter()
    quality_dist = Counter()
    mature_count = 0
    reputable_proc = 0
    first_author = 0
    verified = 0
    quality_points = 0.0

    for conf in conferences:
        core_rank = _resolve_core_rank(conf)
        core_dist[core_rank or "Unknown"] += 1
        series_number = _series_number(conf)
        maturity = _classify_conference_maturity(series_number)
        maturity_dist[maturity] += 1
        if series_number >= 10:
            mature_count += 1
        reputable = _is_reputable_proceedings(conf)
        if reputable:
            reputable_proc += 1
        if conf.get("candidate_authorship_role") in {"first_author", "first_and_corresponding_author", "sole_author"}:
            first_author += 1
        if conf.get("verification", {}).get("verified"):
            verified += 1
        quality_dist[
            conf.get("conference_quality_interpretation")
            or _interpret_conference_quality(core_rank, maturity, reputable)
        ] += 1

        if core_rank == "A*":
            quality_points += 10
        elif core_rank == "A":
            quality_points += 8
        elif core_rank == "B":
            quality_points += 6
        elif core_rank == "C":
            quality_points += 4
        quality_points += 2 if reputable else 0
        quality_points += 1 if series_number >= 10 else 0

    quality_score = min(100.0, (quality_points / (len(conferences) * 12)) * 100)

    return {
        "total_conference_papers": len(conferences),
        "core_distribution": {
            "A*": core_dist.get("A*", 0),
            "A": core_dist.get("A", 0),
            "B": core_dist.get("B", 0),
            "C": core_dist.get("C", 0),
            "Unknown": core_dist.get("Unknown", 0),
        },
        "mature_series_count": mature_count,
        "reputable_proceedings_count": reputable_proc,
        "first_author_percentage": round((first_author / len(conferences)) * 100, 1),
        "conference_quality_score": round(quality_score, 1),
        "verification_coverage": round((verified / len(conferences)) * 100, 1),
        "maturity_distribution": {
            "established": maturity_dist.get("established", 0),
            "growing": maturity_dist.get("growing", 0),
            "early_stage": maturity_dist.get("early_stage", 0),
            "unknown": maturity_dist.get("unknown", 0),
        },
        "quality_interpretation_distribution": dict(quality_dist),
    }


def _build_publication_analysis(
    pubs: List[Dict[str, Any]],
    journal_analysis: Dict[str, Any],
    conference_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    if not pubs:
        return {
            "journal_count": 0,
            "conference_count": 0,
            "wos_count": 0,
            "scopus_count": 0,
            "first_author_count": 0,
            "avg_impact_factor": 0.0,
            "q1_count": 0,
            "q2_count": 0,
            "q3_count": 0,
            "q4_count": 0,
            "year_distribution": {},
            "publication_quality_score": 0.0,
            "indexed_vs_non_indexed_ratio": {"indexed": 0, "non_indexed": 0},
            "verification_coverage": 0.0,
            "authorship_role_distribution": {},
            "candidate_visibility_score": 0.0,
        }

    journal_count = len([p for p in pubs if p.get("publication_type_normalized") == "journal"])
    conf_count = len([p for p in pubs if p.get("publication_type_normalized") == "conference"])
    wos_count = len([p for p in pubs if p.get("indexing_status") in {"verified_wos_and_scopus", "verified_wos"}])
    scopus_count = len([p for p in pubs if p.get("indexing_status") in {"verified_wos_and_scopus", "verified_scopus"}])
    first_author_count = len(
        [p for p in pubs if p.get("candidate_authorship_role") in {"first_author", "first_and_corresponding_author", "sole_author"}]
    )
    quartiles = Counter([(p.get("quartile") or "Unknown") for p in pubs])
    by_year = dict(Counter(p.get("publication_year") for p in pubs if p.get("publication_year")))
    verified_count = len([p for p in pubs if p.get("verification", {}).get("verified")])
    indexed_count = len([p for p in pubs if p.get("indexing_status") in {"verified_wos_and_scopus", "verified_wos", "verified_scopus", "reported_indexed_unverified"}])
    authorship_roles = Counter([p.get("candidate_authorship_role") or "unknown" for p in pubs])

    journal_quality = journal_analysis.get("research_visibility_score", 0.0)
    conference_quality = conference_analysis.get("conference_quality_score", 0.0)
    authorship_strength = min(100.0, (first_author_count / max(len(pubs), 1)) * 100 + 15)
    verification_strength = (verified_count / max(len(pubs), 1)) * 100
    publication_quality_score = round(
        journal_quality * 0.45
        + conference_quality * 0.25
        + authorship_strength * 0.15
        + verification_strength * 0.15,
        1,
    )
    candidate_visibility_score = round(
        publication_quality_score * 0.65
        + journal_analysis.get("publication_consistency", 0.0) * 0.20
        + conference_analysis.get("conference_quality_score", 0.0) * 0.15,
        1,
    )

    return {
        "journal_count": journal_count,
        "conference_count": conf_count,
        "wos_count": wos_count,
        "scopus_count": scopus_count,
        "first_author_count": first_author_count,
        "avg_impact_factor": journal_analysis.get("avg_impact_factor", 0.0),
        "q1_count": quartiles.get("Q1", 0),
        "q2_count": quartiles.get("Q2", 0),
        "q3_count": quartiles.get("Q3", 0),
        "q4_count": quartiles.get("Q4", 0),
        "year_distribution": by_year,
        "indexed_vs_non_indexed_ratio": {
            "indexed": indexed_count,
            "non_indexed": max(0, len(pubs) - indexed_count),
        },
        "verification_coverage": round((verified_count / len(pubs)) * 100, 1),
        "authorship_role_distribution": dict(authorship_roles),
        "candidate_visibility_score": candidate_visibility_score,
        "publication_quality_score": publication_quality_score,
    }


def _analyze_coauthors(pubs: List[dict], candidate_name: Optional[str]) -> Dict[str, Any]:
    if not pubs:
        return {
            "total_unique_coauthors": 0,
            "avg_authors_per_paper": 0,
            "solo_authored_count": 0,
            "top_collaborators": [],
            "collaboration_score": 0,
            "repeat_collaboration_ratio": 0.0,
            "network_density_proxy": 0.0,
            "collaboration_diversity_score": 0.0,
            "collaboration_consistency": 0.0,
            "one_time_collaborators": 0,
            "stable_research_group_count": 0,
            "collaboration_patterns": {},
            "leadership_pattern": "insufficient_data",
            "collaboration_interpretation": "Insufficient collaboration evidence.",
        }

    all_coauthors: List[str] = []
    coauthor_counter: Counter = Counter()
    pair_counts: Counter = Counter()
    coauthors_per_paper: List[List[str]] = []
    year_to_collab_size: Dict[int, List[int]] = defaultdict(list)
    author_counts: List[int] = []
    authorship_roles = Counter()
    first_author_by_paper: List[str] = []
    solo_count = 0
    candidate_norm = _normalize_name(candidate_name)

    for p in pubs:
        authors = p.get("authors_list") or _split_authors(p.get("authors") or "")
        normalized_authors = [_normalize_name(a) for a in authors if _normalize_name(a)]
        coauthors = [a for a in normalized_authors if a != candidate_norm]
        author_count = p.get("author_count") or len(authors) or 1
        author_counts.append(author_count)
        authorship_roles[p.get("candidate_authorship_role") or "unknown"] += 1
        if author_count <= 1:
            solo_count += 1
        unique_coauthors = sorted(set(coauthors))
        all_coauthors.extend(unique_coauthors)
        coauthor_counter.update(unique_coauthors)
        coauthors_per_paper.append(unique_coauthors)
        if normalized_authors:
            first_author = normalized_authors[0]
            if first_author != candidate_norm:
                first_author_by_paper.append(first_author)
        pub_year = p.get("publication_year")
        if isinstance(pub_year, int):
            year_to_collab_size[pub_year].append(len(unique_coauthors))

    for coauthors in coauthors_per_paper:
        for i in range(len(coauthors)):
            for j in range(i + 1, len(coauthors)):
                pair = tuple(sorted((coauthors[i], coauthors[j])))
                pair_counts[pair] += 1

    top = [{"name": n, "paper_count": c} for n, c in coauthor_counter.most_common(12)]
    unique_coauthors = len(coauthor_counter)
    recurring = len([n for n, c in coauthor_counter.items() if c > 1])
    one_time_collaborators = len([n for n, c in coauthor_counter.items() if c == 1])
    repeat_ratio = (recurring / max(unique_coauthors, 1)) * 100
    avg_authors = round(mean(author_counts), 2) if author_counts else 0.0
    network_density = _coauthor_network_density_proxy(coauthors_per_paper)
    collaboration_diversity = _collaboration_diversity_score(coauthor_counter)
    collaboration_consistency = _collaboration_consistency(year_to_collab_size)
    stable_research_group_count = len([1 for _, c in pair_counts.items() if c >= 3])
    collaboration_score = _collaboration_strength_index(
        recurring_ratio=repeat_ratio,
        density=network_density,
        diversity=collaboration_diversity,
        solo_count=solo_count,
        publication_count=len(pubs),
    )
    leadership_pattern = _classify_collaboration_leadership(authorship_roles)
    collaboration_patterns = {
        "recurring_collaborators": recurring,
        "one_time_collaborators": one_time_collaborators,
        "stable_research_groups": stable_research_group_count,
        "possible_supervision_style": _possible_supervision_pattern(pubs, candidate_norm, first_author_by_paper),
        "institutional_collaboration_pattern": _infer_institutional_collaboration(pubs),
        "international_collaboration_pattern": _infer_international_collaboration(pubs),
        "interdisciplinary_collaboration_pattern": _infer_interdisciplinary_collaboration(pubs),
    }
    interpretation = (
        f"Collaboration network includes {unique_coauthors} unique co-authors with "
        f"{repeat_ratio:.1f}% recurring collaborators; leadership pattern is "
        f"{leadership_pattern.replace('_', ' ')}."
    )

    return {
        "total_unique_coauthors": unique_coauthors,
        "avg_authors_per_paper": avg_authors,
        "solo_authored_count": solo_count,
        "top_collaborators": top,
        "repeat_collaboration_ratio": round(repeat_ratio, 1),
        "network_density_proxy": round(network_density, 1),
        "collaboration_diversity_score": collaboration_diversity,
        "collaboration_consistency": collaboration_consistency,
        "one_time_collaborators": one_time_collaborators,
        "stable_research_group_count": stable_research_group_count,
        "collaboration_patterns": collaboration_patterns,
        "leadership_pattern": leadership_pattern,
        "collaboration_interpretation": interpretation,
        "collaboration_score": collaboration_score,
    }


def _analyze_topic_variability(pubs: List[dict]) -> Dict[str, Any]:
    if not pubs:
        return {
            "unique_venues": 0,
            "topic_keywords": [],
            "dominant_topic_area": None,
            "topic_percentages": [],
            "research_breadth": "none",
            "variability_score": 0.0,
            "topic_clusters": [],
            "thematic_clusters": [],
            "topic_evolution_timeline": [],
            "topic_transition_count": 0,
            "topic_concentration_index": 0.0,
            "topic_dispersion_index": 0.0,
            "semantic_similarity_average": 0.0,
            "profile_classification": "insufficient_data",
            "variability_explanation": [],
            "specialization_focus_score": 0.0,
        }

    prepared = _prepare_topic_documents(pubs)
    venues = {d["venue"] for d in prepared if d.get("venue")}
    keyword_counter: Counter = Counter()
    for d in prepared:
        keyword_counter.update(d["tokens"])
    vectors = [d["vector"] for d in prepared]
    sim_matrix = _cosine_similarity_matrix(vectors)
    avg_similarity = _average_similarity(sim_matrix)
    clusters = _cluster_publications(prepared, sim_matrix, threshold=0.24)
    thematic_clusters = _build_thematic_clusters(prepared, clusters)
    domain_counter = Counter()
    for d in prepared:
        domain_counter.update(d["domains"])
    groq_topics = infer_publication_topics_with_groq([d["title"] for d in prepared])
    groq_domain_counter = Counter()
    if groq_topics and isinstance(groq_topics.get("domains"), list):
        for item in groq_topics["domains"]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("domain", "")).strip().lower().replace(" ", "_")
            pct = _safe_float(item.get("percentage"))
            if not name or pct is None:
                continue
            groq_domain_counter[name] += max(0.0, pct)
        if groq_domain_counter:
            domain_counter = Counter()
            for k, v in groq_domain_counter.items():
                domain_counter[k] = float(v)
    dominant_topic_area = domain_counter.most_common(1)[0][0] if domain_counter else None
    topic_percentages = _domain_percentages(domain_counter)
    concentration = _topic_concentration_index(topic_percentages)
    dispersion = round(100.0 - concentration, 1)
    timeline, transitions = _topic_evolution(prepared)
    profile_classification = _classify_topic_profile(concentration, len(topic_percentages), transitions)
    breadth = (
        "strongly_interdisciplinary" if profile_classification == "strongly_interdisciplinary"
        else "moderately_diversified" if profile_classification == "moderately_diversified"
        else "highly_specialized"
    )
    focus_score = _specialization_focus_score(keyword_counter)
    variability_score, explanation = _topic_variability_score(
        concentration=concentration,
        transitions=transitions,
        domain_count=len(topic_percentages),
        avg_similarity=avg_similarity,
        cluster_count=len(thematic_clusters),
    )

    return {
        "unique_venues": len(venues),
        "topic_keywords": [{"keyword": k, "count": c} for k, c in keyword_counter.most_common(20)],
        "dominant_topic_area": dominant_topic_area,
        "topic_percentages": topic_percentages,
        "topic_clusters": thematic_clusters,
        "thematic_clusters": thematic_clusters,
        "topic_evolution_timeline": timeline,
        "topic_transition_count": transitions,
        "topic_concentration_index": concentration,
        "topic_dispersion_index": dispersion,
        "semantic_similarity_average": avg_similarity,
        "research_breadth": breadth,
        "profile_classification": profile_classification,
        "variability_explanation": explanation,
        "groq_topic_inference_used": bool(groq_domain_counter),
        "groq_topic_notes": groq_topics.get("notes") if groq_topics else None,
        "specialization_focus_score": focus_score,
        "variability_score": variability_score,
    }


def _analyze_books(books: List[dict]) -> Dict[str, Any]:
    if not books:
        return {
            "book_count": 0,
            "authorship_distribution": {},
            "valid_isbn_count": 0,
            "academic_publisher_count": 0,
            "commercial_publisher_count": 0,
            "vanity_risk_count": 0,
            "scholarly_relevance_score": 0.0,
            "publisher_quality_interpretation": "insufficient_evidence",
            "academic_contribution_summary": "No books available for analysis.",
            "books_score": 0.0,
            "books": [],
        }

    role_counter = Counter()
    valid_isbn_count = 0
    academic_count = 0
    commercial_count = 0
    vanity_risk = 0
    relevance_points = 0.0
    evidence_gap_count = 0
    for b in books:
        inferred_role = _infer_book_authorship_role(b)
        b["candidate_authorship_role_inferred"] = inferred_role
        role_counter[inferred_role] += 1

        isbn_valid = _is_valid_isbn(b.get("isbn"))
        b["isbn_valid"] = isbn_valid
        if isbn_valid:
            valid_isbn_count += 1
        else:
            evidence_gap_count += 1

        pub_type = _classify_book_publisher_type(b.get("publisher"))
        b["publisher_type"] = pub_type
        if pub_type == "academic":
            academic_count += 1
            relevance_points += 2.0
        elif pub_type == "commercial":
            commercial_count += 1
            relevance_points += 1.0
        elif pub_type == "vanity_or_self_published":
            vanity_risk += 1
            relevance_points -= 0.5

        if inferred_role in {"sole_author", "lead_author"}:
            relevance_points += 1.5
        elif inferred_role == "co_author":
            relevance_points += 1.0
        elif inferred_role == "edited_volume_contributor":
            relevance_points += 0.5

    total_books = len(books)
    scholarly_relevance_score = round(
        max(0.0, min(100.0, (relevance_points / max(total_books * 3.0, 1.0)) * 100)),
        1,
    )
    score = round(
        max(
            0.0,
            min(
                100.0,
                scholarly_relevance_score * 0.55
                + (valid_isbn_count / max(total_books, 1)) * 100 * 0.25
                + (academic_count / max(total_books, 1)) * 100 * 0.20
                - vanity_risk * 6,
            ),
        ),
        1,
    )
    publisher_interpretation = (
        "mostly_academic_publishers" if academic_count >= max(1, round(total_books * 0.5))
        else "mixed_publishers" if academic_count > 0 or commercial_count > 0
        else "limited_publisher_evidence"
    )
    return {
        "book_count": total_books,
        "authorship_distribution": dict(role_counter),
        "valid_isbn_count": valid_isbn_count,
        "academic_publisher_count": academic_count,
        "commercial_publisher_count": commercial_count,
        "vanity_risk_count": vanity_risk,
        "scholarly_relevance_score": scholarly_relevance_score,
        "publisher_quality_interpretation": publisher_interpretation,
        "academic_contribution_summary": (
            f"{total_books} book record(s): "
            f"{role_counter.get('sole_author', 0)} sole-author, "
            f"{role_counter.get('lead_author', 0)} lead-author, "
            f"{role_counter.get('co_author', 0)} co-author entries."
        ),
        "books_score": score,
        "evidence_gap_count": evidence_gap_count,
        "books": books,
    }


def _analyze_patents(patents: List[dict]) -> Dict[str, Any]:
    if not patents:
        return {
            "patent_count": 0,
            "verified_patent_count": 0,
            "countries": [],
            "lead_inventor_count": 0,
            "co_inventor_count": 0,
            "pending_or_unverified_count": 0,
            "innovation_orientation": "insufficient_evidence",
            "commercialization_potential_score": 0.0,
            "research_translation_capability": "insufficient_evidence",
            "inventor_role_distribution": {},
            "innovation_impact_interpretation": "No patent evidence available.",
            "patents_score": 0.0,
            "patents": [],
        }

    countries = sorted(set([p.get("filing_country") or "Unknown" for p in patents]))
    role_counter = Counter()
    verified_count = 0
    pending_count = 0
    lead_count = 0
    co_count = 0
    applied_orientation = 0
    commercialization_points = 0.0

    for patent in patents:
        role = _infer_patent_role(patent)
        patent["candidate_inventor_role_inferred"] = role
        role_counter[role] += 1
        if role in {"lead_inventor", "sole_inventor"}:
            lead_count += 1
        elif role == "co_inventor":
            co_count += 1

        number_ok = _patent_number_likely_valid(patent.get("patent_number"))
        link_ok = _is_patent_verification_link(patent.get("verification_link"))
        verification_status = (
            "verified" if number_ok and link_ok else "partially_verified" if (number_ok or link_ok) else "unverified"
        )
        patent["verification_status"] = verification_status
        if verification_status == "verified":
            verified_count += 1

        patent_status = _infer_patent_status(patent)
        patent["patent_status_inferred"] = patent_status
        if patent_status in {"pending", "unverified"}:
            pending_count += 1

        title = (patent.get("patent_title") or "").lower()
        if any(k in title for k in {"system", "device", "method", "prototype", "implementation", "application"}):
            applied_orientation += 1
            commercialization_points += 1.5
        if any(k in title for k in {"industry", "commercial", "production", "manufactur", "process"}):
            commercialization_points += 1.0
        if link_ok:
            commercialization_points += 0.8

    commercialization_score = round(
        min(100.0, (commercialization_points / max(len(patents) * 2.5, 1.0)) * 100),
        1,
    )
    score = round(
        max(
            0.0,
            min(
                100.0,
                (verified_count / max(len(patents), 1)) * 45
                + (lead_count / max(len(patents), 1)) * 20
                + commercialization_score * 0.25
                + min(10.0, len(countries) * 2.5)
                - pending_count * 4,
            ),
        ),
        1,
    )
    return {
        "patent_count": len(patents),
        "verified_patent_count": verified_count,
        "countries": countries,
        "lead_inventor_count": lead_count,
        "co_inventor_count": co_count,
        "pending_or_unverified_count": pending_count,
        "innovation_orientation": (
            "applied_research_oriented" if applied_orientation >= max(1, round(len(patents) * 0.5))
            else "mixed_or_unclear_orientation"
        ),
        "commercialization_potential_score": commercialization_score,
        "research_translation_capability": (
            "strong" if verified_count >= max(1, round(len(patents) * 0.5))
            else "moderate" if verified_count > 0
            else "limited"
        ),
        "inventor_role_distribution": dict(role_counter),
        "innovation_impact_interpretation": (
            f"{len(patents)} patent record(s), {verified_count} verified, "
            f"{lead_count} lead-inventor contribution(s)."
        ),
        "patents_score": score,
        "patents": patents,
    }


def _compute_research_score(
    publication_analysis: Dict[str, Any],
    journal_analysis: Dict[str, Any],
    conference_analysis: Dict[str, Any],
    coauthor_analysis: Dict[str, Any],
    topic_variability: Dict[str, Any],
    books_analysis: Dict[str, Any],
    patents_analysis: Dict[str, Any],
) -> Tuple[float, Dict[str, Any]]:
    weights = {
        "publication_quality": 0.32,
        "journal_visibility": 0.18,
        "conference_quality": 0.10,
        "topic_variability": 0.14,
        "collaboration": 0.12,
        "books": 0.06,
        "patents": 0.08,
    }
    components = {
        "publication_quality": publication_analysis.get("publication_quality_score", 0.0),
        "journal_visibility": journal_analysis.get("research_visibility_score", 0.0),
        "conference_quality": conference_analysis.get("conference_quality_score", 0.0),
        "topic_variability": topic_variability.get("variability_score", 0.0),
        "collaboration": coauthor_analysis.get("collaboration_score", 0.0),
        "books": books_analysis.get("books_score", 0.0),
        "patents": patents_analysis.get("patents_score", 0.0),
    }
    weighted = {k: round(components[k] * weights[k], 2) for k in weights}
    predatory_penalty = min(15.0, journal_analysis.get("predatory_risk_count", 0) * 3.0)
    low_evidence_penalty = 0.0
    if publication_analysis.get("verification_coverage", 0.0) < 25:
        low_evidence_penalty += 5.0
    if books_analysis.get("evidence_gap_count", 0) > max(1, books_analysis.get("book_count", 0)):
        low_evidence_penalty += 2.0
    total_score = max(0.0, round(sum(weighted.values()) - predatory_penalty - low_evidence_penalty, 1))
    return total_score, {
        "weights": weights,
        "raw_scores": {k: round(v, 1) for k, v in components.items()},
        "weighted_contributions": weighted,
        "risk_adjustments": {
            "predatory_risk_penalty": round(predatory_penalty, 1),
            "low_evidence_penalty": round(low_evidence_penalty, 1),
        },
        "explainability_notes": [
            "Final score is a weighted sum of module scores with transparent penalties for predatory-risk and weak evidence coverage.",
            "Topic variability score reflects domain spread, semantic separation, and temporal transitions.",
            "Collaboration score reflects diversity, recurrence, network structure, and leadership signals.",
        ],
    }


def _build_narrative(
    candidate_name: Optional[str],
    publication_analysis: Dict[str, Any],
    journal_analysis: Dict[str, Any],
    conference_analysis: Dict[str, Any],
    coauthor_analysis: Dict[str, Any],
    topic_variability: Dict[str, Any],
    books_analysis: Dict[str, Any],
    patents_analysis: Dict[str, Any],
) -> str:
    name = candidate_name or "Candidate"
    parts = [
        f"{name} has {publication_analysis.get('journal_count', 0)} journal and "
        f"{publication_analysis.get('conference_count', 0)} conference publication(s)."
    ]
    if publication_analysis.get("journal_count", 0) > 0:
        parts.append(
            f"Verified WoS papers: {publication_analysis.get('wos_count', 0)}, "
            f"Scopus papers: {publication_analysis.get('scopus_count', 0)}, "
            f"Q1 papers: {publication_analysis.get('q1_count', 0)}."
        )
        parts.append(
            f"Journal visibility score is {journal_analysis.get('research_visibility_score', 0):.1f}/100 "
            f"with {journal_analysis.get('verification_coverage', 0):.1f}% metadata verification coverage."
        )
    if publication_analysis.get("conference_count", 0) > 0:
        parts.append(
            f"Conference quality score is {conference_analysis.get('conference_quality_score', 0):.1f}/100; "
            f"mature series papers: {conference_analysis.get('mature_series_count', 0)}; "
            f"A*/A papers: {conference_analysis.get('core_distribution', {}).get('A*', 0) + conference_analysis.get('core_distribution', {}).get('A', 0)}."
        )
    if coauthor_analysis.get("total_unique_coauthors", 0) > 0:
        parts.append(
            f"Collaboration includes {coauthor_analysis.get('total_unique_coauthors', 0)} unique co-authors "
            f"and repeat-collaboration ratio {coauthor_analysis.get('repeat_collaboration_ratio', 0):.1f}%."
        )
    parts.append(
        f"Topic profile is {topic_variability.get('profile_classification', 'unknown').replace('_', ' ')} "
        f"(dominant area: {topic_variability.get('dominant_topic_area') or 'unknown'}) with "
        f"variability score {topic_variability.get('variability_score', 0):.1f}/100."
    )
    if books_analysis.get("book_count", 0) or patents_analysis.get("patent_count", 0):
        parts.append(
            f"Books: {books_analysis.get('book_count', 0)}, patents: {patents_analysis.get('patent_count', 0)}."
        )
    return " ".join(parts)


def _verify_publication_metadata(
    doi: Optional[str],
    issn: Optional[str],
    venue_name: Optional[str],
    publisher: Optional[str],
    verification_cache: Dict[str, Any],
) -> Dict[str, Any]:
    result = {
        "verified": False,
        "source": None,
        "verification_sources": [],
        "publisher": publisher,
        "issn": issn,
        "doi": doi,
        "impact_factor": None,
        "quartile": None,
        "journal_exists": None,
        "wos_verified": None,
        "scopus_verified": None,
    }

    cache_key = f"{doi or ''}|{issn or ''}|{(venue_name or '').lower().strip()}"
    cached = verification_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    external_verify = _external_verification_enabled()
    crossref_data: Dict[str, Any] = {}
    openalex_data: Dict[str, Any] = {}
    if external_verify:
        crossref_data = _fetch_crossref_metadata(doi) if doi else {}
        openalex_data = _fetch_openalex_source(issn=issn, venue_name=venue_name)

    if crossref_data:
        result["verified"] = True
        result["source"] = "crossref"
        result["verification_sources"].append("crossref")
        result["publisher"] = crossref_data.get("publisher") or result["publisher"]
        result["issn"] = result["issn"] or crossref_data.get("issn")
        result["journal_exists"] = True
    if openalex_data:
        result["verified"] = True
        result["source"] = "openalex" if not result["source"] else f"{result['source']}+openalex"
        result["verification_sources"].append("openalex")
        result["publisher"] = openalex_data.get("host_organization_name") or result["publisher"]
        result["issn"] = result["issn"] or openalex_data.get("issn_l")
        result["journal_exists"] = True

    # Optional local references for quartile/indexing enrichment.
    local_ref = _lookup_journal_reference(issn=result.get("issn"), venue_name=venue_name)
    if local_ref:
        result["verification_sources"].append("local_reference")
        result["quartile"] = _normalize_quartile(local_ref.get("quartile"))
        result["impact_factor"] = _safe_float(local_ref.get("impact_factor"))
        result["wos_verified"] = _safe_bool(local_ref.get("wos_indexed"))
        result["scopus_verified"] = _safe_bool(local_ref.get("scopus_indexed"))
        result["verified"] = True

    verification_cache[cache_key] = result
    return result


def _determine_indexing_status(
    verification: Dict[str, Any],
    reported_scopus: Optional[bool],
    reported_wos: Optional[bool],
    reported_quartile: Optional[str],
) -> str:
    if verification.get("wos_verified") is True and verification.get("scopus_verified") is True:
        return "verified_wos_and_scopus"
    if verification.get("wos_verified") is True:
        return "verified_wos"
    if verification.get("scopus_verified") is True:
        return "verified_scopus"
    if verification.get("verified") and (reported_scopus or reported_wos):
        return "reported_indexed_unverified"
    if reported_quartile in {"Q1", "Q2", "Q3", "Q4"}:
        return "reported_indexed_unverified"
    if verification.get("verified"):
        return "verified_unindexed_or_unknown"
    if reported_scopus or reported_wos:
        return "reported_indexed_unverified"
    return "not_verified"


def _resolve_core_rank(conf: Dict[str, Any]) -> Optional[str]:
    reported = (conf.get("conference_rank_reported") or "").upper().strip()
    if reported in {"A*", "A", "B", "C"}:
        return reported

    venue = (conf.get("conference_name") or conf.get("venue_name") or "").lower().strip()
    if not venue:
        return None
    refs = _load_conference_reference()
    mapped = refs.get(venue)
    if mapped in {"A*", "A", "B", "C"}:
        return mapped
    return None


def _series_number(conf: Dict[str, Any]) -> int:
    text = " ".join(
        [
            str(conf.get("conference_series_edition") or ""),
            str(conf.get("conference_name") or ""),
            str(conf.get("venue_name") or ""),
        ]
    ).lower()
    m = re.search(r"\b(\d{1,3})(st|nd|rd|th)\b", text)
    if m:
        return int(m.group(1))
    return 0


def _is_reputable_proceedings(conf: Dict[str, Any]) -> bool:
    combined = " ".join(
        [
            str(conf.get("publisher") or ""),
            str(conf.get("proceedings_indexed_in") or ""),
            str(conf.get("conference_name") or ""),
            str(conf.get("venue_name") or ""),
        ]
    ).lower()
    return any(x in combined for x in ("ieee", "acm", "springer", "scopus", "wos", "web of science", "dblp"))


def _classify_yearly_trend(by_year: Counter) -> str:
    if len(by_year) < 2:
        return "insufficient_data"
    years = sorted(by_year.items())
    first = years[0][1]
    last = years[-1][1]
    if last > first:
        return "improving"
    if last < first:
        return "declining"
    return "stable"


def _compute_publication_consistency(by_year: Counter) -> float:
    if not by_year:
        return 0.0
    values = list(by_year.values())
    if len(values) == 1:
        return 100.0
    avg = mean(values)
    if avg == 0:
        return 0.0
    variance_penalty = min(100.0, (pstdev(values) / avg) * 100)
    return round(max(0.0, 100.0 - variance_penalty), 1)


def _compute_research_visibility_score(
    indexed_ratio: float,
    q1_count: int,
    avg_if: float,
    first_author_ratio: float,
) -> float:
    score = (
        indexed_ratio * 45.0
        + min(30.0, q1_count * 4.0)
        + min(15.0, avg_if * 2.5)
        + first_author_ratio * 10.0
    )
    return round(min(100.0, score), 1)


def _interpret_venue_quality(
    publication_type: Optional[str],
    indexing_status: str,
    quartile: Optional[str],
    impact_factor: Optional[float],
    predatory_risk: str,
) -> str:
    if predatory_risk == "high":
        return "predatory_risk_indicators"
    if indexing_status in {"verified_wos", "verified_scopus"} and quartile in {"Q1", "Q2"}:
        return "highly_reputed_indexed_venue"
    if indexing_status == "verified_wos_and_scopus" and quartile in {"Q1", "Q2", "Q3"}:
        return "highly_reputed_indexed_venue"
    if indexing_status in {"verified_wos_and_scopus", "verified_wos", "verified_scopus"} and quartile in {"Q3", "Q4"}:
        return "lower_tier_indexed_venue"
    if indexing_status in {"verified_wos_and_scopus", "verified_wos", "verified_scopus"}:
        return "moderate_quality_venue"
    if indexing_status == "reported_indexed_unverified":
        return "unverified_venue"
    if impact_factor and impact_factor > 0:
        return "moderate_quality_venue"
    if publication_type == "conference":
        return "insufficient_evidence"
    return "unverified_venue"


def _specialization_focus_score(keyword_counter: Counter) -> float:
    if not keyword_counter:
        return 0.0
    top = [c for _, c in keyword_counter.most_common(5)]
    total = sum(keyword_counter.values())
    return round(min(100.0, (sum(top) / max(total, 1)) * 100), 1)


def _derive_topic_clusters(keyword_counter: Counter, cooccurrence: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    clusters = []
    seeds = [k for k, _ in keyword_counter.most_common(6)]
    for seed in seeds:
        related = []
        for (a, b), freq in cooccurrence.items():
            if seed in {a, b} and freq >= 2:
                related.append((b if a == seed else a, freq))
        related_sorted = sorted(related, key=lambda x: x[1], reverse=True)[:4]
        if related_sorted:
            clusters.append({
                "topic": seed,
                "related_keywords": [k for k, _ in related_sorted],
                "cooccurrence_strength": sum(v for _, v in related_sorted),
            })
    return clusters


def _classify_publisher_credibility(publisher: Optional[str], venue_name: Optional[str]) -> str:
    text = f"{publisher or ''} {venue_name or ''}".lower()
    if any(p in text for p in KNOWN_REPUTED_PUBLISHERS):
        return "high"
    if any(p in text for p in {"university", "press", "society", "association"}):
        return "moderate"
    if not text.strip():
        return "unknown"
    return "low"


def _estimate_predatory_risk(
    venue_name: Optional[str],
    publisher: Optional[str],
    has_doi: bool,
    has_issn: bool,
    indexed_status: str,
) -> str:
    text = f"{venue_name or ''} {publisher or ''}".lower()
    risk_score = 0
    if any(term in text for term in PREDATORY_RISK_TERMS):
        risk_score += 2
    if not has_doi:
        risk_score += 1
    if not has_issn:
        risk_score += 1
    if indexed_status == "not_verified":
        risk_score += 2
    elif indexed_status == "reported_indexed_unverified":
        risk_score += 1

    if risk_score >= 4:
        return "high"
    if risk_score >= 2:
        return "medium"
    return "low"


def _normalize_publication_type(
    reported_type: Optional[str],
    journal_name: Optional[str],
    conference_name: Optional[str],
    venue_name: Optional[str],
) -> str:
    text = (reported_type or "").lower().strip()
    if "journal" in text:
        return "journal"
    if "conference" in text:
        return "conference"
    combined = " ".join([journal_name or "", conference_name or "", venue_name or ""]).lower()
    if re.search(r"\b(conference|symposium|workshop|proceedings|ieee conf|acm conf)\b", combined):
        return "conference"
    return "journal" if journal_name else "conference" if conference_name else "journal"


def _classify_authorship_role(
    candidate_position: Optional[int],
    author_count: int,
    corresponding: bool,
) -> str:
    if author_count <= 1:
        return "sole_author"
    if candidate_position is None:
        return "unknown"
    if candidate_position == 1 and corresponding:
        return "first_and_corresponding_author"
    if candidate_position == 1:
        return "first_author"
    if corresponding:
        return "corresponding_author"
    if candidate_position == author_count and author_count > 2:
        return "last_author"
    return "middle_co_author"


def _infer_corresponding_flag(
    authors_raw: str,
    candidate_name: Optional[str],
    candidate_position: Optional[int],
) -> bool:
    text = authors_raw or ""
    if "*" in text and candidate_position == 1:
        return True
    if candidate_name and re.search(re.escape(candidate_name), text, flags=re.IGNORECASE) and "corresponding" in text.lower():
        return True
    return False


def _infer_author_position(candidate_name: Optional[str], authors: List[str]) -> Optional[int]:
    if not candidate_name or not authors:
        return None
    candidate_norm = _normalize_name(candidate_name)
    for idx, author in enumerate(authors, start=1):
        if _normalize_name(author) == candidate_norm:
            return idx
    return None


def _split_authors(authors_text: str) -> List[str]:
    if not authors_text:
        return []
    return [a.strip() for a in re.split(r",|;| and ", authors_text, flags=re.IGNORECASE) if a.strip()]


def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    text = doi.strip()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    return text if re.match(r"^10\.\d{4,9}/", text) else None


def _normalize_issn(issn: Optional[str]) -> Optional[str]:
    if not issn:
        return None
    m = re.search(r"\b(\d{4}-?\d{3}[\dxX])\b", issn)
    if not m:
        return None
    raw = m.group(1).replace("-", "")
    return f"{raw[:4]}-{raw[4:]}"


def _normalize_quartile(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().upper()
    m = re.search(r"\bQ([1-4])\b", text)
    return f"Q{m.group(1)}" if m else None


def _external_verification_enabled() -> bool:
    return os.getenv("TALASH_RESEARCH_EXTERNAL_VERIFY", "true").strip().lower() in {"1", "true", "yes"}


def _fetch_crossref_metadata(doi: str) -> Dict[str, Any]:
    url = f"https://api.crossref.org/works/{quote_plus(doi)}"
    payload = _fetch_json(url)
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    if not message:
        return {}
    issn_values = message.get("ISSN") or []
    return {
        "publisher": message.get("publisher"),
        "issn": issn_values[0] if issn_values else None,
    }


def _fetch_openalex_source(issn: Optional[str], venue_name: Optional[str]) -> Dict[str, Any]:
    if issn:
        payload = _fetch_json(f"https://api.openalex.org/sources?filter=issn:{quote_plus(issn)}&per-page=1")
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if results:
            return results[0]
    if venue_name:
        payload = _fetch_json(
            f"https://api.openalex.org/sources?search={quote_plus(venue_name)}&per-page=1"
        )
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if results:
            return results[0]
    return {}


def _fetch_json(url: str) -> Dict[str, Any]:
    try:
        with urlopen(url, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError):
        return {}


def _lookup_journal_reference(issn: Optional[str], venue_name: Optional[str]) -> Optional[Dict[str, Any]]:
    refs = _load_json_dict(_journal_ref_file)
    if not refs:
        return None
    if issn:
        normalized_issn = _normalize_issn(issn)
        if normalized_issn and normalized_issn in refs:
            return refs[normalized_issn]
    if venue_name:
        key = venue_name.strip().lower()
        return refs.get(key)
    return None


def _load_conference_reference() -> Dict[str, str]:
    refs = _load_json_dict_cached(str(_conference_ref_file))
    out: Dict[str, str] = {}
    for k, v in refs.items():
        key = str(k).strip().lower()
        rank = str(v).strip().upper()
        if rank in {"A*", "A", "B", "C"}:
            out[key] = rank
    return out


def _load_verification_cache() -> Dict[str, Any]:
    cache = _load_json_dict(_verification_cache_file)
    return cache if isinstance(cache, dict) else {}


def _save_verification_cache(cache: Dict[str, Any]) -> None:
    try:
        _verification_cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_verification_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _load_json_dict(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=32)
def _load_json_dict_cached(path_str: str) -> Dict[str, Any]:
    return _load_json_dict(Path(path_str))


def _build_indexing_evidence(
    verification: Dict[str, Any],
    reported_scopus: Optional[bool],
    reported_wos: Optional[bool],
    reported_quartile: Optional[str],
) -> Dict[str, Any]:
    return {
        "wos": "verified" if verification.get("wos_verified") else "reported" if reported_wos else "not_found",
        "scopus": "verified" if verification.get("scopus_verified") else "reported" if reported_scopus else "not_found",
        "quartile": reported_quartile or verification.get("quartile"),
        "verification_sources": verification.get("verification_sources", []),
    }


def _verification_confidence_score(
    verification: Dict[str, Any],
    indexing_status: str,
    doi: Optional[str],
    issn: Optional[str],
) -> float:
    score = 0.0
    if verification.get("verified"):
        score += 35
    if indexing_status in {"verified_wos_and_scopus", "verified_wos", "verified_scopus"}:
        score += 35
    elif indexing_status == "reported_indexed_unverified":
        score += 12
    if doi:
        score += 15
    if issn:
        score += 15
    return round(min(100.0, score), 1)


def _evidence_gaps(
    verification: Dict[str, Any],
    indexing_status: str,
    doi: Optional[str],
    issn: Optional[str],
) -> List[str]:
    gaps: List[str] = []
    if not doi:
        gaps.append("doi_missing")
    if not issn:
        gaps.append("issn_missing")
    if indexing_status == "reported_indexed_unverified":
        gaps.append("indexing_unverified")
    if not verification.get("verified"):
        gaps.append("external_metadata_unavailable")
    return gaps


def _authorship_significance(authorship_role: str, author_count: int) -> str:
    if authorship_role in {"sole_author", "first_and_corresponding_author"}:
        return "very_high"
    if authorship_role in {"first_author", "corresponding_author", "last_author"}:
        return "high"
    if authorship_role == "middle_co_author":
        return "moderate" if author_count <= 4 else "supporting"
    return "insufficient_evidence"


def _classify_journal_legitimacy(
    indexing_status: str,
    publisher_credibility: str,
    predatory_risk: str,
    verification_confidence: float,
) -> str:
    if predatory_risk == "high":
        return "predatory_risk_indicators"
    if indexing_status in {"verified_wos_and_scopus", "verified_wos", "verified_scopus"}:
        return "legitimate_indexed"
    if publisher_credibility in {"high", "moderate"} and verification_confidence >= 50:
        return "likely_legitimate_but_unindexed_or_unverified"
    if predatory_risk == "medium":
        return "suspicious_or_lower_credibility"
    return "insufficient_evidence"


def _classify_conference_maturity(series_number: int) -> str:
    if series_number >= 15:
        return "established"
    if series_number >= 5:
        return "growing"
    if series_number > 0:
        return "early_stage"
    return "unknown"


def _interpret_conference_quality(
    core_rank: Optional[str],
    conference_maturity: str,
    reputable_proceedings: bool,
) -> str:
    if core_rank in {"A*", "A"} and reputable_proceedings:
        return "highly_reputed_indexed_venue"
    if core_rank in {"B", "C"} or (conference_maturity in {"established", "growing"} and reputable_proceedings):
        return "moderate_quality_venue"
    if conference_maturity == "early_stage" and not reputable_proceedings:
        return "lower_tier_or_early_stage_venue"
    return "insufficient_evidence"


def _build_recruiter_summary(
    publication_analysis: Dict[str, Any],
    journal_analysis: Dict[str, Any],
    conference_analysis: Dict[str, Any],
    coauthor_analysis: Dict[str, Any],
    topic_variability: Dict[str, Any],
    books_analysis: Dict[str, Any],
    patents_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    key_indicators = [
        f"Publication quality score: {publication_analysis.get('publication_quality_score', 0):.1f}/100",
        f"Journal visibility score: {journal_analysis.get('research_visibility_score', 0):.1f}/100",
        f"Conference quality score: {conference_analysis.get('conference_quality_score', 0):.1f}/100",
        f"Topic variability score: {topic_variability.get('variability_score', 0):.1f}/100 ({topic_variability.get('profile_classification', 'unknown').replace('_', ' ')})",
        f"Collaboration score: {coauthor_analysis.get('collaboration_score', 0):.1f}/100 ({coauthor_analysis.get('leadership_pattern', 'unknown').replace('_', ' ')})",
        f"Books score: {books_analysis.get('books_score', 0):.1f}/100, Patents score: {patents_analysis.get('patents_score', 0):.1f}/100",
        f"Verification coverage: {publication_analysis.get('verification_coverage', 0):.1f}%",
    ]
    risk_flags: List[str] = []
    if journal_analysis.get("predatory_risk_count", 0) > 0:
        risk_flags.append(
            f"{journal_analysis.get('predatory_risk_count', 0)} publication(s) show predatory-risk indicators"
        )
    if publication_analysis.get("verification_coverage", 0) < 35:
        risk_flags.append("Low external verification coverage for publication metadata")
    if topic_variability.get("profile_classification") == "insufficient_data":
        risk_flags.append("Insufficient topic evidence for confident thematic profiling")
    if patents_analysis.get("pending_or_unverified_count", 0) > 0:
        risk_flags.append("Some patent records remain pending/unverified")
    if books_analysis.get("vanity_risk_count", 0) > 0:
        risk_flags.append("Some books show vanity/self-publishing risk indicators")
    if coauthor_analysis.get("solo_authored_count", 0) == publication_analysis.get("journal_count", 0) + publication_analysis.get("conference_count", 0) and publication_analysis.get("journal_count", 0) + publication_analysis.get("conference_count", 0) > 0:
        risk_flags.append("All publications appear solo-authored; collaboration evidence is limited")

    if publication_analysis.get("candidate_visibility_score", 0) >= 75:
        profile_level = "strong_evidence_backed_profile"
    elif publication_analysis.get("candidate_visibility_score", 0) >= 55:
        profile_level = "moderate_profile_with_mixed_evidence"
    else:
        profile_level = "limited_or_uncertain_profile"

    return {
        "profile_level": profile_level,
        "key_indicators": key_indicators,
        "risk_flags": risk_flags,
        "topic_breadth": topic_variability.get("research_breadth", "unknown"),
        "dominant_topic_area": topic_variability.get("dominant_topic_area"),
    }


def _build_book_records(
    books_df: Optional[pd.DataFrame],
    candidate_name: Optional[str],
) -> List[Dict[str, Any]]:
    if books_df is None or books_df.empty:
        return []
    records: List[Dict[str, Any]] = []
    for _, row in books_df.iterrows():
        records.append({
            "book_title": _safe(row.get("book_title")),
            "authors": _safe(row.get("authors")),
            "candidate_authorship_role": _safe(row.get("candidate_authorship_role")),
            "isbn": _safe(row.get("isbn")),
            "publisher": _safe(row.get("publisher")),
            "publication_year": _safe_int(row.get("publication_year")),
            "online_link": _safe(row.get("url")) or _safe(row.get("online_link")),
            "candidate_name": candidate_name,
        })
    return records


def _build_patent_records(patents_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if patents_df is None or patents_df.empty:
        return []
    records: List[Dict[str, Any]] = []
    for _, row in patents_df.iterrows():
        records.append({
            "patent_title": _safe(row.get("patent_title")),
            "patent_number": _safe(row.get("patent_number")),
            "inventors": _safe(row.get("inventors")),
            "candidate_inventor_role": _safe(row.get("candidate_inventor_role")),
            "filing_country": _safe(row.get("filing_country")),
            "date_text": _safe(row.get("date_text")),
            "organization": _safe(row.get("organization")),
            "filing_year": _safe_int(row.get("filing_year")),
            "verification_link": _safe(row.get("url")) or _safe(row.get("verification_link")),
        })
    return records


def _tokenize_topic_text(text: str) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"\b[a-z][a-z0-9\-]{2,}\b", text.lower())
    return [t for t in tokens if t not in TOPIC_STOPWORDS and len(t) > 2]


def _infer_topic_domains(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    token_counter = Counter(tokens)
    scores: Dict[str, float] = {}
    for domain, keywords in TOPIC_DOMAIN_KEYWORDS.items():
        overlap = sum(token_counter[k] for k in keywords if k in token_counter)
        if overlap > 0:
            scores[domain] = float(overlap)
    total = sum(scores.values())
    if total <= 0:
        return {}
    return {k: round((v / total) * 100, 2) for k, v in scores.items()}


def _dominant_domain(domain_scores: Dict[str, float]) -> Optional[str]:
    if not domain_scores:
        return None
    return max(domain_scores.items(), key=lambda x: x[1])[0]


def _prepare_topic_documents(pubs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for i, pub in enumerate(pubs):
        text = " ".join(
            [
                pub.get("paper_title") or "",
                pub.get("abstract_text") or "",
                pub.get("keywords_text") or "",
                pub.get("venue_name") or "",
            ]
        )
        tokens = pub.get("semantic_tokens") or _tokenize_topic_text(text)
        domain_scores = pub.get("domain_scores") or _infer_topic_domains(tokens)
        domains = sorted(domain_scores.keys(), key=lambda d: domain_scores[d], reverse=True)[:2]
        docs.append(
            {
                "id": i,
                "title": pub.get("paper_title") or "Untitled Publication",
                "year": pub.get("publication_year"),
                "venue": (pub.get("venue_name") or "").strip().lower(),
                "tokens": tokens,
                "vector": Counter(tokens),
                "domains": domains or ["unknown_domain"],
            }
        )
    return docs


def _cosine_similarity_matrix(vectors: List[Counter]) -> List[List[float]]:
    n = len(vectors)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    norms = []
    for vec in vectors:
        norms.append(math.sqrt(sum(v * v for v in vec.values())))
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            inter = set(vectors[i].keys()) & set(vectors[j].keys())
            dot = sum(vectors[i][k] * vectors[j][k] for k in inter)
            denom = norms[i] * norms[j]
            sim = 0.0 if denom == 0 else float(dot / denom)
            matrix[i][j] = sim
            matrix[j][i] = sim
    return matrix


def _average_similarity(matrix: List[List[float]]) -> float:
    n = len(matrix)
    if n < 2:
        return 100.0
    values: List[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            values.append(matrix[i][j])
    if not values:
        return 0.0
    return round(mean(values) * 100, 1)


def _cluster_publications(docs: List[Dict[str, Any]], sim_matrix: List[List[float]], threshold: float = 0.24) -> List[int]:
    n = len(docs)
    clusters = [-1 for _ in range(n)]
    current = 0
    for i in range(n):
        if clusters[i] != -1:
            continue
        clusters[i] = current
        stack = [i]
        while stack:
            node = stack.pop()
            for j in range(n):
                if clusters[j] != -1:
                    continue
                if sim_matrix[node][j] >= threshold:
                    clusters[j] = current
                    stack.append(j)
        current += 1
    return clusters


def _build_thematic_clusters(docs: List[Dict[str, Any]], cluster_assignments: List[int]) -> List[Dict[str, Any]]:
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for doc, cid in zip(docs, cluster_assignments):
        grouped[cid].append(doc)
    clusters: List[Dict[str, Any]] = []
    total_docs = max(1, len(docs))
    for cid, members in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        token_counter = Counter()
        domain_counter = Counter()
        years = [m.get("year") for m in members if isinstance(m.get("year"), int)]
        for m in members:
            token_counter.update(m["tokens"])
            domain_counter.update(m["domains"])
        clusters.append(
            {
                "cluster_id": cid,
                "publication_count": len(members),
                "cluster_percentage": round((len(members) / total_docs) * 100, 1),
                "representative_keywords": [k for k, _ in token_counter.most_common(8)],
                "dominant_domains": [d for d, _ in domain_counter.most_common(3)],
                "sample_titles": [m["title"] for m in members[:3]],
                "year_span": [min(years), max(years)] if years else None,
            }
        )
    return clusters


def _domain_percentages(domain_counter: Counter) -> List[Dict[str, Any]]:
    total = sum(domain_counter.values())
    if total <= 0:
        return []
    return [
        {"domain": domain, "count": count, "percentage": round((count / total) * 100, 1)}
        for domain, count in domain_counter.most_common()
    ]


def _topic_concentration_index(topic_percentages: List[Dict[str, Any]]) -> float:
    if not topic_percentages:
        return 0.0
    hhi = sum((t["percentage"] / 100) ** 2 for t in topic_percentages)
    return round(min(100.0, hhi * 100), 1)


def _topic_evolution(docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    by_year: Dict[int, Counter] = defaultdict(Counter)
    for d in docs:
        year = d.get("year")
        if not isinstance(year, int):
            continue
        for dom in d.get("domains", []):
            by_year[year][dom] += 1
    timeline: List[Dict[str, Any]] = []
    transitions = 0
    previous = None
    for year in sorted(by_year):
        dom, count = by_year[year].most_common(1)[0]
        timeline.append({"year": year, "dominant_domain": dom, "paper_count": sum(by_year[year].values())})
        if previous and previous != dom:
            transitions += 1
        previous = dom
    return timeline, transitions


def _classify_topic_profile(concentration: float, domain_count: int, transitions: int) -> str:
    if domain_count <= 1 or concentration >= 70:
        return "highly_specialized"
    if domain_count >= 4 and concentration <= 45 and transitions >= 2:
        return "strongly_interdisciplinary"
    if domain_count >= 2:
        return "moderately_diversified"
    return "insufficient_data"


def _topic_variability_score(
    concentration: float,
    transitions: int,
    domain_count: int,
    avg_similarity: float,
    cluster_count: int,
) -> Tuple[float, List[str]]:
    dispersion = max(0.0, 100.0 - concentration)
    transition_score = min(100.0, transitions * 25.0)
    domain_score = min(100.0, domain_count * 22.0)
    semantic_dispersion = max(0.0, 100.0 - avg_similarity)
    clustering_score = min(100.0, cluster_count * 20.0)
    score = round(
        dispersion * 0.35
        + transition_score * 0.20
        + domain_score * 0.20
        + semantic_dispersion * 0.15
        + clustering_score * 0.10,
        1,
    )
    explanation = [
        f"Concentration/dispersion contribution: {dispersion:.1f} (lower concentration increases variability).",
        f"Topic transitions contribution: {transition_score:.1f} based on {transitions} transition(s).",
        f"Domain spread contribution: {domain_score:.1f} across {domain_count} domain(s).",
        f"Semantic dispersion contribution: {semantic_dispersion:.1f} from average similarity {avg_similarity:.1f}%.",
        f"Thematic clustering contribution: {clustering_score:.1f} from {cluster_count} cluster(s).",
    ]
    return score, explanation


def _coauthor_network_density_proxy(coauthors_per_paper: List[List[str]]) -> float:
    unique_nodes = sorted({c for row in coauthors_per_paper for c in row})
    n = len(unique_nodes)
    if n < 2:
        return 0.0
    edge_set = set()
    for row in coauthors_per_paper:
        uniq = sorted(set(row))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                edge_set.add((uniq[i], uniq[j]))
    possible = n * (n - 1) / 2
    return round(min(100.0, (len(edge_set) / max(possible, 1)) * 100), 1)


def _collaboration_diversity_score(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0 or len(counter) <= 1:
        return 0.0
    entropy = 0.0
    for c in counter.values():
        p = c / total
        entropy -= p * math.log(p, 2)
    max_entropy = math.log(len(counter), 2)
    return round((entropy / max(max_entropy, 1e-9)) * 100, 1)


def _collaboration_consistency(year_to_collab_size: Dict[int, List[int]]) -> float:
    if not year_to_collab_size:
        return 0.0
    yearly_avg = [mean(v) for _, v in sorted(year_to_collab_size.items()) if v]
    if len(yearly_avg) <= 1:
        return 100.0
    avg = mean(yearly_avg)
    if avg == 0:
        return 0.0
    cv = pstdev(yearly_avg) / avg
    return round(max(0.0, 100.0 - min(100.0, cv * 100)), 1)


def _collaboration_strength_index(
    recurring_ratio: float,
    density: float,
    diversity: float,
    solo_count: int,
    publication_count: int,
) -> float:
    solo_penalty = (solo_count / max(publication_count, 1)) * 25
    score = recurring_ratio * 0.35 + density * 0.20 + diversity * 0.30 + (100 - solo_penalty) * 0.15
    return round(max(0.0, min(100.0, score)), 1)


def _classify_collaboration_leadership(role_counter: Counter) -> str:
    total = sum(role_counter.values())
    if total == 0:
        return "insufficient_data"
    lead = role_counter.get("first_author", 0) + role_counter.get("first_and_corresponding_author", 0) + role_counter.get("sole_author", 0)
    middle = role_counter.get("middle_co_author", 0)
    last = role_counter.get("last_author", 0)
    if middle / total >= 0.7:
        return "always_middle_author_behavior"
    if (lead + last) / total >= 0.6 and lead / total >= 0.35:
        return "leadership_oriented_authorship"
    if (lead + last) / total >= 0.45:
        return "collaborative_leadership"
    return "dependent_collaboration_pattern"


def _possible_supervision_pattern(pubs: List[Dict[str, Any]], candidate_norm: str, first_author_names: List[str]) -> str:
    if not pubs:
        return "insufficient_data"
    last_author_count = sum(1 for p in pubs if p.get("candidate_authorship_role") == "last_author")
    first_author_repeats = Counter(first_author_names)
    repeated_first = len([1 for _, c in first_author_repeats.items() if c >= 2])
    if last_author_count >= 2 and repeated_first >= 1:
        return "possible_student_supervisor_pattern"
    if last_author_count >= 1:
        return "possible_senior_guidance_pattern"
    return "not_detected"


def _infer_institutional_collaboration(pubs: List[Dict[str, Any]]) -> str:
    venues = [str(p.get("venue_name") or "").lower() for p in pubs]
    if not venues:
        return "unknown"
    if any("university" in v for v in venues):
        return "institutional_collaboration_possible"
    return "not_enough_institutional_signals"


def _infer_international_collaboration(pubs: List[Dict[str, Any]]) -> str:
    venue_text = " ".join([str(p.get("venue_name") or "") for p in pubs]).lower()
    if re.search(r"\b(usa|uk|europe|asia|international|global|world)\b", venue_text):
        return "possible_international_collaboration"
    return "not_detected_or_insufficient_data"


def _infer_interdisciplinary_collaboration(pubs: List[Dict[str, Any]]) -> str:
    domains = Counter()
    for p in pubs:
        for d in (p.get("domain_scores") or {}).keys():
            domains[d] += 1
    if len(domains) >= 4:
        return "strong_interdisciplinary_collaboration"
    if len(domains) >= 2:
        return "moderate_interdisciplinary_collaboration"
    return "focused_domain_collaboration"


def _infer_book_authorship_role(book: Dict[str, Any]) -> str:
    role = (book.get("candidate_authorship_role") or "").strip().lower()
    if role in {"sole_author", "lead_author", "co_author", "editor", "co-editor"}:
        if role in {"editor", "co-editor"}:
            return "edited_volume_contributor"
        return role
    candidate_norm = _normalize_name(book.get("candidate_name"))
    authors = _split_authors(book.get("authors") or "")
    if not authors:
        return "uncertain"
    normalized = [_normalize_name(a) for a in authors]
    if len(normalized) == 1 and candidate_norm and normalized[0] == candidate_norm:
        return "sole_author"
    if candidate_norm and normalized and normalized[0] == candidate_norm:
        return "lead_author"
    if candidate_norm and candidate_norm in normalized:
        return "co_author"
    return "uncertain"


def _is_valid_isbn(isbn: Optional[str]) -> bool:
    if not isbn:
        return False
    cleaned = re.sub(r"[^0-9Xx]", "", isbn)
    if len(cleaned) == 10:
        return _valid_isbn10(cleaned)
    if len(cleaned) == 13:
        return _valid_isbn13(cleaned)
    return False


def _valid_isbn10(isbn10: str) -> bool:
    if not re.match(r"^\d{9}[\dXx]$", isbn10):
        return False
    total = 0
    for i, ch in enumerate(isbn10):
        v = 10 if ch in {"X", "x"} else int(ch)
        total += v * (10 - i)
    return total % 11 == 0


def _valid_isbn13(isbn13: str) -> bool:
    if not re.match(r"^\d{13}$", isbn13):
        return False
    total = 0
    for i, ch in enumerate(isbn13[:12]):
        total += int(ch) * (1 if i % 2 == 0 else 3)
    check = (10 - (total % 10)) % 10
    return check == int(isbn13[12])


def _classify_book_publisher_type(publisher: Optional[str]) -> str:
    text = (publisher or "").lower().strip()
    if not text:
        return "unknown"
    if any(k in text for k in VANITY_BOOK_INDICATORS):
        return "vanity_or_self_published"
    if any(k in text for k in ACADEMIC_BOOK_PUBLISHER_TERMS):
        return "academic"
    if any(k in text for k in COMMERCIAL_BOOK_PUBLISHER_TERMS):
        return "commercial"
    if any(k in text for k in {"university", "press", "academic"}):
        return "academic"
    return "unknown"


def _infer_patent_role(patent: Dict[str, Any]) -> str:
    role = (patent.get("candidate_inventor_role") or "").lower().strip()
    if role in {"lead_inventor", "first_inventor", "co_inventor", "sole_inventor"}:
        return "lead_inventor" if role in {"lead_inventor", "first_inventor"} else role
    inventors = _split_authors(patent.get("inventors") or "")
    if len(inventors) == 1:
        return "sole_inventor"
    if len(inventors) >= 2:
        return "co_inventor"
    return "uncertain"


def _patent_number_likely_valid(number: Optional[str]) -> bool:
    if not number:
        return False
    return bool(re.search(r"[A-Z]{1,3}\s?\d{4,}", number.upper()))


def _is_patent_verification_link(link: Optional[str]) -> bool:
    if not link:
        return False
    lower = link.lower()
    return any(k in lower for k in {"google.com/patents", "wipo.int", "uspto", "espacenet", "epo.org", "patentscope"})


def _infer_patent_status(patent: Dict[str, Any]) -> str:
    text = " ".join(
        [
            str(patent.get("patent_title") or ""),
            str(patent.get("date_text") or ""),
            str(patent.get("patent_number") or ""),
            str(patent.get("verification_link") or ""),
        ]
    ).lower()
    if any(k in text for k in {"pending", "application", "appln", "filed"}):
        return "pending"
    if any(k in text for k in {"granted", "grant", "issued", "publication"}):
        return "granted_or_published"
    return "unverified"


def _summarize_missing_research_evidence(
    publications: List[Dict[str, Any]],
    books: List[Dict[str, Any]],
    patents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    missing = {
        "publications_missing_doi": sum(1 for p in publications if not p.get("doi")),
        "publications_missing_issn": sum(1 for p in publications if not p.get("issn")),
        "publications_unverified_indexing": sum(
            1 for p in publications if p.get("indexing_status") in {"reported_indexed_unverified", "not_verified"}
        ),
        "books_missing_valid_isbn": sum(1 for b in books if not b.get("isbn_valid")),
        "patents_unverified": sum(1 for p in patents if p.get("verification_status") != "verified"),
    }
    total_gaps = sum(missing.values())
    return {
        "counts": missing,
        "total_evidence_gaps": total_gaps,
        "evidence_reliability_level": "high" if total_gaps == 0 else "moderate" if total_gaps < 5 else "limited",
    }


def _safe(val, default=None):
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    s = str(val).strip()
    return default if s in {"", "nan", "None", "NaN"} else s


def _safe_int(val):
    v = _safe(val)
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    v = _safe(val)
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _safe_bool(val):
    v = _safe(val)
    if v is None:
        return None
    return str(v).strip().lower() in {"true", "1", "yes"}
