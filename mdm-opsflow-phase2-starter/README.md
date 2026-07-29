# MDM OpsFlow — Phase 2 Starter

AI-first bilingual construction operating system starter.

## Included

- FastAPI backend
- Next.js frontend
- Flutter mobile scaffold
- English/Spanish localization
- Super-admin foundation
- Docker Compose

## Run

```bash
docker compose up --build
```

## Container Security: Postgres Image Patching

The local DB service uses an explicit image tag in [docker-compose.yml](docker-compose.yml):

- Default: `postgres:16-alpine3.22`
- Override via env var: `POSTGRES_IMAGE`

When Docker Scout reports CVEs for the Postgres base image, you can patch quickly by bumping the tag without code changes:

```bash
POSTGRES_IMAGE=postgres:16-alpine3.22 docker compose pull db
POSTGRES_IMAGE=postgres:16-alpine3.22 docker compose up -d --build
```

If a newer patched tag is published, replace `16-alpine3.22` with that tag and re-run the commands.

## Railway Deployment (Monorepo)

This repository contains three deployable services with different root folders. If Railway is pointed at the wrong root directory, it will build the wrong image and fail health checks.

### Service 1: Backend API (FastAPI)

- Root directory: `backend`
- Railway config: `backend/railway.toml`
- Dockerfile: `backend/Dockerfile`
- Health check: `/health`
- Start command: `sh /app/start.sh`

Required environment variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `SUPER_ADMIN_EMAIL`
- `SUPER_ADMIN_PASSWORD`
- `ALLOWED_ORIGINS`
- `OPENAI_API_KEY` (optional, required for OCR/AI enrichment)

Expected runtime:

- Binds to `${PORT}` via `uvicorn` in `backend/start.sh`

### Service 2: Frontend App (Next.js)

- Root directory: `frontend`
- Railway config: `frontend/railway.toml`
- Dockerfile: `frontend/Dockerfile`
- Health check: `/`

Required environment variables:

- `NEXT_PUBLIC_API_URL` (must point to the Backend Railway URL)

Expected runtime:

- Binds to `${PORT}` via `npm run start`

### Service 3: Streamlit (Optional)

- Root directory: repository root
- Railway config: `railway.toml`
- Dockerfile: `Dockerfile`
- Health check: `/`

Use this only if you are deploying the Streamlit dashboard. It is separate from the main Next.js frontend.

### Common Railway Failure Pattern

If deployment fails immediately or health checks never pass:

1. Verify each Railway service points to the correct root directory.
2. Verify that service-specific environment variables are set.
3. Confirm frontend `NEXT_PUBLIC_API_URL` targets the backend deployment URL (not localhost).
4. Confirm backend health endpoint returns 200 at `/health`.

## Streamlit

```powershell
& .\.venv311\Scripts\python.exe -m streamlit run streamlit_app.py
```

The Streamlit app is a separate operational dashboard that talks to the FastAPI backend at `http://localhost:8080` by default.

## OpenAPI OperationId Snapshot

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\generate_openapi_operationid_snapshot.py
```

This regenerates `docs/openapi-operationid-snapshot.md` from the current FastAPI app metadata.

## Fast Guardrails

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\run_fast_guardrails.py
```

Runs the quick contract checks for OpenAPI and Streamlit file integrity before heavier integration steps.

In CI, fast-guardrail output is saved as the `backend-fast-guardrails-output` artifact for easier failure triage.

## Replay Token Observability Runbook

See `docs/replay-token-observability-runbook.md` for endpoint contracts, cursor/sort usage, alert-threshold tuning, and bulk revoke governance behavior.

## Validation Baseline

Use these commands as the canonical local validation flow:

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\run_fast_guardrails.py
Set-Location .\backend
..\.venv311\Scripts\python.exe -m pytest -q
```

Current expected baseline:

In CI, use artifact `backend-fast-guardrails-output` to inspect fast-guardrail failures quickly.

Optional fail-closed canary check (intentionally injects a known bad fragment into a temporary in-memory workflow and restores `streamlit_app.py` automatically):

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\verify_streamlit_guardrail_canary.py
```

## PR Checklist

