from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import IngestionBatchStatus, IntakeStatus, PlatformRole, ProjectStatus, TenantType


class TokenPair(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "<jwt-access-token>",
                "refresh_token": "<jwt-refresh-token>",
                "token_type": "bearer",
            }
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthRegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ops.user@example.com",
                "password": "Pass12345!",
                "display_name": "Ops User",
            }
        }
    )

    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=255)
    is_test: bool = False
    created_by_automation: bool = False
    test_run_id: str | None = Field(default=None, max_length=120)
    expires_at: datetime | None = None


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ops.user@example.com",
                "password": "Pass12345!",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
            }
        }
    )

    email: EmailStr
    password: str
    tenant_id: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "<jwt-refresh-token>",
            }
        }
    )

    refresh_token: str


class AuthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "display_name": "Ops User",
                "title": "",
                "platform_role": "tenant_user",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "tokens": {
                    "access_token": "<jwt-access-token>",
                    "refresh_token": "<jwt-refresh-token>",
                    "token_type": "bearer",
                },
            }
        }
    )

    user_id: str
    email: str
    display_name: str
    title: str
    platform_role: PlatformRole
    tenant_id: str | None = None
    tokens: TokenPair


class MeMembership(BaseModel):
    tenant_id: str
    tenant_name: str
    role_name: str


class TenantUserSummary(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "display_name": "Ops User",
                "title": "Operations Manager",
                "role_name": "owner",
                "status": "active",
            }
        }
    )

    user_id: str
    email: str
    display_name: str
    title: str
    role_name: str
    status: str


class UserPermissionOverrideItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "permission": "billing_write",
                "enabled": True,
            }
        }
    )

    permission: str = Field(min_length=2, max_length=120)
    enabled: bool


class TenantUserPermissionsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "role_name": "project_manager",
                "base_permissions": ["project_read", "project_write", "intake_read"],
                "effective_permissions": ["project_read", "project_write", "intake_read", "billing_read"],
                "overrides": [
                    {"permission": "billing_read", "enabled": True},
                    {"permission": "intake_write", "enabled": False},
                ],
            }
        }
    )

    user_id: str
    email: str
    role_name: str
    base_permissions: list[str]
    effective_permissions: list[str]
    overrides: list[UserPermissionOverrideItem]


class UpdateTenantUserPermissionsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overrides": [
                    {"permission": "billing_read", "enabled": True},
                    {"permission": "intake_write", "enabled": False},
                ]
            }
        }
    )

    overrides: list[UserPermissionOverrideItem] = Field(default_factory=list) # type: ignore


class MeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "display_name": "Ops User",
                "title": "",
                "platform_role": "tenant_user",
                "memberships": [
                    {
                        "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                        "tenant_name": "Acme Civil",
                        "role_name": "owner",
                    }
                ],
            }
        }
    )

    id: str
    email: str
    display_name: str
    title: str
    platform_role: PlatformRole
    memberships: list[MeMembership]


class MeUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "display_name": "Ops User",
                "title": "Operations Manager",
            }
        }
    )

    display_name: str = Field(min_length=2, max_length=255)
    title: str = Field(max_length=120, default="")


class AssignTenantUserRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new.member@example.com",
                "role_name": "project_manager",
                "display_name": "New Member",
                "title": "Assistant PM",
                "temporary_password": "ChangeMe123!",
            }
        }
    )

    email: EmailStr
    role_name: str = Field(min_length=2, max_length=100)
    display_name: str = Field(min_length=2, max_length=255, default="")
    title: str = Field(max_length=120, default="")
    temporary_password: str = Field(min_length=8, max_length=255, default="ChangeMe123!")


class UpdateTenantUserMembershipRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role_name": "field_supervisor",
                "status": "active",
            }
        }
    )

    role_name: str | None = Field(default=None, min_length=2, max_length=100)
    status: str | None = Field(default=None, pattern="^(active|inactive|invited)$")


class TenantUserResetPasswordRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_password": "NewStrongPass123!",
            }
        }
    )

    new_password: str = Field(min_length=8)


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "mdm-opsflow-backend",
                "environment": "local",
            }
        }
    )

    status: str
    service: str
    environment: str


class DashboardRoleLink(BaseModel):
    label: str
    href: str


class DashboardRoleExperienceResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role_key": "estimator",
                "role_label": "Estimator",
                "kpi_order": ["estimates", "draft_estimates", "awarded_estimates", "intake_pending_review"],
                "modules": [
                    {"label": "Takeoff", "href": "/modules/estimator/takeoff"},
                    {"label": "Bid Pipeline", "href": "/modules/estimator/bid-pipeline"},
                ],
                "quick_actions": [
                    {"label": "Open estimator workspace", "href": "/estimator"},
                    {"label": "Review ticket inputs", "href": "/tickets"},
                ],
                "alerts": ["3 estimates are still in draft."],
            }
        }
    )

    role_key: str
    role_label: str
    kpi_order: list[str]
    modules: list[DashboardRoleLink]
    quick_actions: list[DashboardRoleLink]
    alerts: list[str]


class AdminOverviewResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "MDM OpsFlow",
                "status": "foundation-ready",
                "role": "platform_super_admin",
                "tenants": 4,
                "production_tenants": 2,
                "demo_tenants": 1,
                "test_tenants": 1,
                "canary_tenants": 0,
                "test_and_canary_tenants": 1,
                "users": 18,
                "active_users": 16,
                "inactive_users": 2,
                "projects": 12,
                "role_count": 14,
                "expiring_test_tenants": 1,
                "expiring_test_users": 2,
            }
        }
    )

    platform: str
    status: str
    role: str
    tenants: int
    production_tenants: int
    demo_tenants: int
    test_tenants: int
    canary_tenants: int
    test_and_canary_tenants: int
    users: int
    active_users: int
    inactive_users: int
    projects: int
    role_count: int
    expiring_test_tenants: int
    expiring_test_users: int


class AdminTenantUser(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "display_name": "Ops User",
                "title": "Operations Manager",
            }
        }
    )

    id: str
    email: str
    display_name: str
    title: str


class AdminAuditLogEntry(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "d8af6ea7-0ec4-4f89-8b7a-0f8d9f9505e9",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "action": "create_project",
                "resource_type": "project",
                "resource_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "request_id": "req-2f8bde38a0d04b01a5f95f6a8d5c0b84",
                "before_values_json": "{\"status\": \"planning\"}",
                "after_values_json": "{\"status\": \"active\"}",
                "occurred_at": "2026-07-25T15:32:16.935131Z",
                "created_at": "2026-07-25T15:32:16.935131Z",
                "actor_user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
            }
        }
    )

    id: str
    tenant_id: str | None = None
    action: str
    resource_type: str
    resource_id: str
    request_id: str | None = None
    before_values_json: str = ""
    after_values_json: str = ""
    occurred_at: datetime
    created_at: datetime
    actor_user_id: str


class AdminPermissionsPreviewItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "platform_role": "tenant_user",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "role_name": "owner",
                "permissions": ["project_read", "project_write"],
            }
        }
    )

    user_id: str
    email: str
    platform_role: str
    tenant_id: str | None = None
    role_name: str | None = None
    permissions: list[str]


class AdminPermissionsPreviewResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "user_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                        "email": "ops.user@example.com",
                        "platform_role": "tenant_user",
                        "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                        "role_name": "owner",
                        "permissions": ["project_read", "project_write"],
                    }
                ]
            }
        }
    )

    items: list[AdminPermissionsPreviewItem]


class AdminUserAccessItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "email": "ops.user@example.com",
                "display_name": "Ops User",
                "title": "Operations Manager",
                "platform_role": "user",
                "is_active": True,
                "user_status": "active",
            }
        }
    )

    id: str
    email: str
    display_name: str
    title: str
    platform_role: PlatformRole
    is_active: bool
    user_status: str
    is_test: bool = False
    created_by_automation: bool = False
    test_run_id: str | None = None
    expires_at: datetime | None = None


class AdminUserTenantMembershipItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "membership_id": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "user_id": "12d3121c-5038-4025-8e4c-a64fd3b76156",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "tenant_name": "Acme Civil",
                "role_name": "estimator",
                "status": "active",
            }
        }
    )

    membership_id: str
    user_id: str
    tenant_id: str
    tenant_name: str
    role_name: str
    status: str


class AdminAssignUserTenantMembershipRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "role_name": "estimator",
            }
        }
    )

    tenant_id: str
    role_name: str = Field(min_length=2, max_length=100)


class AdminUpdateUserTenantMembershipRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "role_name": "project_manager",
                "status": "active",
            }
        }
    )

    tenant_id: str | None = None
    role_name: str | None = Field(default=None, min_length=2, max_length=100)
    status: str | None = Field(default=None, pattern="^(active|inactive|invited)$")


class AdminUpdateUserAccessRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform_role": "platform_super_admin",
                "is_active": True,
            }
        }
    )

    platform_role: PlatformRole | None = None
    is_active: bool | None = None


class AdminResetPasswordRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_password": "NewStrongPass123!",
            }
        }
    )

    new_password: str = Field(min_length=8)


class AdminCreateTenantRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_name": "North Ridge Civil",
                "company_type": "Heavy Civil",
                "preferred_language": "en",
                "selected_modules": ["Projects", "Budget", "Safety"],
            }
        }
    )

    tenant_name: str = Field(min_length=2, max_length=255)
    company_type: str = Field(default="General Contractor", min_length=2, max_length=255)
    tenant_type: TenantType = TenantType.PRODUCTION
    is_test: bool = False
    created_by_automation: bool = False
    test_run_id: str | None = Field(default=None, max_length=120)
    expires_at: datetime | None = None
    preferred_language: str = Field(default="en", min_length=2, max_length=10)
    selected_modules: list[str] = Field(default_factory=lambda: ["Projects", "Budget", "Safety"])
    owner_email: EmailStr | None = None
    owner_display_name: str = Field(default="", max_length=255)
    owner_temporary_password: str = Field(default="", max_length=255)


class AdminCreateTenantResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "tenant_name": "North Ridge Civil",
            }
        }
    )

    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None = None
    expires_at: datetime | None = None


class AdminTenantServiceSummaryItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "tenant_name": "Acme Civil",
                "tenant_status_filter": "active",
                "users": 12,
                "active_users": 11,
                "inactive_users": 1,
                "projects": 8,
                "tickets": 152,
                "intake_items": 247,
                "extractions": 91,
                "pending_reviews": 11,
            }
        }
    )

    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    tenant_status_filter: str = "all"
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None = None
    expires_at: datetime | None = None
    users: int
    active_users: int
    inactive_users: int
    projects: int
    tickets: int
    intake_items: int
    extractions: int
    pending_reviews: int


class AdminTenantServiceSummaryResponse(BaseModel):
    tenant_type_filter: TenantType | None = None
    tenant_status_filter: str = "all"
    items: list[AdminTenantServiceSummaryItem]


class AdminTenantCountTriplet(BaseModel):
    users: int
    projects: int
    tickets: int


class AdminTenantCountDiscrepancyItem(BaseModel):
    tenant_id: str
    tenant_name: str
    expected: AdminTenantCountTriplet
    actual: AdminTenantCountTriplet
    discrepancies: list[str]
    is_reconciled: bool


class AdminDataCountSessionValidation(BaseModel):
    expected_total_tenants: int | None = None
    actual_total_tenants: int
    expected_total_users: int | None = None
    actual_total_users: int
    discrepancies: list[str]


class AdminDataCountReconciliationResponse(BaseModel):
    generated_at: datetime
    total_tenants: int
    mismatched_tenants: int
    items: list[AdminTenantCountDiscrepancyItem]
    session_validation: AdminDataCountSessionValidation


class AdminServiceInsightsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenants": 4,
                "users": 18,
                "projects": 12,
                "tickets": 235,
                "production_tenants": 2,
                "demo_tenants": 1,
                "test_tenants": 1,
                "canary_tenants": 0,
                "test_and_canary_tenants": 1,
                "active_users": 16,
                "inactive_users": 2,
                "role_count": 14,
                "expiring_test_tenants": 1,
                "expiring_test_users": 2,
                "customer_growth_tenants": 2,
                "intake_items": 420,
                "intake_needs_review": 16,
                "extractions_pending_review": 9,
                "extractions_review_submitted": 5,
                "unresolved_extraction_issues": 14,
                "integration_events_pending": 7,
                "integration_events_failed": 2,
                "opportunities": [
                    "Reduce intake review backlog by resolving pending intake items.",
                    "Address failed integration events to improve downstream reliability.",
                ],
            }
        }
    )

    tenants: int
    users: int
    active_users: int
    inactive_users: int
    projects: int
    tickets: int
    production_tenants: int
    demo_tenants: int
    test_tenants: int
    canary_tenants: int
    test_and_canary_tenants: int
    role_count: int
    expiring_test_tenants: int
    expiring_test_users: int
    customer_growth_tenants: int
    intake_items: int
    intake_needs_review: int
    extractions_pending_review: int
    extractions_review_submitted: int
    unresolved_extraction_issues: int
    integration_events_pending: int
    integration_events_failed: int
    opportunities: list[str]


class PermissionCatalogResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "permissions": {
                    "project.view": "View project records and project-level metrics.",
                    "project.manage": "Create, edit, and delete projects.",
                },
                "role_matrix": {
                    "owner": ["project.view", "project.manage", "membership.assign"],
                    "estimator": ["estimate.view", "estimate.create", "estimate.edit"],
                },
                "legacy_aliases": {
                    "project_read": ["project.view"],
                    "estimate_write": ["estimate.create", "estimate.edit"],
                },
            }
        }
    )

    permissions: dict[str, str]
    role_matrix: dict[str, list[str]]
    legacy_aliases: dict[str, list[str]]


class AdminTestDataCleanupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dry_run": True,
            }
        }
    )

    dry_run: bool = True


class AdminTestDataCleanupTenantAction(BaseModel):
    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None = None
    expires_at: datetime | None = None
    memberships_to_deactivate: int


class AdminTestDataCleanupUserAction(BaseModel):
    user_id: str
    email: str
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None = None
    expires_at: datetime | None = None
    memberships_to_deactivate: int


class AdminTestDataCleanupResponse(BaseModel):
    dry_run: bool
    executed_at: datetime
    eligible_tenants: int
    eligible_users: int
    deactivated_memberships: int
    deactivated_users: int
    preserved_audit_logs: bool = True
    tenant_actions: list[AdminTestDataCleanupTenantAction]
    user_actions: list[AdminTestDataCleanupUserAction]


class OnboardingRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "Acme Civil",
                "company_types": ["General Contractor", "Earthwork / Site Development"],
                "language": "en",
                "modules": ["Projects", "Intake", "Payroll"],
                "invite_emails": ["pm@example.com"],
                "first_project_name": "Downtown Site Prep",
            }
        }
    )

    company_name: str = Field(min_length=2, max_length=200)
    company_types: list[str] = Field(default_factory=list)
    language: str = Field(default="en", pattern="^(en|es)$")
    modules: list[str] = Field(default_factory=list)
    invite_emails: list[EmailStr] = Field(default_factory=list)
    first_project_name: str = Field(min_length=2, max_length=255)
    tenant_type: TenantType = TenantType.PRODUCTION
    is_test: bool = False
    created_by_automation: bool = False
    test_run_id: str | None = Field(default=None, max_length=120)
    expires_at: datetime | None = None


class OnboardingResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "project_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
            }
        }
    )

    tenant_id: str
    project_id: str
    tenant_type: TenantType
    is_test: bool
    created_by_automation: bool
    test_run_id: str | None = None
    expires_at: datetime | None = None


class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EmployeeBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    role_title: str = ""
    email: str = ""
    phone: str = ""
    department: str = ""
    status: str = "active"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = None
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    status: str | None = None


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class PayrollTimecardBase(BaseModel):
    employee_id: str
    project_id: str | None = None
    work_date: datetime
    regular_hours: Decimal = Decimal("0.00")
    overtime_hours: Decimal = Decimal("0.00")
    double_time_hours: Decimal = Decimal("0.00")
    cost_code: str = ""
    work_description: str = ""
    status: str = "draft"


class PayrollTimecardCreate(PayrollTimecardBase):
    pass


class PayrollTimecardUpdate(BaseModel):
    employee_id: str | None = None
    project_id: str | None = None
    work_date: datetime | None = None
    regular_hours: Decimal | None = None
    overtime_hours: Decimal | None = None
    double_time_hours: Decimal | None = None
    cost_code: str | None = None
    work_description: str | None = None
    status: str | None = None


