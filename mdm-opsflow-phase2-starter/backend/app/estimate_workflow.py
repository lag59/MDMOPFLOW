from __future__ import annotations

from dataclasses import dataclass


ESTIMATE_STATUS_DRAFT = "Draft"
ESTIMATE_STATUS_PENDING_REVIEW = "Pending Review"
ESTIMATE_STATUS_SUBMITTED = "Submitted"
ESTIMATE_STATUS_UNDER_REVIEW = "Under Review"
ESTIMATE_STATUS_AWARDED = "Awarded"
ESTIMATE_STATUS_CONTRACT_EXECUTED = "Contract Executed"
ESTIMATE_STATUS_CONVERTED_TO_PROJECT = "Converted to Project"


ESTIMATE_STATUS_ALIASES: dict[str, str] = {
    "new": ESTIMATE_STATUS_DRAFT,
    "draft": ESTIMATE_STATUS_DRAFT,
    "draft estimate": ESTIMATE_STATUS_DRAFT,
    "internal review": ESTIMATE_STATUS_PENDING_REVIEW,
    "pending review": ESTIMATE_STATUS_PENDING_REVIEW,
    "submitted": ESTIMATE_STATUS_SUBMITTED,
    "approved for submission": ESTIMATE_STATUS_UNDER_REVIEW,
    "under review": ESTIMATE_STATUS_UNDER_REVIEW,
    "awarded": ESTIMATE_STATUS_AWARDED,
    "contract executed": ESTIMATE_STATUS_CONTRACT_EXECUTED,
    "converted to project": ESTIMATE_STATUS_CONVERTED_TO_PROJECT,
}


VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ESTIMATE_STATUS_DRAFT: {ESTIMATE_STATUS_PENDING_REVIEW},
    ESTIMATE_STATUS_PENDING_REVIEW: {ESTIMATE_STATUS_SUBMITTED, ESTIMATE_STATUS_DRAFT},
    ESTIMATE_STATUS_SUBMITTED: {ESTIMATE_STATUS_UNDER_REVIEW, ESTIMATE_STATUS_DRAFT},
    ESTIMATE_STATUS_UNDER_REVIEW: {ESTIMATE_STATUS_AWARDED, ESTIMATE_STATUS_DRAFT},
    ESTIMATE_STATUS_AWARDED: {ESTIMATE_STATUS_CONTRACT_EXECUTED, ESTIMATE_STATUS_CONVERTED_TO_PROJECT},
    ESTIMATE_STATUS_CONTRACT_EXECUTED: {ESTIMATE_STATUS_CONVERTED_TO_PROJECT},
    ESTIMATE_STATUS_CONVERTED_TO_PROJECT: set(),
}


LOCKING_STATUSES: set[str] = {
    ESTIMATE_STATUS_AWARDED,
    ESTIMATE_STATUS_CONTRACT_EXECUTED,
    ESTIMATE_STATUS_CONVERTED_TO_PROJECT,
}


@dataclass(frozen=True)
class TransitionValidationResult:
    current_status: str
    target_status: str


def normalize_estimate_status(raw_status: str) -> str:
    normalized = (raw_status or "").strip().lower()
    return ESTIMATE_STATUS_ALIASES.get(normalized, raw_status.strip())


def validate_estimate_transition(current_status: str, target_status: str) -> TransitionValidationResult:
    normalized_current = normalize_estimate_status(current_status)
    normalized_target = normalize_estimate_status(target_status)

    allowed = VALID_STATUS_TRANSITIONS.get(normalized_current)
    if allowed is None:
        raise ValueError(f"Unknown estimate status '{current_status}'")
    if normalized_target not in VALID_STATUS_TRANSITIONS:
        raise ValueError(f"Unknown target status '{target_status}'")
    if normalized_target not in allowed:
        allowed_display = ", ".join(sorted(allowed)) if allowed else "none"
        raise ValueError(
            f"Illegal estimate status transition: {normalized_current} -> {normalized_target}. "
            f"Allowed targets: {allowed_display}."
        )

    return TransitionValidationResult(
        current_status=normalized_current,
        target_status=normalized_target,
    )


def is_locking_status(status_value: str) -> bool:
    return normalize_estimate_status(status_value) in LOCKING_STATUSES
