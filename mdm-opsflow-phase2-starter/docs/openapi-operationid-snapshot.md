# OpenAPI OperationId Snapshot

Generated from `backend/app/main.py`.

| Method | Path | Operation ID |
| --- | --- | --- |
| GET | `/` | `root_get` |
| GET | `/admin/audit-events` | `list_audit_events_admin_audit_events_get` |
| GET | `/admin/permissions/preview` | `preview_permissions_admin_permissions_preview_get` |
| GET | `/admin/platform-users` | `list_platform_users_admin_platform_users_get` |
| GET | `/admin/role-catalog` | `list_role_catalog_admin_role_catalog_get` |
| POST | `/admin/role-catalog` | `create_role_catalog_entry_admin_role_catalog_post` |
| GET | `/admin/roles` | `list_platform_roles_admin_roles_get` |
| GET | `/auth/me` | `me_auth_me_get` |
| POST | `/auth/refresh` | `refresh_auth_refresh_post` |
| POST | `/auth/register` | `register_auth_register_post` |
| POST | `/auth/signin` | `signin_auth_signin_post` |
| GET | `/health` | `health_check_health_get` |
| GET | `/intake/items` | `list_intake_items_intake_items_get` |
| GET | `/intake/items/{item_id}` | `get_intake_item_intake_items__item_id__get` |
| POST | `/intake/items/{item_id}/approve` | `approve_intake_item_intake_items__item_id__approve_post` |
| POST | `/intake/items/{item_id}/reject` | `reject_intake_item_intake_items__item_id__reject_post` |
| POST | `/intake/upload` | `upload_intake_files_intake_upload_post` |
| GET | `/onboarding/bootstrap` | `bootstrap_onboarding_bootstrap_get` |
| GET | `/projects` | `list_projects_projects_get` |
| POST | `/projects` | `create_project_projects_post` |
| GET | `/projects/{project_id}` | `get_project_projects__project_id__get` |
| PATCH | `/projects/{project_id}` | `update_project_projects__project_id__patch` |
| GET | `/tenant-users` | `list_tenant_users_tenant_users_get` |
| POST | `/tenant-users` | `assign_tenant_user_tenant_users_post` |
| GET | `/tickets` | `list_tickets_tickets_get` |
| POST | `/tickets` | `create_ticket_tickets_post` |
| GET | `/tickets/{ticket_id}` | `get_ticket_tickets__ticket_id__get` |
| PATCH | `/tickets/{ticket_id}` | `update_ticket_tickets__ticket_id__patch` |