class PayrollTimecardResponse(PayrollTimecardBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class PayrollRunBase(BaseModel):
    run_number: str = Field(min_length=2, max_length=120)
    period_start: datetime
    period_end: datetime
    status: str = "draft"
    notes: str = ""


class PayrollRunCreate(PayrollRunBase):
    pass


class PayrollRunResponse(PayrollRunBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    employee_count: int
    total_regular_hours: Decimal
    total_overtime_hours: Decimal
    total_double_time_hours: Decimal
    created_by: str
    created_at: datetime
    updated_at: datetime


class PayrollSummaryByProjectResponse(BaseModel):
    project_id: str | None = None
    timecard_count: int
    regular_hours: Decimal
    overtime_hours: Decimal
    double_time_hours: Decimal


class PayrollSummaryResponse(BaseModel):
    employee_count: int
    timecard_count: int
    payroll_run_count: int
    total_regular_hours: Decimal
    total_overtime_hours: Decimal
    total_double_time_hours: Decimal
    by_project: list[PayrollSummaryByProjectResponse]


class EstimatorTakeoffBase(BaseModel):
    project_id: str | None = None
    takeoff_number: str = Field(min_length=2, max_length=120)
    material_name: str = ""
    quantity: Decimal = Decimal("0.00")
    unit_of_measure: str = "cy"
    estimated_cost: Decimal | None = None
    status: str = "draft"
    notes: str = ""


class EstimatorTakeoffCreate(EstimatorTakeoffBase):
    pass


class EstimatorTakeoffResponse(EstimatorTakeoffBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimatorVersionBase(BaseModel):
    project_id: str | None = None
    version_name: str = Field(min_length=2, max_length=120)
    revision_number: int = 1
    estimated_revenue: Decimal | None = None
    estimated_cost: Decimal | None = None
    status: str = "draft"
    notes: str = ""


class EstimatorVersionCreate(EstimatorVersionBase):
    pass


class EstimatorVersionResponse(EstimatorVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimatorBidPipelineItemBase(BaseModel):
    project_id: str | None = None
    bid_number: str = Field(min_length=2, max_length=120)
    customer_name: str = ""
    stage: str = "qualifying"
    bid_amount: Decimal | None = None
    probability_percent: Decimal | None = None
    due_date: datetime | None = None
    status: str = "open"
    notes: str = ""


class EstimatorBidPipelineItemCreate(EstimatorBidPipelineItemBase):
    pass


class EstimatorBidPipelineItemResponse(EstimatorBidPipelineItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimatorWinLossRecordBase(BaseModel):
    project_id: str | None = None
    bid_pipeline_item_id: str | None = None
    outcome: str = "pending"
    final_amount: Decimal | None = None
    decision_date: datetime | None = None
    reason: str = ""


class EstimatorWinLossRecordCreate(EstimatorWinLossRecordBase):
    pass


class EstimatorWinLossRecordResponse(EstimatorWinLossRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimatorSummaryResponse(BaseModel):
    takeoff_count: int
    version_count: int
    bid_pipeline_count: int
    wins: int
    losses: int
    pending: int
    win_rate_percent: Decimal


class EstimateBase(BaseModel):
    project_id: str | None = None
    estimate_name: str = Field(min_length=2, max_length=255)
    estimate_number: str = Field(min_length=2, max_length=120)
    customer_name: str = ""
    project_name: str = ""
    project_address: str = ""
    project_type: str = ""
    bid_due_date: datetime | None = None
    expected_start_date: datetime | None = None
    expected_completion_date: datetime | None = None
    estimator_name: str = ""
    project_manager_name: str = ""
    sales_contact: str = ""
    contract_type: str = ""
    estimate_type: str = ""
    currency: str = "USD"
    tax_jurisdiction: str = ""
    target_margin_percent: Decimal = Decimal("0.00")
    default_overhead_percent: Decimal = Decimal("0.00")
    default_contingency_percent: Decimal = Decimal("0.00")
    notes: str = ""


class EstimateCreate(EstimateBase):
    status: str = "Draft"


class EstimateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    project_id: str | None = None
    estimate_name: str | None = None
    estimate_number: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    project_address: str | None = None
    project_type: str | None = None
    bid_due_date: datetime | None = None
    expected_start_date: datetime | None = None
    expected_completion_date: datetime | None = None
    estimator_name: str | None = None
    project_manager_name: str | None = None
    sales_contact: str | None = None
    contract_type: str | None = None
    estimate_type: str | None = None
    currency: str | None = None
    tax_jurisdiction: str | None = None
    target_margin_percent: Decimal | None = None
    default_overhead_percent: Decimal | None = None
    default_contingency_percent: Decimal | None = None
    notes: str | None = None


class EstimateResponse(EstimateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    status: str
    approval_status: str
    is_locked: bool
    locked_at: datetime | None = None
    converted_project_id: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimateStatusUpdateRequest(BaseModel):
    target_status: str = Field(min_length=2, max_length=40)
    details: str = ""


class EstimateUnlockRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class EstimateDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    estimate_id: str
    intake_item_id: str | None = None
    filename: str
    document_type: str
    processing_status: str
    confidence_score: Decimal
    version_label: str
    review_status: str
    uploaded_by: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime


class EstimateItemBase(BaseModel):
    item_number: str = ""
    cost_code: str = ""
    division: str = ""
    phase: str = ""
    description: str = ""
    work_location: str = ""
    quantity: Decimal = Decimal("0.00")
    unit_of_measure: str = ""
    unit_cost: Decimal = Decimal("0.00")
    total_cost: Decimal = Decimal("0.00")
    unit_price: Decimal = Decimal("0.00")
    total_selling_price: Decimal = Decimal("0.00")
    source: str = "manual"
    assumption: str = ""
    notes: str = ""
    review_status: str = "pending"


class EstimateItemCreate(EstimateItemBase):
    pass


class EstimateItemUpdate(BaseModel):
    item_number: str | None = None
    cost_code: str | None = None
    division: str | None = None
    phase: str | None = None
    description: str | None = None
    work_location: str | None = None
    quantity: Decimal | None = None
    unit_of_measure: str | None = None
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    unit_price: Decimal | None = None
    total_selling_price: Decimal | None = None
    source: str | None = None
    assumption: str | None = None
    notes: str | None = None
    review_status: str | None = None


class EstimateItemResponse(EstimateItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    estimate_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimateApprovalRequest(BaseModel):
    decision: str = Field(min_length=2, max_length=40)
    comments: str = ""


class EstimateApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    estimate_id: str
    approver_user_id: str
    approver_role: str
    decision: str
    comments: str
    decided_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimateAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    estimate_id: str
    actor_user_id: str
    action: str
    previous_status: str
    new_status: str
    details: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class EstimateCompareResponse(BaseModel):
    left_version_id: str
    right_version_id: str
    summary: str
    changes: list[str]


class EstimateValidationResponse(BaseModel):
    completion_score: int
    unresolved_issues: list[str]


class EstimateAiReviewResponse(BaseModel):
    estimate_id: str
    warnings: list[str]
    recommendations: list[str]


class CostLibraryResponse(BaseModel):
    labor: list[dict[str, str]]
    equipment: list[dict[str, str]]
    materials: list[dict[str, str]]
    trucking: list[dict[str, str]]
    subcontractors: list[dict[str, str]]


class CostLibraryImportRequest(BaseModel):
    labor: list[dict[str, str]] = []
    equipment: list[dict[str, str]] = []
    materials: list[dict[str, str]] = []
    trucking: list[dict[str, str]] = []
    subcontractors: list[dict[str, str]] = []


class CostLibraryImportResponse(BaseModel):
    imported_count: int


class VendorPurchaseOrderBase(BaseModel):
    project_id: str | None = None
    po_number: str = Field(min_length=2, max_length=120)
    vendor_name: str = ""
    description: str = ""
    status: str = "open"
    total_amount: Decimal | None = None


class VendorPurchaseOrderCreate(VendorPurchaseOrderBase):
    pass


class VendorPurchaseOrderResponse(VendorPurchaseOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class VendorInvoiceSubmissionBase(BaseModel):
    project_id: str | None = None
    purchase_order_id: str | None = None
    invoice_number: str = Field(min_length=2, max_length=120)
    vendor_name: str = ""
    amount: Decimal | None = None
    status: str = "submitted"
    notes: str = ""


class VendorInvoiceSubmissionCreate(VendorInvoiceSubmissionBase):
    pass


class VendorInvoiceSubmissionResponse(VendorInvoiceSubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class VendorDeliveryRecordBase(BaseModel):
    project_id: str | None = None
    purchase_order_id: str | None = None
    ticket_number: str = ""
    vendor_name: str = ""
    destination: str = ""
    status: str = "pending"
    received_at: datetime | None = None


class VendorDeliveryRecordCreate(VendorDeliveryRecordBase):
    pass


class VendorDeliveryRecordResponse(VendorDeliveryRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class VendorComplianceDocumentBase(BaseModel):
    project_id: str | None = None
    document_name: str = Field(min_length=2, max_length=255)
    vendor_name: str = ""
    status: str = "current"
    expires_at: datetime | None = None
    notes: str = ""


class VendorComplianceDocumentCreate(VendorComplianceDocumentBase):
    pass


class VendorComplianceDocumentResponse(VendorComplianceDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class CustomerPortalProjectSummaryResponse(BaseModel):
    project_id: str
    project_name: str
    project_number: str
    status: str
    project_manager: str
    actual_revenue: Decimal
    ticket_count: int
    total_documents: int
    pending_review_documents: int


class CustomerPortalBillingStatusResponse(BaseModel):
    project_id: str
    project_name: str
    status: str
    actual_revenue: Decimal
    ticket_count: int
    total_tons: Decimal
    total_cubic_yards: Decimal
    revenue_shortfall: bool


class CustomerPortalDocumentStatusResponse(BaseModel):
    project_id: str
    project_name: str
    total_documents: int
    pending_review_documents: int
    latest_document_at: datetime | None = None


class EquipmentBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    equipment_type: str = ""
    capacity_tons: Decimal | None = None
    status: str = "available"
    notes: str = ""


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: str | None = None
    equipment_type: str | None = None
    capacity_tons: Decimal | None = None
    status: str | None = None
    notes: str | None = None


class EquipmentResponse(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class TruckBase(BaseModel):
    unit_number: str = Field(min_length=2, max_length=120)
    truck_type: str = ""
    capacity_tons: Decimal | None = None
    status: str = "available"
    assigned_driver: str = ""
    notes: str = ""


class TruckCreate(TruckBase):
    pass


class TruckUpdate(BaseModel):
    unit_number: str | None = None
    truck_type: str | None = None
    capacity_tons: Decimal | None = None
    status: str | None = None
    assigned_driver: str | None = None
    notes: str | None = None


class TruckResponse(TruckBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class MaterialBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    unit_of_measure: str = "ton"
    density_tons_per_cubic_yard: Decimal | None = None
    description: str = ""


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit_of_measure: str | None = None
    density_tons_per_cubic_yard: Decimal | None = None
    description: str | None = None


class MaterialResponse(MaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class ProjectBase(BaseModel):
    project_name: str = Field(min_length=2, max_length=255)
    project_number: str = Field(min_length=1, max_length=80)
    customer: str = ""
    address: str = ""
    project_manager: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    contract_amount: Decimal | None = None
    budget: Decimal | None = None
    status: ProjectStatus = ProjectStatus.PLANNING
    description: str = ""


class ProjectCreate(ProjectBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "Downtown Site Prep",
                "project_number": "PRJ-2026-001",
                "customer": "City of Example",
                "address": "100 Main St",
                "project_manager": "Alex Ramos",
                "status": "planning",
                "description": "Initial site prep and grading",
            }
        }
    )


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
                "project_manager": "Jordan Lee",
                "description": "Mobilized and active",
            }
        }
    )

    project_name: str | None = None
    project_number: str | None = None
    customer: str | None = None
    address: str | None = None
    project_manager: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    contract_amount: Decimal | None = None
    budget: Decimal | None = None
    status: ProjectStatus | None = None
    description: str | None = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "project_name": "Downtown Site Prep",
                "project_number": "PRJ-2026-001",
                "customer": "City of Example",
                "address": "100 Main St",
                "project_manager": "Jordan Lee",
                "start_date": None,
                "end_date": None,
                "contract_amount": None,
                "budget": None,
                "status": "active",
                "description": "Mobilized and active",
                "created_by": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "created_at": "2026-07-25T15:32:16.935131Z",
                "updated_at": "2026-07-25T15:35:01.128927Z",
            }
        },
    )

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

class DailyFieldReportBase(BaseModel):
    project_id: str
    report_date: datetime
    company_name: str = ""
    reporting_supervisor: str = ""
    shift_start_time: str = ""
    shift_end_time: str = ""
    weather: dict[str, object] | None = None
    crew_members: list[dict[str, object]] = Field(default_factory=list)
    equipment_used: list[dict[str, object]] = Field(default_factory=list)
    deliveries: list[dict[str, object]] = Field(default_factory=list)
    visitors: list[dict[str, object]] = Field(default_factory=list)
    delays: list[dict[str, object]] = Field(default_factory=list)
    photos: list[dict[str, object]] = Field(default_factory=list)
    production_quantities: list[dict[str, object]] = Field(default_factory=list)
    safety_observations: list[dict[str, object]] = Field(default_factory=list)
    work_performed: str = ""
    work_planned_for_tomorrow: str = ""
    prepared_by: str = ""
    electronic_signature: str = ""
    status: str = "draft"


class DailyFieldReportCreate(DailyFieldReportBase):
    pass


class DailyFieldReportUpdate(BaseModel):
    project_id: str | None = None
    report_date: datetime | None = None
    company_name: str | None = None
    reporting_supervisor: str | None = None
    shift_start_time: str | None = None
    shift_end_time: str | None = None
    weather: dict[str, object] | None = None
    crew_members: list[dict[str, object]] | None = None
    equipment_used: list[dict[str, object]] | None = None
    deliveries: list[dict[str, object]] | None = None
    visitors: list[dict[str, object]] | None = None
    delays: list[dict[str, object]] | None = None
    photos: list[dict[str, object]] | None = None
    production_quantities: list[dict[str, object]] | None = None
    safety_observations: list[dict[str, object]] | None = None
    work_performed: str | None = None
    work_planned_for_tomorrow: str | None = None
    prepared_by: str | None = None
    electronic_signature: str | None = None
    status: str | None = None


class DailyFieldReportResponse(DailyFieldReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    report_number: str
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class DailyFieldReportAssistRequest(BaseModel):
    project_id: str
    report_date: datetime
    reporting_supervisor: str = ""
    total_workers: int | None = None
    weather: dict[str, object] | None = None
    work_performed: str = ""
    equipment_used: list[dict[str, object]] = Field(default_factory=list)


class DailyFieldReportAssistResponse(BaseModel):
    project_id: str
    report_date: datetime
    ai_generated: bool
    productivity_score: int
    productivity_summary: str
    suggested_work_performed: str
    suggested_delay_notes: list[str]
    suggested_safety_observations: list[str]
    ticket_context: dict[str, object]
    weather_context: dict[str, object]


class AIWorkflowRouteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=8000)
    company_name: str | None = None
    reporting_supervisor: str | None = None
    work_performed: str | None = None
    work_planned_for_tomorrow: str | None = None
    material_name: str | None = None
    project_id: str | None = None
    report_date: datetime | None = None


class AIWorkflowRouteResponse(BaseModel):
    routed: bool
    customer_created: bool
    material_created: bool
    report_created: bool
    customer_name: str | None = None
    material_name: str | None = None
    report_number: str | None = None
    message: str


class ProjectCostResponse(BaseModel):
    """Project cost aggregation from all tickets."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tickets": 15,
                "total_revenue": "45000.00",
                "total_fuel_cost": "8500.00",
                "total_net_tons": 450,
                "total_cubic_yards": 900,
                "avg_revenue_per_ton": "100.00",
            }
        }
    )

    total_tickets: int
    total_revenue: Decimal
    total_fuel_cost: Decimal
    total_net_tons: Decimal
    total_cubic_yards: Decimal
    avg_revenue_per_ton: Decimal


class ProjectProfitabilityResponse(BaseModel):
    """Project profitability summary comparing contract/budget vs actual costs."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "project_name": "Downtown Site Prep",
                "status": "active",
                "contract_amount": "50000.00",
                "budgeted_cost": "10000.00",
                "actual_cost": "8500.00",
                "actual_revenue": "45000.00",
                "contract_variance": "5000.00",
                "budget_variance": "1500.00",
                "gross_profit": "36500.00",
                "profit_margin": 81.11,
                "cost_overrun": False,
                "revenue_shortfall": False,
                "ticket_count": 15,
                "total_tons": 450,
                "total_cubic_yards": 900,
            }
        }
    )

    project_id: str | None = None
    project_name: str | None = None
    status: str | None = None
    contract_amount: Decimal
    budgeted_cost: Decimal
    actual_cost: Decimal
    actual_revenue: Decimal
    contract_variance: Decimal
    budget_variance: Decimal
    gross_profit: Decimal
    profit_margin: float
    cost_overrun: bool
    revenue_shortfall: bool
    ticket_count: int
    total_tons: Decimal
    total_cubic_yards: Decimal


class InvoiceLineItemResponse(BaseModel):
    """Single line item on an invoice."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "12345678-1234-5678-1234-567812345678",
                "description": "Dirt - Unit 5 (Ticket #DRT-2026-001)",
                "quantity": "450.00",
                "unit": "tons",
                "rate": "100.00",
                "amount": "45000.00",
                "rate_type": "per_ton",
            }
        }
    )

    ticket_id: str
    description: str
    quantity: Decimal
    unit: str
    rate: Decimal
    amount: Decimal
    rate_type: str


class InvoiceGenerationRequest(BaseModel):
    """Request to generate an invoice for a project."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rate_per_ton": "100.00",
                "rate_per_yard": None,
                "rate_per_load": None,
                "status_filter": "approved",
            }
        }
    )

    rate_per_ton: Decimal | None = None
    rate_per_yard: Decimal | None = None
    rate_per_load: Decimal | None = None
    status_filter: str = Field(default="approved", min_length=2, max_length=30)


class InvoiceResponse(BaseModel):
    """Complete invoice with line items and totals."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "line_items": [
                    {
                        "ticket_id": "12345678-1234-5678-1234-567812345678",
                        "description": "Dirt - Unit 5 (Ticket #DRT-2026-001)",
                        "quantity": "450.00",
                        "unit": "tons",
                        "rate": "100.00",
                        "amount": "45000.00",
                        "rate_type": "per_ton",
                    }
                ],
                "subtotal": "45000.00",
                "tax_rate": 0.0,
                "tax_amount": "0.00",
                "total": "45000.00",
                "item_count": 1,
            }
        }
    )

    project_id: str
    line_items: list[InvoiceLineItemResponse]
    subtotal: Decimal
    tax_rate: float
    tax_amount: Decimal
    total: Decimal
    item_count: int


class IntakeItemBase(BaseModel):
    project_id: str | None = None
    filename: str = Field(min_length=1, max_length=255)
    original_filename: str = ""
    content_hash: str = ""
    document_type: str = Field(default="general", min_length=2, max_length=120)
    source: str = Field(default="manual", min_length=2, max_length=120)
    status: IntakeStatus = IntakeStatus.UPLOADED
    classification_confidence: float = 0
    match_confidence: float = 0
    page_number: int | None = None
    page_document_index: int | None = None
    extracted_summary: str = ""
    extracted_text: str = ""
    ai_summary: str = ""
    extracted_entities: str = "{}"
    ocr_status: str = "pending"
    ai_status: str = "pending"
    needs_review: bool = False
    review_reason: str = ""
    duplicate_of_item_id: str | None = None
    conflict_notes: str = ""


class IntakeItemCreate(IntakeItemBase):
    pass


class IntakeItemUpdate(BaseModel):
    project_id: str | None = None
    document_type: str | None = Field(default=None, min_length=2, max_length=120)
    source: str | None = Field(default=None, min_length=2, max_length=120)
    status: IntakeStatus | None = None
    extracted_summary: str | None = None
    extracted_text: str | None = None
    ai_summary: str | None = None
    extracted_entities: str | None = None
    ocr_status: str | None = None
    ai_status: str | None = None
    needs_review: bool | None = None
    review_reason: str | None = None
    duplicate_of_item_id: str | None = None
    conflict_notes: str | None = None


class IntakeDuplicateResolutionRequest(BaseModel):
    duplicate_of_item_id: str | None = None
    conflict_notes: str = ""


class IntakeIntegrationEventProcessRequest(BaseModel):
    status: str = Field(default="processed", pattern="^(processed|failed)$")
    processing_notes: str = ""
    failure_reason: str = ""


class IntakeIntegrationEventRetryRequest(BaseModel):
    retry_notes: str = ""


class IntakeIntegrationEventReplayRequest(BaseModel):
    approval_notes: str = ""


class IntakeItemResponse(IntakeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    batch_id: str | None = None
    file_path: str
    mime_type: str
    file_size_bytes: int
    processing_stage: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class IntakePlacementSuggestionRequest(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=50)


class IntakeDocumentIntelligenceResponse(BaseModel):
    primary_document_type: str
    subtype: str
    project_name: str = ""
    project_number: str = ""
    vendor_subcontractor: str = ""
    document_date: str = ""
    document_reference_number: str = ""
    recommended_module: str
    confidence: float
    classification_family: str = ""
    revision_chain_detected: bool = False
    ticket_block_reason: str = ""
    estimator_intent_score: float = 0.0
    precedence_basis: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)


class DocumentIntakeProjectResponse(BaseModel):
    name: str | None = None
    number: str | None = None
    match_confidence: float = 0.0


class DocumentIntakeVendorResponse(BaseModel):
    name: str | None = None
    document_number: str | None = None


class DocumentIntakeRouteResponse(BaseModel):
    document_type: str
    classification_confidence: float
    recommended_route: str
    project: DocumentIntakeProjectResponse
    vendor: DocumentIntakeVendorResponse
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    uncertain_fields: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    requires_human_review: bool = False
    reason_for_review: str | None = None


class DocumentIntakeConfigResponse(BaseModel):
    auto_route_min_confidence: float
    auto_post_financial_or_ticket_min_confidence: float
    never_silent_overwrite: bool
    preserve_source_value: bool
    preserve_units: bool
    flag_cross_document_conflicts: bool
    require_tenant_scope: bool
    create_audit_event: bool
    routes: dict[str, str]


class IntakeProjectMatchAlternativeResponse(BaseModel):
    project_id: str
    project_name: str
    project_number: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class IntakeProjectMatchResponse(BaseModel):
    matched_project_id: str | None = None
    match_confidence: float = 0.0
    matching_evidence: list[str] = Field(default_factory=list)
    alternative_matches: list[IntakeProjectMatchAlternativeResponse] = Field(default_factory=list)
    auto_associate: bool = False
    ambiguity_flag: bool = False
    confidence_gap_to_next: float = 0.0
    match_strategy: str = ""
    human_confirmation_required: bool = False


class IntakePlacementSuggestionResponse(BaseModel):
    item_id: str
    destination_key: str
    destination_label: str
    destination_href: str
    confidence: float
    reason: str
    signal_source: str
    document_intelligence: IntakeDocumentIntelligenceResponse | None = None
    project_match: IntakeProjectMatchResponse | None = None


class IntakePlacementSuggestionListResponse(BaseModel):
    items: list[IntakePlacementSuggestionResponse] = Field(default_factory=list)


class IntakeConflictValueCandidateResponse(BaseModel):
    item_id: str
    field_name: str
    value: float
    unit: str
    document_type: str
    document_subtype: str
    source_text: str
    page: int | None = None
    confidence: float
    created_at: datetime


class IntakeConflictSuggestionResponse(BaseModel):
    field_name: str
    candidates: list[IntakeConflictValueCandidateResponse] = Field(default_factory=list)
    recommended: IntakeConflictValueCandidateResponse
    reason: str


class IntakeConflictSuggestionListResponse(BaseModel):
    items: list[IntakeConflictSuggestionResponse] = Field(default_factory=list)


class IntakeConflictResolveRequest(BaseModel):
    field_name: str = Field(min_length=2, max_length=120)
    selected_item_id: str = Field(min_length=3, max_length=120)
    selected_value: float
    rationale: str = ""


class IngestionBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    source_channel: str
    status: IngestionBatchStatus
    total_documents: int
    created_documents: int
    matched_documents: int
    needs_review_documents: int
    duplicate_documents: int
    blocked_documents: int
    error_documents: int
    summary_json: str
    created_by: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IntakeBatchDetailResponse(IngestionBatchResponse):
    items: list[IntakeItemResponse] = []


class IntakeIntegrationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    event_type: str
    resource_type: str
    resource_id: str
    payload_json: str
    status: str
    created_by: str
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IntakeReplayAuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    actor_user_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class IntakeReplayExportTokenResponse(BaseModel):
    token: str
    download_url: str
    expires_at: datetime


class IntakeReplayExportTokenRevokeRequest(BaseModel):
    token: str


class IntakeReplayExportTokenRevokeResponse(BaseModel):
    token_id: str
    revoked: bool
    revoked_at: datetime


class IntakeReplayExportTokenBulkRevokeActiveRequest(BaseModel):
    tenant_id: str | None = None
    actor_user_id: str | None = None
    issued_before: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)
    reason: str | None = None
    dry_run: bool = False


class IntakeReplayExportTokenBulkRevokeActiveResponse(BaseModel):
    tenant_id: str
    dry_run: bool = False
    inspected_tokens: int
    candidate_count: int
    revoked_count: int
    skipped_consumed_count: int
    skipped_revoked_count: int
    skipped_expired_count: int
    candidate_token_ids: list[str] = []
    revoked_token_ids: list[str] = []
    revoked_at: datetime


class IntakeReplayExportTokenAuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    actor_user_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class IntakeReplayExportTokenAuditHistoryListResponse(BaseModel):
    items: list[IntakeReplayExportTokenAuditEntryResponse] = []
    limit: int
    has_more: bool
    next_cursor_created_at: datetime | None = None
    next_cursor_id: str | None = None
    sort: str


class IntakeReplayExportTokenAuditSummaryResponse(BaseModel):
    total_entries: int
    issued_count: int
    consumed_count: int
    revoked_count: int
    consume_rate_percent: float | None = None
    revoke_rate_percent: float | None = None
    unique_actor_count: int
    latest_created_at: datetime | None = None


class IntakeReplayExportTokenAuditTrendBucketResponse(BaseModel):
    bucket_start_created_at: datetime
    issued_count: int
    consumed_count: int
    revoked_count: int
    total_count: int


class IntakeReplayExportTokenAuditTrendResponse(BaseModel):
    items: list[IntakeReplayExportTokenAuditTrendBucketResponse] = []
    granularity: str
    window_start_created_at: datetime | None = None
    window_end_created_at: datetime | None = None
    window_effective_timezone: str = "UTC"


class IntakeReplayExportTokenStateResponse(BaseModel):
    token_id: str
    tenant_id: str
    state: str
    issued_at: datetime
    issued_by_user_id: str
    consumed_at: datetime | None = None
    consumed_by_user_id: str | None = None
    revoked_at: datetime | None = None
    revoked_by_user_id: str | None = None
    expires_at: datetime
    latest_activity_at: datetime
    event_id: str | None = None
    output: str | None = None
    export_limit: int | None = None


class IntakeReplayExportTokenStateListResponse(BaseModel):
    items: list[IntakeReplayExportTokenStateResponse] = []
    limit: int
    has_more: bool
    next_cursor_issued_at: datetime | None = None
    next_cursor_token_id: str | None = None
    sort: str
    window_start_issued_at: datetime | None = None
    window_end_issued_at: datetime | None = None
    window_effective_timezone: str = "UTC"


class IntakeReplayExportTokenActorStateSummaryResponse(BaseModel):
    actor_user_id: str
    total_tokens: int
    issued_tokens: int
    consumed_tokens: int
    revoked_tokens: int
    expired_tokens: int


class IntakeReplayExportTokenStateSummaryResponse(BaseModel):
    window_start_issued_at: datetime | None = None
    window_end_issued_at: datetime | None = None
    window_effective_timezone: str = "UTC"
    total_tokens: int
    issued_tokens: int
    consumed_tokens: int
    revoked_tokens: int
    expired_tokens: int
    actors: list[IntakeReplayExportTokenActorStateSummaryResponse] = []


class IntakeReplayExportTokenStateAlertsResponse(BaseModel):
    as_of: datetime
    stale_threshold_minutes: int
    stale_active_threshold_count: int
    window_start_issued_at: datetime | None = None
    window_end_issued_at: datetime | None = None
    window_effective_timezone: str = "UTC"
    total_tokens: int
    active_tokens: int
    active_tokens_older_than_threshold: int
    active_tokens_older_than_threshold_exceeded: bool
    consumed_tokens: int
    revoked_tokens: int
    consumed_to_revoked_ratio: float | None = None


class TicketBase(BaseModel):
    intake_item_id: str | None = None
    project_id: str | None = None
    ticket_number: str = ""
    truck: str = ""
    driver: str = ""
    material: str = ""
    origin: str = ""
    destination: str = ""
    load_time: datetime | None = None
    unload_time: datetime | None = None
    miles: Decimal | None = None
    weight: Decimal | None = None
    volume_yards: Decimal | None = None
    tons: Decimal | None = None
    fuel_cost: Decimal | None = None
    revenue: Decimal | None = None
    status: str = Field(default="draft", min_length=2, max_length=30)
    notes: str = ""
    source_document_path: str = ""


class TicketCreate(TicketBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "ticket_number": "TCK-1001",
                "truck": "Unit 24",
                "driver": "Alex Ramos",
                "material": "Aggregate",
                "origin": "Pit A",
                "destination": "Site B",
                "status": "draft",
                "notes": "Entered from dispatch board",
            }
        }
    )


class TicketUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "approved",
                "notes": "Reviewed and approved by operations",
                "revenue": "1450.00",
            }
        }
    )

    intake_item_id: str | None = None
    project_id: str | None = None
    ticket_number: str | None = None
    truck: str | None = None
    driver: str | None = None
    material: str | None = None
    origin: str | None = None
    destination: str | None = None
    load_time: datetime | None = None
    unload_time: datetime | None = None
    miles: Decimal | None = None
    weight: Decimal | None = None
    volume_yards: Decimal | None = None
    tons: Decimal | None = None
    fuel_cost: Decimal | None = None
    revenue: Decimal | None = None
    status: str | None = Field(default=None, min_length=2, max_length=30)
    notes: str | None = None


class TicketResponse(TicketBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e6f6ea2f-b4c8-4e35-8134-5fc633c23f35",
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "intake_item_id": "15c0642b-b342-4935-973a-d142e90b6b92",
                "project_id": "b9c8f6d7-6a9c-4ea5-b5fb-801d343bdb48",
                "ticket_number": "TCK-1001",
                "truck": "Unit 24",
                "driver": "Alex Ramos",
                "material": "Aggregate",
                "origin": "Pit A",
                "destination": "Site B",
                "load_time": "2026-07-25T14:30:00Z",
                "unload_time": "2026-07-25T15:10:00Z",
                "miles": "23.50",
                "weight": "42000.00",
                "volume_yards": "16.00",
                "tons": "21.00",
                "fuel_cost": "58.20",
                "revenue": "1450.00",
                "status": "approved",
                "notes": "Reviewed and approved by operations",
                "created_by": "7e4e28dc-5038-4025-8e4c-a64fd3b76156",
                "created_at": "2026-07-25T15:32:16.935131Z",
                "updated_at": "2026-07-25T15:35:01.128927Z"
            }
        },
    )

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class TicketFromIntakeCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_number": "OVERRIDE-001",
                "truck": "Unit Z",
                "driver": "Override Driver",
                "status": "approved",
                "notes": "Manual override applied",
            }
        }
    )

    project_id: str | None = Field(default=None, description="Optional target project ID for the generated ticket.")
    ticket_number: str | None = Field(default=None, description="Override for ticket number from extracted entities.")
    truck: str | None = Field(default=None, description="Override for truck/unit value.")
    driver: str | None = Field(default=None, description="Override for driver name.")
    material: str | None = Field(default=None, description="Override for hauled material.")
    origin: str | None = Field(default=None, description="Override for origin location.")
    destination: str | None = Field(default=None, description="Override for destination location.")
    load_time: datetime | None = Field(default=None, description="Override for load timestamp in ISO 8601 format.")
    unload_time: datetime | None = Field(default=None, description="Override for unload timestamp in ISO 8601 format.")
    miles: Decimal | None = Field(default=None, description="Override for miles value.")
    weight: Decimal | None = Field(default=None, description="Override for weight value.")
    volume_yards: Decimal | None = Field(default=None, description="Override for volume in cubic yards.")
    tons: Decimal | None = Field(default=None, description="Override for tons value.")


class TicketQuantityCalculationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "gross_weight_lbs": "54000",
                "tare_weight_lbs": "32000",
                "number_of_loads": 4,
                "truck_type": "triaxle",
                "material_density_tons_per_cubic_yard": "1.50",
                "rate_per_ton": "12.50",
            }
        }
    )

    gross_weight_lbs: Decimal | None = Field(default=None, ge=0)
    tare_weight_lbs: Decimal | None = Field(default=None, ge=0)
    net_weight_lbs: Decimal | None = Field(default=None, ge=0)
    material_name: str | None = Field(default=None, min_length=1, max_length=120)
    number_of_loads: int | None = Field(default=None, ge=1)
    truck_type: str | None = Field(default=None, max_length=40)  # tandem|triaxle|quad|quint
    truck_capacity_tons: Decimal | None = Field(default=None, gt=0)
    material_density_tons_per_cubic_yard: Decimal | None = Field(default=None, gt=0)
    rate_per_ton: Decimal | None = Field(default=None, ge=0)
    rate_per_cubic_yard: Decimal | None = Field(default=None, ge=0)
    rate_per_load: Decimal | None = Field(default=None, ge=0)


class TicketQuantityCalculationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "net_weight_lbs": "22000.00",
                "net_tons": "11.00",
                "estimated_cubic_yards": "7.33",
                "estimated_load_count": "4.00",
                "tons_per_load": "2.75",
                "cubic_yards_per_load": "1.83",
                "cost_from_ton": "137.50",
                "cost_from_cubic_yard": "131.94",
                "cost_from_load": "260.00",
                "selected_cost_method": "per_ton",
                "selected_total_cost": "137.50",
                "assumptions": [
                    "net_weight_lbs derived from gross_weight_lbs - tare_weight_lbs"
                ]
            }
        }
    )

    net_weight_lbs: Decimal | None = None
    net_tons: Decimal | None = None
    total_tons: Decimal | None = None          # tons across all loads
    total_cubic_yards: Decimal | None = None   # volume across all loads
    estimated_cubic_yards: Decimal | None = None
    estimated_load_count: Decimal | None = None
    tons_per_load: Decimal | None = None
    cubic_yards_per_load: Decimal | None = None
    cost_from_ton: Decimal | None = None
    cost_from_cubic_yard: Decimal | None = None
    cost_from_load: Decimal | None = None
    selected_cost_method: str | None = None
    selected_total_cost: Decimal | None = None
    resolved_material_name: str | None = None
    resolved_density_source: str | None = None
    weight_method: str | None = None           # "actual" | "estimated"
    resolved_truck_type: str | None = None
    resolved_truck_capacity_tons: Decimal | None = None
    assumptions: list[str] = []


class MaterialDensityPresetUpsertRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "density_tons_per_cubic_yard": "1.45"
            }
        }
    )

    density_tons_per_cubic_yard: Decimal = Field(gt=0)


class MaterialDensityPresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    material_name: str
    density_tons_per_cubic_yard: Decimal
    created_by: str
    created_at: datetime
    updated_at: datetime


class TicketCalculatorPrefillResponse(BaseModel):
    material_name: str | None = None
    gross_weight_lbs: str | None = None
    tare_weight_lbs: str | None = None
    net_weight_lbs: str | None = None
    number_of_loads: int | None = None


class TicketUploadExtractionItemResponse(BaseModel):
    filename: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    extracted_summary: str
    extracted_text_preview: str | None = None
    extraction_confidence: float = 0.0
    review_required: bool = False
    extracted_entities: dict[str, str] = Field(default_factory=dict)
    calculator_prefill: TicketCalculatorPrefillResponse
    created_ticket_id: str | None = None
    duplicate_ticket_id: str | None = None


class TicketUploadExtractionResponse(BaseModel):
    items: list[TicketUploadExtractionItemResponse] = []


# ============================================================================
# OCR/AI Document Extraction Schemas
# ============================================================================

class DocumentExtractionIssueResponse(BaseModel):
    """Issue detected in document extraction (low confidence, missing field, validation error)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "issue-123",
                "issue_type": "low_confidence",
                "field_name": "destination",
                "severity": "warning",
                "message": "Destination address confidence is only 55%",
                "suggested_value": "123 Main St, Portland OR",
                "correction_source": "project_location",
                "resolved": False,
            }
        },
    )

    id: str
    issue_type: str
    field_name: str
    severity: str
    message: str
    suggested_value: str | None = None
    correction_source: str | None = None
    resolved: bool
    resolved_value: str | None = None