Before opening or updating a PR, run:

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\run_fast_guardrails.py
Set-Location .\backend
..\.venv311\Scripts\python.exe -m pytest -q
```

Expected local result:

- Fast guardrails: `91 passed, 15 deselected`.
- Full backend suite: `106 passed`.
- Warnings: none.

If either command fails, fix issues before push so CI is a confirmation step, not first detection.

## Git Pre-Commit Hook

Enable the repository-managed pre-commit hook so local commits run fast guardrails automatically:

```powershell
git config core.hooksPath .githooks
```

The hook file is [\.githooks\pre-commit](.githooks/pre-commit) and executes [backend/scripts/run_fast_guardrails.py](backend/scripts/run_fast_guardrails.py). If the guardrails fail, the commit is blocked.

The fast script executes `pytest -m guardrail` inside `backend`.

To run only the remaining backend tests (the same split used by CI):

```powershell
Set-Location .\backend
..\.venv311\Scripts\python.exe -m pytest -q -m "not guardrail"
```

## Guardrail Matrix

Streamlit file integrity guardrails live in `backend/tests/test_streamlit_script_syntax.py`.

- `test_streamlit_app_starts_with_future_import`: catches accidental leading characters before the future import.
- `test_streamlit_app_compiles`: catches Python syntax errors.
- `test_streamlit_import_line_present`: enforces one canonical Streamlit import line and rejects partial stream-fragment variants (`import stream...` and `from stream import ...`).
- `test_streamlit_header_has_no_stray_tokens_before_streamlit_import`: blocks unexpected non-empty lines before the Streamlit import.
- `test_streamlit_app_has_no_top_level_bare_name_statements`: catches stray top-level tokens like a lone `n`.
- `test_streamlit_app_has_no_top_level_import_stream_statements`: blocks accidental `import stream` or `from stream import ...`.
- `test_streamlit_import_appears_before_any_st_usage`: ensures import ordering before first `st.` use.
- `test_streamlit_header_prefix_matches_expected`: enforces the canonical first-lines header/import block.
- `test_streamlit_header_prefix_is_ascii_only`: enforces ASCII-only content in the pre-import header block to reduce Unicode lookalike corruption risk.
- `test_streamlit_app_does_not_contain_known_corruption_fingerprint_lines`: explicitly blocks known bad lines `n` and `import stream`.
- `test_streamlit_app_does_not_contain_known_corruption_sequence`: blocks the specific sequence pattern of a lone `n` followed by `import stream` later in the file.
- Sequence detection uses AST-first logic (including semicolon variants like `n; import stream`) with a line-based fallback for malformed snippets.
- Detector regression tests (`test_known_corruption_fingerprint_detector_*`, `test_known_corruption_sequence_detector_*`, and `test_known_corruption_fingerprint_detector_matrix`) validate spacing/comment/alias/from-import/wildcard variants and protect against false positives like `import streamlit as st`.

## Hardening Summary

Current guardrail coverage includes:

- Streamlit prologue and import-shape integrity checks (header prefix, canonical import, AST-level invariants, hidden-byte/control-character checks).
- CI workflow drift checks (trigger paths, marker split, artifact upload wiring, manual dispatch, Python setup pin).
- Local hook drift checks for `.githooks/pre-commit` including repo-root resolution and interpreter fallback chain.
- Documentation/process drift checks for README validation guidance and PR template baseline alignment.
- Fail-closed mutation canary via `backend/scripts/verify_streamlit_guardrail_canary.py` with automatic `streamlit_app.py` restore.

Latest local consolidation run in this session:

- Fast guardrails: `91 passed, 15 deselected`
- Full backend suite: `106 passed`

## Guardrail Failure Playbook

When a Streamlit guardrail fails, use this quick flow:

1. Re-run the fast suite locally:

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\run_fast_guardrails.py
```

1. If CI failed, download artifact `backend-fast-guardrails-output` and inspect the first failing test.

1. Map common failures to fixes:

   - Header prefix/import order tests failing: restore the canonical top block in [streamlit_app.py](streamlit_app.py) so `from __future__ import annotations` stays first and `import streamlit as st  # pyright: ignore[reportMissingImports]` remains in the expected position.
   - Partial/fragment import failures (`import stream`, `from stream import ...`): remove the fragment and restore the canonical Streamlit import line.
   - Bare token failures (lone `n`): remove stray top-level tokens introduced by merge/conflict or copy-paste.
   - ASCII/header integrity failures: replace lookalike Unicode characters in the header block with plain ASCII.

1. Re-run the fast suite, then commit.

## OCR And AI Setup

1. Create a root `.env` file from `.env.example`.
2. Paste your OpenAI key into `OPENAI_API_KEY` in that file.
3. Restart the stack with `docker compose up --build`.

If `OPENAI_API_KEY` is not set, uploads still work, but OCR and AI summarization for scanned files and images will stay limited.

Backend: <http://localhost:8080/docs>

Frontend: <http://localhost:3000>
