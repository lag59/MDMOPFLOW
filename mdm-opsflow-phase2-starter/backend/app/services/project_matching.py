from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project
from app.services.canonical_intake import CanonicalDocument

ABBREVIATION_MAP = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "rdg": "ridge",
    "pk": "park",
    "ph": "phase",
    "ctr": "center",
    "ct": "court",
    "st": "street",
    "ave": "avenue",
}

STOPWORDS = {"project", "the", "at", "of", "and", "site"}


@dataclass(frozen=True)
class ProjectMatchCandidate:
    project_id: str
    project_name: str
    project_number: str
    confidence: float
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectMatchResult:
    matched_project_id: str | None
    match_confidence: float
    matching_evidence: tuple[str, ...] = ()
    alternative_matches: tuple[ProjectMatchCandidate, ...] = ()
    auto_associate: bool = False


def _normalize_project_name(value: str) -> str:
    tokens = re.split(r"[^a-z0-9]+", value.lower())
    expanded: list[str] = []
    for token in tokens:
        token = token.strip(".")
        if not token or token in STOPWORDS:
            continue
        expanded.append(ABBREVIATION_MAP.get(token, token))
    return " ".join(expanded)


def _token_set(value: str) -> set[str]:
    if not value:
        return set()
    return set(value.split())


def _clamp(value: float) -> float:
    return max(0.0, min(value, 1.0))


def _parse_document_date(canonical_doc: CanonicalDocument) -> datetime | None:
    value = (canonical_doc.dates.get("quote_date", "") or canonical_doc.dates.get("invoice_date", "")).strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _score_candidate(canonical_doc: CanonicalDocument, project: Project) -> tuple[float, list[str]]:
    score = 0.0
    evidence: list[str] = []

    doc_project_number = (canonical_doc.project.get("project_number", "") or "").strip().lower()
    project_number = (project.project_number or "").strip().lower()
    if doc_project_number and project_number and doc_project_number == project_number:
        score += 0.80
        evidence.append("Exact project number match")

    doc_project_name = (canonical_doc.project.get("project_name", "") or "").strip()
    project_name = (project.project_name or "").strip()
    if doc_project_name and project_name and doc_project_name.lower() == project_name.lower():
        score += 0.26
        evidence.append("Exact project name match")

    normalized_doc_name = _normalize_project_name(doc_project_name)
    normalized_project_name = _normalize_project_name(project_name)
    if normalized_doc_name and normalized_project_name:
        ratio = SequenceMatcher(None, normalized_doc_name, normalized_project_name).ratio()
        overlap = _token_set(normalized_doc_name)
        project_tokens = _token_set(normalized_project_name)
        jaccard = len(overlap & project_tokens) / max(1, len(overlap | project_tokens))

        name_score = max(ratio, jaccard)
        if name_score >= 0.68:
            score += min(0.3, name_score * 0.3)
            evidence.append(f"Normalized name similarity={name_score:.2f}")

    doc_owner_or_gc = (
        canonical_doc.entities.get("owner", "")
        or canonical_doc.entities.get("general_contractor", "")
        or canonical_doc.entities.get("customer", "")
    ).strip()
    if doc_owner_or_gc and project.customer and doc_owner_or_gc.lower() in project.customer.lower():
        score += 0.07
        evidence.append("Owner/GC signal aligned with project customer")

    doc_location = (
        canonical_doc.entities.get("location", "")
        or canonical_doc.entities.get("job_location", "")
        or canonical_doc.entities.get("address", "")
    ).strip()
    if doc_location and project.address and any(part and part in project.address.lower() for part in _normalize_project_name(doc_location).split()):
        score += 0.06
        evidence.append("Location signal aligned")

    doc_date = _parse_document_date(canonical_doc)
    if doc_date and project.start_date:
        delta_days = abs((project.start_date.replace(tzinfo=None) - doc_date).days)
        if delta_days <= 120:
            score += 0.05
            evidence.append("Bid/document date near project start")

    doc_vendor = (canonical_doc.vendor.get("name", "") or "").strip().lower()
    if doc_vendor and doc_vendor in (project.description or "").lower():
        score += 0.03
        evidence.append("Vendor reference appears in project description")

    return _clamp(score), evidence


def match_document_to_projects(
    db: Session,
    *,
    tenant_id: str,
    canonical_doc: CanonicalDocument,
    auto_associate_threshold: float = 0.78,
) -> ProjectMatchResult:
    projects = list(
        db.scalars(
            select(Project).where(Project.tenant_id == tenant_id)
        ).all()
    )
    if not projects:
        return ProjectMatchResult(matched_project_id=None, match_confidence=0.0, matching_evidence=(), alternative_matches=(), auto_associate=False)

    candidates: list[ProjectMatchCandidate] = []
    for project in projects:
        confidence, evidence = _score_candidate(canonical_doc, project)
        if confidence <= 0:
            continue
        candidates.append(
            ProjectMatchCandidate(
                project_id=project.id,
                project_name=project.project_name,
                project_number=project.project_number,
                confidence=confidence,
                evidence=tuple(evidence),
            )
        )

    if not candidates:
        return ProjectMatchResult(matched_project_id=None, match_confidence=0.0, matching_evidence=(), alternative_matches=(), auto_associate=False)

    ranked = sorted(candidates, key=lambda item: item.confidence, reverse=True)
    best = ranked[0]
    alternatives = tuple(ranked[1:4])

    return ProjectMatchResult(
        matched_project_id=best.project_id,
        match_confidence=best.confidence,
        matching_evidence=best.evidence,
        alternative_matches=alternatives,
        auto_associate=best.confidence >= auto_associate_threshold,
    )
