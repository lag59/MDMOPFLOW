# Frontend to Backend API Map

This map tracks the primary live-data contracts between the Next.js frontend and FastAPI backend.

## Shared Auth and Tenant Context

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/lib/auth.ts` | `POST /api/auth/login` | Sign in and store access/refresh tokens. |
| `frontend/lib/auth.ts` | `POST /api/auth/refresh` | Refresh expired sessions before retrying protected calls. |
| `frontend/lib/roleAccess.ts`, `AppShell`, dashboard/settings pages | `GET /api/auth/me` | Hydrate current user, platform role, memberships, and tenant context. |

## Workspace and Dashboard

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/app/dashboard/page.tsx` | `GET /api/auth/me` | Live greeting and user context. |
| `frontend/app/dashboard/page.tsx` | `GET /api/dashboard/role-experience` | Role-specific KPI order, modules, quick actions, and alerts. |
| `frontend/app/dashboard/page.tsx` | `GET /api/projects` | Project pipeline, active-project count, and health signal. |
| `frontend/app/dashboard/page.tsx` | `GET /api/tickets` | Open-ticket stats and ticket activity. |
| `frontend/app/dashboard/page.tsx` | `GET /api/estimates` | Estimate snapshot and bid activity. |
| `frontend/app/dashboard/page.tsx` | `GET /api/intake/items` | Recent documents, document activity, and review-pressure stats. |
| `frontend/app/workspace/page.tsx` | `GET /api/customers`, `/api/employees`, `/api/equipment`, `/api/trucks`, `/api/materials`, `/api/projects`, `/api/daily-field-reports` | Workspace resource browser and create forms. |

## Intake and Extraction

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/app/intake/page.tsx` | `GET /api/intake/items`, `POST /api/intake/upload` | Intake list and upload flow. |
| `frontend/app/intake/page.tsx`, `frontend/components/ExtractionReview.tsx` | `POST /api/intake/placement/suggest`, `POST /api/intake/conflicts/suggest` | AI routing and conflict review. |
| `frontend/components/ExtractionReview.tsx` | `GET /api/extractions/{id}`, `POST /api/extractions/{id}/review`, `POST /api/extractions/{id}/approve`, `POST /api/extractions/{id}/validate` | Review, correction, approval, rejection, and validation workflow. |
| `frontend/components/ExtractionReview.tsx` | `GET /api/intake/items/{item_id}/file` | Authenticated source document preview. |
| `frontend/lib/documentIntake.ts` | `GET /api/document-intake/config`, `POST /api/document-intake` | Strict document-intake OCR routing contract. |

## Operations

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/app/projects/**` | `GET/POST/PATCH/DELETE /api/projects`, `GET /api/projects/{id}/profitability`, `GET /api/projects/{id}/tickets` | Project management and project dashboards. |
| `frontend/app/tickets/page.tsx`, `frontend/lib/tickets.ts` | `GET/POST/PATCH/DELETE /api/tickets`, `POST /api/tickets/quantity-calculation`, `GET /api/tickets/material-density-presets`, `POST /api/tickets/upload-extract` | Ticket CRUD, calculator, density presets, and OCR ticket extraction. |
| `frontend/app/daily-production/page.tsx` | `GET/POST/PATCH /api/daily-field-reports`, `POST /api/daily-field-reports/assist` | Daily production and AI/weather-assisted field reporting. |
| `frontend/app/ai-assignment/page.tsx`, modules page | `POST /api/ai/workflow/route`, `POST /api/ai/tickets/auto-assign`, `GET /api/ai/tickets/{ticket_id}/project-suggestions` | AI routing and project assignment. |

## Estimator, Finance, and Vendor

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/app/estimator/page.tsx`, `frontend/lib/estimator.ts` | `GET/POST /api/estimates`, `POST /api/estimates/{id}/ai-assist`, `POST /api/estimates/{id}/ai-review` | Estimate CRUD and AI review/assist. |
| `frontend/lib/estimator.ts` | `/api/estimator/takeoffs`, `/api/estimator/versions`, `/api/estimator/bid-pipeline`, `/api/estimator/win-loss`, `/api/estimator/summary` | Estimator module surfaces. |
| `frontend/app/accounting/page.tsx` | `POST /api/invoices/generate` | Generate project invoice from approved tickets. |
| `frontend/lib/payroll.ts` | `/api/payroll/timecards`, `/api/payroll/runs`, `/api/payroll/summary` | Payroll module surfaces. |
| `frontend/app/vendor/page.tsx`, `frontend/lib/vendor.ts` | `/api/vendor/purchase-orders`, `/api/vendor/invoice-submissions`, `/api/vendor/delivery-records`, `/api/vendor/compliance-documents` | Vendor portal data. |

## Administration

| Frontend surface | Backend endpoint | Purpose |
| --- | --- | --- |
| `frontend/app/platform-admin/page.tsx` | `/api/admin/overview`, `/api/admin/service-insights`, `/api/admin/users`, `/api/admin/tenant-service-summary`, `/api/admin/roles/catalog` | Platform super-admin dashboards and user/tenant controls. |
| `frontend/app/settings/users/page.tsx` | `/api/tenant-users`, `/api/tenant-users/roles/catalog`, `/api/tenant-users/permissions/catalog` | Tenant-scoped user and function access management. |
| `frontend/app/onboarding/page.tsx` | `GET /api/onboarding/company-types`, `POST /api/onboarding/complete` | Tenant setup and first project creation. |

## Current Mapping Notes

- Dashboard user name, document list, activity feed, stats, and role actions are now backend-driven.
- The dashboard field-conditions card links to daily production because there is no standalone weather endpoint yet.
- `GET /api/admin/tenant-service-summary` is the platform-admin tenant listing source; there is no separate `GET /api/admin/tenants` list endpoint required by the current frontend.
- `POST /api/invoices/generate` is the active billing route; the backend router prefix is `/api/invoices`.