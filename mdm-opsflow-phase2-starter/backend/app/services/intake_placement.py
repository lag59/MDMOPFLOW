from __future__ import annotations

from dataclasses import dataclass

from app.models import IntakeItem
from app.services.canonical_intake import (
    build_canonical_document,
    has_estimator_signals,
    score_canonical_document,
)


@dataclass(frozen=True)
class IntakePlacementSuggestion:
    destination_key: str
    destination_label: str
    destination_href: str
    confidence: float
    reason: str
    signal_source: str


DESTINATION_CATALOG: dict[str, tuple[str, str]] = {
    "tickets": ("Tickets workspace", "/tickets"),
    "estimator": ("Estimator workspace", "/estimator"),
    "accounting": ("Accounting invoice intake", "/modules/accounting/ap-invoice-intake"),
    "vendor": ("Vendor portal", "/vendor"),
    "safety": ("Safety module", "/modules/safety_manager/incidents"),
    "extraction_queue": ("Extraction queue review", "/extraction-queue"),
}


def _build_suggestion(
    destination_key: str,
    *,
    confidence: float,
    reason: str,
    signal_source: str,
) -> IntakePlacementSuggestion:
    label, href = DESTINATION_CATALOG[destination_key]
    return IntakePlacementSuggestion(
        destination_key=destination_key,
        destination_label=label,
        destination_href=href,
        confidence=max(0.0, min(confidence, 1.0)),
        reason=reason,
        signal_source=signal_source,
    )


def suggest_intake_placement(item: IntakeItem) -> IntakePlacementSuggestion:
    canonical = build_canonical_document(item)
    scores = score_canonical_document(canonical)
    classification_confidence = float(item.classification_confidence or 0.0)

    ranked_scores = sorted(
        (
            ("estimator", scores.estimator_document_score),
            ("accounting", scores.accounting_document_score),
            ("tickets", scores.operational_ticket_score),
        ),
        key=lambda entry: entry[1],
        reverse=True,
    )
    _, top_score = ranked_scores[0]
    second_score = ranked_scores[1][1]

    # Strong estimating/accounting intent should still surface the right destination
    # even when extraction confidence requires review before operational placement.
    if scores.estimator_document_score >= 0.75:
        return _build_suggestion(
            "estimator",
            confidence=scores.estimator_document_score,
            reason=(
                "Estimator signals met routing threshold "
                f"(score={scores.estimator_document_score:.2f}, type={canonical.document_type}/{canonical.document_subtype})."
            ),
            signal_source=("canonical+priority+review_gate" if item.needs_review or classification_confidence < 0.75 else "canonical+priority"),
        )

    if scores.accounting_document_score >= 0.80:
        return _build_suggestion(
            "accounting",
            confidence=scores.accounting_document_score,
            reason=(
                "Accounting signals met routing threshold "
                f"(score={scores.accounting_document_score:.2f}, type={canonical.document_type})."
            ),
            signal_source=("canonical+priority+review_gate" if item.needs_review or classification_confidence < 0.75 else "canonical+priority"),
        )

    if item.needs_review or classification_confidence < 0.75:
        return _build_suggestion(
            "extraction_queue",
            confidence=max(0.74, top_score),
            reason="Extraction needs reviewer confirmation before operational routing.",
            signal_source="review_gate",
        )

    if top_score >= 0.75 and (top_score - second_score) < 0.07:
        return _build_suggestion(
            "extraction_queue",
            confidence=top_score,
            reason="Signals conflict across modules and require reviewer confirmation.",
            signal_source="score_conflict_gate",
        )

    if scores.operational_ticket_score >= 0.85:
        return _build_suggestion(
            "tickets",
            confidence=scores.operational_ticket_score,
            reason=(
                "Operational ticket signals met routing threshold "
                f"(score={scores.operational_ticket_score:.2f})."
            ),
            signal_source="canonical+priority",
        )

    if any(token in canonical.summary for token in ("safety", "incident", "osha")) or any(
        token in canonical.extracted_text for token in ("near miss", "incident", "osha", "safety")
    ):
        return _build_suggestion(
            "safety",
            confidence=0.79,
            reason="Safety-related indicators were detected in OCR text.",
            signal_source="summary+text",
        )

    return _build_suggestion(
        "extraction_queue",
        confidence=0.55,
        reason="No strong routing signal was detected; manual review is recommended.",
        signal_source="fallback",
    )
