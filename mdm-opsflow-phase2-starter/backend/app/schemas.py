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


class OnboardingRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "Acme Civil",
                "company_type": "General Contractor",
                "language": "en",
                "modules": ["Projects", "Intake"],
                "invite_emails": ["pm@example.com"],
                "first_project_name": "Downtown Site Prep",
            }
        }
    )

    company_name: str = Field(min_length=2, max_length=200)
    company_type: str
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
    items: list[IntakeItemResponse] = Field(default_factory=list)


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
    fuel_cost: Decimal | None = Field(default=None, description="Override for fuel cost.")
    revenue: Decimal | None = Field(default=None, description="Override for revenue.")
    status: str | None = Field(default=None, min_length=2, max_length=30)
    notes: str | None = Field(default=None, description="Override notes for the created ticket.")
