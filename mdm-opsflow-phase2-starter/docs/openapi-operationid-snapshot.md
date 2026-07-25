# OpenAPI OperationId Snapshot

Generated from `backend/app/main.py`.

| Method | Path | Operation ID |
| --- | --- | --- |
| GET | `/` | `root_get` |
| GET | `/api/admin/audit-logs` | `admin_audit_logs_list` |
| GET | `/api/admin/overview` | `admin_overview` |
| GET | `/api/admin/permissions-preview` | `admin_permissions_preview` |
| GET | `/api/admin/tenants/{tenant_id}/users` | `admin_tenant_users_list` |
| POST | `/api/auth/login` | `auth_login` |
| POST | `/api/auth/logout` | `auth_logout` |
| GET | `/api/auth/me` | `auth_me` |
| POST | `/api/auth/refresh` | `auth_refresh` |
| POST | `/api/auth/register` | `auth_register` |
| GET | `/api/intake/events` | `intake_events_list` |
| POST | `/api/intake/events/{event_id}/mark-processed` | `intake_events_mark_processed` |
| POST | `/api/intake/events/{event_id}/replay-dead-letter` | `intake_events_replay_dead_letter` |
| POST | `/api/intake/events/{event_id}/retry` | `intake_events_retry` |
| GET | `/api/intake/items` | `intake_items_list` |
| GET | `/api/intake/items/{item_id}` | `intake_items_get` |
| POST | `/api/intake/items/{item_id}/approve` | `intake_items_approve` |
| POST | `/api/intake/items/{item_id}/reject` | `intake_items_reject` |
| POST | `/api/intake/items/{item_id}/resolve-duplicate` | `intake_items_resolve_duplicate` |
| POST | `/api/intake/upload` | `intake_upload` |
| GET | `/api/onboarding/company-types` | `onboarding_company_types` |
| POST | `/api/onboarding/complete` | `onboarding_complete` |
| GET | `/api/projects` | `projects_list` |
| POST | `/api/projects` | `projects_create` |
| DELETE | `/api/projects/{project_id}` | `projects_delete` |
| GET | `/api/projects/{project_id}` | `projects_get` |
| PATCH | `/api/projects/{project_id}` | `projects_update` |
| GET | `/api/tenant-users` | `tenant_users_list` |
| POST | `/api/tenant-users` | `tenant_users_assign` |
| GET | `/api/tickets` | `tickets_list` |
| POST | `/api/tickets` | `tickets_create` |
| GET | `/api/tickets/{ticket_id}` | `tickets_get` |
| PATCH | `/api/tickets/{ticket_id}` | `tickets_update` |
| GET | `/health` | `health_get` |
