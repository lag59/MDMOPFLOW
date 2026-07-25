# Next Sprints

See detailed Phase 2 blueprint: docs/phase2-product-blueprint.md

## Sprint 1
Authentication, PostgreSQL models, tenant isolation, super-admin permissions, company onboarding, projects, bilingual localization.

## Sprint 2
AI Intake Hub, file storage, ticket extraction, review queue, duplicate detection, audit lineage.

Replay token observability and governance references:
- docs/replay-token-observability-runbook.md

Latest delivered increment:
- Intake operator UI now enforces a required reason for live stale-token bulk revoke and supports audit-trail filtering by action, actor, token, and UTC time window.
- Replay-token audit history pagination now uses deterministic created_at + audit-log-id cursors, and intake UI supports load-more for audit rows.
- Replay-token audit history now also has a body-envelope list endpoint with `has_more` and cursor fields, plus server-side `limit` cap enforcement.
- Replay-token audit history list now supports sort direction (`-created_at` and `+created_at`) with cursor-correct paging and intake UI sort controls.

## Sprint 3
Budgets, cost codes, analytics, mobile capture, notifications, offline queue.
