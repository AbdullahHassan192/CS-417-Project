from __future__ import annotations

import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
_project_root = Path(__file__).resolve().parent.parent


def _groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _post_groq_json(prompt: str, temperature: float = 0.0, max_tokens: int = 600) -> Optional[Dict[str, Any]]:
    key = _groq_key()
    if not key:
        return None
    payload = {
        "model": GROQ_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": "Return only strict JSON object. No markdown. No extra text.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        GROQ_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None
    choices = raw.get("choices", []) if isinstance(raw, dict) else []
    if not choices:
        return None
    content = (((choices[0] or {}).get("message") or {}).get("content") or "").strip()
    return _extract_json_block(content)


def _load_context_text(candidates: List[Path]) -> str:
    for p in candidates:
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                continue
    return "{}"


def _deterministic_high_rank(seed_text: str) -> int:
    seed_hash = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    seed_int = int(seed_hash[:8], 16)
    rng = random.Random(seed_int)
    return rng.randint(800, 1000)


def resolve_university_rank_with_groq(institution_name: str) -> Dict[str, Any]:
    context_text = _load_context_text(
        [
            _project_root / "data" / "UniversityRankings.json",
            _project_root / "data" / "university_rankings.json",
        ]
    )
    prompt = (
        "Given this university ranking context JSON and institution name, return JSON with keys:\n"
        "{matched_name, qs_rank, the_rank, found_in_context, confidence}\n"
        "Rules:\n"
        "1) If institution exists in context, return its ranks.\n"
        "2) If not found, keep qs_rank and the_rank null.\n"
        "3) Do not invent names.\n\n"
        f"Institution: {institution_name}\n\n"
        f"Context JSON:\n{context_text}"
    )
    parsed = _post_groq_json(prompt)
    qs = _safe_rank((parsed or {}).get("qs_rank"))
    the = _safe_rank((parsed or {}).get("the_rank"))
    if qs is None:
        qs = _deterministic_high_rank(institution_name + "|qs")
    if the is None:
        the = _deterministic_high_rank(institution_name + "|the")
    return {
        "matched_name": (parsed or {}).get("matched_name") or institution_name,
        "qs_rank": qs,
        "the_rank": the,
        "found_in_context": bool((parsed or {}).get("found_in_context")),
        "confidence": (parsed or {}).get("confidence"),
        "source": "groq_context" if parsed else "random_fallback",
    }


def resolve_journal_rank_with_groq(journal_name: str, issn: Optional[str] = None) -> Dict[str, Any]:
    context_text = _load_context_text(
        [
            _project_root / "data" / "JournalRankings.json",
            _project_root / "data" / "journal_rankings.json",
            _project_root / "data" / "journal_indexing_reference.json",
        ]
    )
    prompt = (
        "Given ranking context JSON and journal name/ISSN, return JSON with keys:\n"
        "{matched_name, sjr_rank, quartile, found_in_context, confidence}\n"
        "Rules:\n"
        "1) If found in context, return rank/quartile.\n"
        "2) If not found, keep sjr_rank and quartile null.\n"
        "3) Quartile must be one of Q1,Q2,Q3,Q4 when present.\n\n"
        f"Journal name: {journal_name}\n"
        f"ISSN: {issn or ''}\n\n"
        f"Context JSON:\n{context_text}"
    )
    parsed = _post_groq_json(prompt)
    sjr_rank = _safe_rank((parsed or {}).get("sjr_rank"))
    quartile = _safe_quartile((parsed or {}).get("quartile"))
    if sjr_rank is None:
        sjr_rank = _deterministic_high_rank((journal_name or "") + "|" + (issn or "") + "|sjr")
    if quartile is None:
        quartile = "Q4"
    return {
        "matched_name": (parsed or {}).get("matched_name") or journal_name,
        "sjr_rank": sjr_rank,
        "quartile": quartile,
        "found_in_context": bool((parsed or {}).get("found_in_context")),
        "confidence": (parsed or {}).get("confidence"),
        "source": "groq_context" if parsed else "random_fallback",
    }


def infer_publication_topics_with_groq(publication_titles: List[str]) -> Optional[Dict[str, Any]]:
    titles = [t.strip() for t in publication_titles if t and t.strip()]
    if not titles:
        return None
    prompt = (
        "Given publication titles, infer major research domains.\n"
        "Return strict JSON with keys:\n"
        "{domains: [{domain, percentage}], dominant_domain, notes}\n"
        "Rules:\n"
        "1) Percentages should sum roughly to 100.\n"
        "2) Use concise domain labels.\n"
        "3) Base only on titles.\n\n"
        f"Titles:\n{json.dumps(titles, ensure_ascii=True)}"
    )
    parsed = _post_groq_json(prompt, temperature=0.1, max_tokens=500)
    if not parsed:
        return None
    domains = parsed.get("domains")
    if not isinstance(domains, list):
        return None
    cleaned = []
    for d in domains:
        if not isinstance(d, dict):
            continue
        name = str(d.get("domain", "")).strip().lower().replace(" ", "_")
        pct = d.get("percentage")
        try:
            pct_val = float(pct)
        except (TypeError, ValueError):
            continue
        if not name:
            continue
        cleaned.append({"domain": name, "percentage": max(0.0, min(100.0, pct_val))})
    if not cleaned:
        return None
    return {
        "domains": cleaned,
        "dominant_domain": str(parsed.get("dominant_domain", "")).strip().lower().replace(" ", "_") or cleaned[0]["domain"],
        "notes": parsed.get("notes"),
    }


def _safe_rank(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        x = int(value)
        return x if x > 0 else None
    s = str(value)
    m = re.search(r"\d{1,4}", s)
    if not m:
        return None
    x = int(m.group(0))
    return x if x > 0 else None


def _safe_quartile(value: Any) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip().upper()
    m = re.search(r"\bQ([1-4])\b", s)
    return f"Q{m.group(1)}" if m else None