class DocumentExtractionResponse(BaseModel):
    """Complete document extraction with all extracted fields and confidence scores."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "extraction-123",
                "intake_item_id": "item-123",
                "document_type": "ticket",
                "document_type_confidence": 0.95,
                "status": "review_pending",
                "company_name": "Acme Hauling",
                "company_name_confidence": 0.88,
                "ticket_number": "TCK-2026-001",
                "ticket_number_confidence": 0.92,
                "destination": "456 Oak Ave, Portland OR",
                "destination_confidence": 0.72,
                "material": "Topsoil",
                "material_confidence": 0.85,
                "tons": "12.50",
                "invoice_total": "450.00",
                "review_notes": "",
                "created_at": "2026-07-27T10:30:00Z",
            }
        },
    )

    id: str
    tenant_id: str
    intake_item_id: str
    source_file_url: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    extracted_text_preview: str | None = None
    document_type: str
    document_type_confidence: float
    status: str
    project_name: str = ""
    project_name_confidence: float = 0.0
    company_name: str
    company_name_confidence: float
    ticket_number: str
    ticket_number_confidence: float
    destination: str
    destination_confidence: float
    material: str
    material_confidence: float
    tons: Decimal | None = None
    invoice_total: Decimal | None = None
    canonical_profile: str | None = None
    canonical_revision: int | None = None
    canonical_payload: dict[str, Any] | None = None
    canonical_discrepancies: list[dict[str, Any]] | None = None
    canonical_source_facts: list[dict[str, str | float | int | None]] | None = None
    precedence_decisions: list[dict[str, str | float | int | None]] | None = None
    discrepancy_summary: dict[str, int | float | str | None] | None = None
    estimate_mapping_preview: dict[str, Any] | None = None
    geotech_profile: list[dict[str, str | float | int | None]] | None = None
    review_notes: str
    created_at: datetime
    created_by: str


class ExtractionReviewRequest(BaseModel):
    """Request to review and correct extracted fields."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "review_notes": "Verified against original document. Minor correction to destination.",
                "corrections": {
                    "destination": "456 Oak Avenue, Portland OR 97214",
                    "tons": "12.75",
                },
            }
        }
    )

    review_notes: str = Field(default="", max_length=2000)
    corrections: dict[str, str] = Field(default_factory=dict, description="Field name → corrected value")


