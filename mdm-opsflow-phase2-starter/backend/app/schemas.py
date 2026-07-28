from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import IngestionBatchStatus, IntakeStatus, PlatformRole, ProjectStatus


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


class AssignTenantUserRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new.member@example.com",
                "role_name": "member",
            }
        }
    )

    email: EmailStr
    role_name: str = Field(min_length=2, max_length=100)


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


class AdminOverviewResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "MDM OpsFlow",
                "status": "foundation-ready",
                "role": "platform_super_admin",
                "tenants": 4,
                "users": 18,
                "projects": 12,
            }
        }
    )

    platform: str
    status: str
    role: str
    tenants: int
    users: int
    projects: int


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
            }
        }
    )

    id: str
    email: str
    display_name: str
    title: str
    platform_role: PlatformRole
    is_active: bool


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


class AdminTenantServiceSummaryItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "f2a4f8f1-8439-4fa4-b9d0-5dcf8a5f9a8d",
                "tenant_name": "Acme Civil",
                "users": 12,
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
    users: int
    projects: int
    tickets: int
    intake_items: int
    extractions: int
    pending_reviews: int


class AdminTenantServiceSummaryResponse(BaseModel):
    items: list[AdminTenantServiceSummaryItem]


class AdminServiceInsightsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenants": 4,
                "users": 18,
                "projects": 12,
                "tickets": 235,
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
    projects: int
    tickets: int
    intake_items: int
    intake_needs_review: int
    extractions_pending_review: int
    extractions_review_submitted: int
    unresolved_extraction_issues: int
    integration_events_pending: int
    integration_events_failed: int
    opportunities: list[str]


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
    document_type: str
    document_type_confidence: float
    status: str
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
