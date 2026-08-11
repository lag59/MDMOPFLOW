# Release Notes

## 2026-08-11 - Production Incident Closure

- Deployment `2549c66a-c570-41aa-90cf-b8ee10397ecb` reached `SUCCESS` on Railway for backend service `MDMOPFLOW`.
- Alembic migration `20260811_0013` was applied in production (`20260729_0012 -> 20260811_0013`).
- Canonical fix shipped: migration-first schema alignment for `daily_field_reports` and `tickets.source_document_path`.
- Runtime safeguard retained in backend routes to reduce blast radius if future environments lag migrations.
- Incident closed: `/api/daily-field-reports/assist` and `/api/tickets` now pass post-deploy smoke checks (HTTP 200).