class ExtractionApprovalRequest(BaseModel):
    """Request to approve or reject extraction for distribution."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "approve": True,
                "approval_notes": "All issues resolved. Ready for distribution.",
                "rejection_reason": None,
            }
        }
    )

    approve: bool = Field(description="True to approve, False to reject")
    approval_notes: str = Field(default="", max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class ExtractionApprovalResponse(BaseModel):
    """Response after approval with distribution results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "extraction_id": "extraction-123",
                "status": "distributed",
                "ticket_created_id": "ticket-456",
                "distributed_at": "2026-07-27T10:45:00Z",
                "distribution_summary": {
                    "ticket_created": True,
                    "project_updated": True,
                    "vendor_created": False,
                    "dispatch_updated": False,
                },
            }
        }
    )

    extraction_id: str
    status: str
    ticket_created_id: str | None = None
    distributed_at: datetime | None = None
    distribution_summary: dict[str, bool] = Field(default_factory=dict)


class ExtractionListItemResponse(BaseModel):
    """Extraction item in list view."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "extraction-123",
                "status": "review_pending",
                "document_type": "ticket",
                "company_name": "Acme Hauling",
                "ticket_number": "TCK-2026-001",
                "issue_count": 2,
                "avg_confidence": 0.81,
                "created_at": "2026-07-27T10:30:00Z",
            }
        },
    )

    id: str
    status: str
    document_type: str
    company_name: str
    ticket_number: str
    issue_count: int = 0
    avg_confidence: float = 0.0
    created_at: datetime


class ExtractionListResponse(BaseModel):
    """List of pending extractions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "extraction-123",
                        "status": "review_pending",
                        "document_type": "ticket",
                        "company_name": "Acme Hauling",
                        "ticket_number": "TCK-2026-001",
                        "issue_count": 2,
                        "avg_confidence": 0.81,
                        "created_at": "2026-07-27T10:30:00Z",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        }
    )

    items: list[ExtractionListItemResponse] = []
    total: int = 0
    limit: int = 50
    offset: int = 0


class ExtractionTriggerResponse(BaseModel):
    """Response after triggering OCR extraction for an intake item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "extraction_id": "extraction-123",
                "intake_item_id": "intake-456",
                "status": "review_pending",
                "document_type": "ticket",
                "issue_count": 2,
                "fields_extracted": 9,
                "is_new": True,
            }
        }
    )

    extraction_id: str
    intake_item_id: str
    status: str
    document_type: str
    issue_count: int = 0
    fields_extracted: int = 0
    is_new: bool = True


class ExtractionDetailResponse(BaseModel):
    """Complete extraction detail with all issues."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "extraction": {"id": "extraction-123"},
                "issues": [
                    {
                        "id": "issue-1",
                        "issue_type": "low_confidence",
                        "field_name": "destination",
                        "severity": "warning",
                        "message": "Destination address confidence is only 55%",
                        "suggested_value": "123 Main St, Portland OR",
                        "resolved": False,
                    }
                ],
            }
        }
    )

    extraction: DocumentExtractionResponse
    issues: list[DocumentExtractionIssueResponse] = []
