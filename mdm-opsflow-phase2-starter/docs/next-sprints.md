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
- Replay-token audit history now has a summary endpoint with action totals, unique actors, and latest-event timestamp; intake audit panel now shows these metrics for the active filter scope.
- Replay-token audit summary now includes consume/revoke percentage KPIs (relative to issue count), and intake audit cards display these rates for the active filter scope.
- Intake audit trend panel now includes an operator-selectable granularity control (`day`/`hour`) that is propagated to trends API requests.
- Intake audit filters now include window presets (`all time`, `last 24 hours`, `last 7 days`, `last 30 days`, `custom`) that auto-fill UTC timestamps for faster scoped refreshes.
- Intake audit window presets now include `last 1 hour` for incident-time slices, with deterministic UTC start/end propagation to audit history requests.
- Intake audit window presets now include `last 6 hours` for short-range investigations, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 12 hours` for half-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 48 hours` for two-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 72 hours` for three-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 96 hours` for four-day operational slices, with deterministic UTC query propagation coverage.

## Sprint 3
Budgets, cost codes, analytics, mobile capture, notifications, offline queue.
