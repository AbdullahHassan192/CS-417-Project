from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_project_root = Path(__file__).resolve().parent.parent
_qs_ranks_file = _project_root / "data" / "qs_ranks.json"
_journal_ranks_file = _project_root / "data" / "journal_ranks.json"

_NAME_STOPWORDS = {
    "the", "of", "and", "for", "in", "at", "university", "institute",
    "college", "school", "department", "faculty", "center", "centre",
}


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[\(\)\[\],.\-_/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(value: str) -> List[str]:
    toks = [t for t in _normalize_text(value).split() if t and t not in _NAME_STOPWORDS and len(t) > 2]
    return toks


def _token_overlap_score(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _regex_phrase_match(query_tokens: List[str], candidate_norm: str) -> bool:
    if len(query_tokens) < 2:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(t) for t in query_tokens[:6]) + r"\b"
    return bool(re.search(pattern, candidate_norm))


@lru_cache(maxsize=1)
def _load_qs_rows() -> List[Dict[str, Any]]:
    if not _qs_ranks_file.exists():
        return []
    try:
        data = json.loads(_qs_ranks_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rows: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        rank = item.get("rank")
        if not name:
            continue
        try:
            rank_int = int(float(rank))
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "name": name,
                "rank": rank_int,
                "name_norm": _normalize_text(name),
                "tokens": _tokens(name),
            }
        )
    return rows


@lru_cache(maxsize=1)
def _load_journal_rows() -> List[Dict[str, Any]]:
    if not _journal_ranks_file.exists():
        return []
    try:
        data = json.loads(_journal_ranks_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rows: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or item.get("name") or "").strip().strip('"')
        rank = item.get("rank")
        quartile_raw = item.get("quartile")
        if not name:
            continue
        try:
            rank_int = int(float(rank))
        except (TypeError, ValueError):
            continue
        quartile = _parse_quartile(quartile_raw)
        rows.append(
            {
                "name": name,
                "rank": rank_int,
                "quartile": quartile,
                "name_norm": _normalize_text(name),
                "tokens": _tokens(name),
            }
        )
    return rows


def resolve_university_rank_regex(institution_name: str) -> Optional[Dict[str, Any]]:
    query_norm = _normalize_text(institution_name)
    query_tokens = _tokens(institution_name)
    if not query_norm or not query_tokens:
        return None

    best = None
    best_score = 0.0
    for row in _load_qs_rows():
        score = _token_overlap_score(query_tokens, row["tokens"])
        if query_norm == row["name_norm"]:
            score = 1.0
        elif _regex_phrase_match(query_tokens, row["name_norm"]) or _regex_phrase_match(row["tokens"], query_norm):
            score = max(score, 0.82)
        if score > best_score:
            best_score = score
            best = row

    if not best or best_score < 0.60:
        return None
    return {
        "matched_name": best["name"],
        "rank": best["rank"],
        "confidence": round(best_score, 3),
    }


def resolve_journal_rank_regex(journal_name: str) -> Optional[Dict[str, Any]]:
    query_norm = _normalize_text(journal_name)
    query_tokens = _tokens(journal_name)
    if not query_norm or not query_tokens:
        return None

    best = None
    best_score = 0.0
    for row in _load_journal_rows():
        score = _token_overlap_score(query_tokens, row["tokens"])
        if query_norm == row["name_norm"]:
            score = 1.0
        elif _regex_phrase_match(query_tokens, row["name_norm"]) or _regex_phrase_match(row["tokens"], query_norm):
            score = max(score, 0.82)
        if score > best_score:
            best_score = score
            best = row

    if not best or best_score < 0.58:
        return None
    return {
        "matched_name": best["name"],
        "rank": best["rank"],
        "quartile": best.get("quartile"),
        "confidence": round(best_score, 3),
    }


def _parse_quartile(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    m = re.search(r"\bQ([1-4])\b", text)
    if m:
        return f"Q{m.group(1)}"
    m2 = re.search(r"\b([1-4])\b", text)
    if m2:
        return f"Q{m2.group(1)}"
    return None
