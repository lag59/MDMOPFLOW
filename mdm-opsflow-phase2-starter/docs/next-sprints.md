# Next Sprints

See detailed Phase 2 blueprint: docs/phase2-product-blueprint.md

## Sprint 1
Authentication, PostgreSQL models, tenant isolation, super-admin permissions, company onboarding, projects, bilingual localization.

## Sprint 2
AI Intake Hub, file storage, ticket extraction, review queue, duplicate detection, audit lineage.

Replay token observability and governance references:
- docs/replay-token-observability-runbook.md

Latest delivered increment:
- Intake audit export now requires a selected time window, with an inline `Export scope` hint that explains export uses the current audit time window and prompts operators to set a preset or timestamps first.
- Intake audit panel now shows a compact `Active scope` summary line (action, window preset, actor, token, and time range) that updates live and returns to defaults after `Reset audit filters`.
- Intake audit panel now includes `Reset audit filters` to restore default audit scope/controls in one click and immediately refresh unscoped history, summary, and trend queries.
- Intake audit window preset selector is now grouped by horizon (`Hours`, `Days and months`, `Years and long-range`) and long-range labels now include year equivalents for faster operator scanning.
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
- Intake audit window presets now include `last 120 hours` for five-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 144 hours` for six-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 168 hours` for seven-day operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 14 days` for two-week operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 21 days` for three-week operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 28 days` for four-week operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 60 days` for two-month operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 90 days` for quarterly operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 180 days` for half-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 365 days` for annual operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 730 days` for two-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 1095 days` for three-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 1460 days` for four-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 1825 days` for five-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 3650 days` for ten-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 7300 days` for twenty-year operational slices, with deterministic UTC query propagation coverage.
- Intake audit window presets now include `last 10950 days` for thirty-year operational slices, with deterministic UTC query propagation coverage.

## Sprint 3
Budgets, cost codes, analytics, mobile capture, notifications, offline queue.
