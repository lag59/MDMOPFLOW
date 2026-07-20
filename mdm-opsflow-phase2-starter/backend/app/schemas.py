from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import PlatformRole, ProjectStatus


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=255)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
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
    user_id: str
    email: str
    display_name: str
    title: str
    role_name: str
    status: str


class MeResponse(BaseModel):
    id: str
    email: str
    display_name: str
    title: str
    platform_role: PlatformRole
    memberships: list[MeMembership]


class AssignTenantUserRequest(BaseModel):
    email: EmailStr
    role_name: str = Field(min_length=2, max_length=100)


class OnboardingRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    company_type: str
    language: str = Field(default="en", pattern="^(en|es)$")
    modules: list[str] = Field(default_factory=list)
    invite_emails: list[EmailStr] = Field(default_factory=list)
    first_project_name: str = Field(min_length=2, max_length=255)


class OnboardingResponse(BaseModel):
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
    pass


class ProjectUpdate(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
