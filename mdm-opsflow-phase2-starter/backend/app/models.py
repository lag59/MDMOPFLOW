import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PlatformRole(str, enum.Enum):
    PLATFORM_SUPER_ADMIN = "platform_super_admin"
    USER = "user"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    INACTIVE = "inactive"


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class IntakeStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"


class IngestionBatchStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_REVIEW = "completed_with_review"
    FAILED = "failed"


class TenantType(str, enum.Enum):
    PRODUCTION = "production"
    DEMO = "demo"
    TEST = "test"
    CANARY = "canary"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    company_type: Mapped[str] = mapped_column(String(120), nullable=False)
    tenant_type: Mapped[TenantType] = mapped_column(Enum(TenantType), default=TenantType.PRODUCTION, nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_by_automation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    test_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    selected_modules: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    platform_role: Mapped[PlatformRole] = mapped_column(Enum(PlatformRole), default=PlatformRole.USER, nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_by_automation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    test_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_title: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    capacity_tons: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="available", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    unit_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    truck_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    capacity_tons: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="available", nullable=False)
    assigned_driver: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    unit_of_measure: Mapped[str] = mapped_column(String(80), default="ton", nullable=False)
    density_tons_per_cubic_yard: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True, nullable=False)
    role_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roles.id"), index=True, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus), default=MembershipStatus.ACTIVE, nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UserPermissionOverride(Base):
    __tablename__ = "user_permission_overrides"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "permission", name="uq_user_permission_overrides_scope"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True, nullable=False)
    permission: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_number: Mapped[str] = mapped_column(String(80), nullable=False)
    customer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_manager: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.PLANNING, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=True)
    actor_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(120), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    before_values_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    after_values_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class DailyFieldReport(Base):
    __tablename__ = "daily_field_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=False)
    report_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reporting_supervisor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    shift_start_time: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    shift_end_time: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    weather: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    work_performed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    work_planned_for_tomorrow: Mapped[str] = mapped_column(Text, default="", nullable=False)
    crew_members: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    equipment_used: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    deliveries: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    visitors: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    delays: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    photos: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    production_quantities: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    safety_observations: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    prepared_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    electronic_signature: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PayrollTimecard(Base):
    __tablename__ = "payroll_timecards"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("employees.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    work_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    regular_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    overtime_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    double_time_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    cost_code: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    work_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    run_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_regular_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_overtime_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_double_time_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class EstimatorTakeoff(Base):
    __tablename__ = "estimator_takeoffs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    takeoff_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    material_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(40), default="cy", nullable=False)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimatorVersion(Base):
    __tablename__ = "estimator_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    version_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estimated_revenue: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimatorBidPipelineItem(Base):
    __tablename__ = "estimator_bid_pipeline_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    bid_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="qualifying", nullable=False)
    bid_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    probability_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimatorWinLossRecord(Base):
    __tablename__ = "estimator_win_loss_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    bid_pipeline_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("estimator_bid_pipeline_items.id"), index=True, nullable=True)
    outcome: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)
    final_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Estimate(Base):
    __tablename__ = "estimates"
    __table_args__ = (UniqueConstraint("tenant_id", "estimate_number", name="uq_estimates_tenant_number"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    estimate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    estimate_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    bid_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimator_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_manager_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sales_contact: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    contract_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    estimate_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    currency: Mapped[str] = mapped_column(String(12), default="USD", nullable=False)
    tax_jurisdiction: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    target_margin_percent: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    default_overhead_percent: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    default_contingency_percent: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="New", nullable=False, index=True)
    approval_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimateItem(Base):
    __tablename__ = "estimate_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    estimate_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("estimates.id"), index=True, nullable=False)
    item_number: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    cost_code: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    division: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    phase: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    work_location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=0, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 4), default=0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 4), default=0, nullable=False)
    total_selling_price: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="manual", nullable=False)
    assumption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimateDocument(Base):
    __tablename__ = "estimate_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    estimate_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("estimates.id"), index=True, nullable=False)
    intake_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), default="Unknown document", nullable=False)
    processing_status: Mapped[str] = mapped_column(String(40), default="Uploaded", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    version_label: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="Review recommended", nullable=False)
    uploaded_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimateApproval(Base):
    __tablename__ = "estimate_approvals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    estimate_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("estimates.id"), index=True, nullable=False)
    approver_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    decision: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EstimateAuditLog(Base):
    __tablename__ = "estimate_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    estimate_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("estimates.id"), index=True, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    new_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VendorPurchaseOrder(Base):
    __tablename__ = "vendor_purchase_orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    po_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    total_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VendorInvoiceSubmission(Base):
    __tablename__ = "vendor_invoice_submissions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    purchase_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("vendor_purchase_orders.id"), index=True, nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VendorDeliveryRecord(Base):
    __tablename__ = "vendor_delivery_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    purchase_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("vendor_purchase_orders.id"), index=True, nullable=True)
    ticket_number: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    destination: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VendorComplianceDocument(Base):
    __tablename__ = "vendor_compliance_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="current", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IntakeItem(Base):
    __tablename__ = "intake_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    batch_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("ingestion_batches.id"), index=True, nullable=True)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_document_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_type: Mapped[str] = mapped_column(String(120), default="general", nullable=False)
    classification_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    match_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="manual", nullable=False)
    status: Mapped[IntakeStatus] = mapped_column(
        Enum(
            IntakeStatus,
            name="intakestatus",
            values_callable=lambda items: [item.value for item in items],
        ),
        default=IntakeStatus.UPLOADED,
        nullable=False,
    )
    processing_stage: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    extracted_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extracted_entities: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    ocr_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    ai_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    duplicate_of_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), nullable=True)
    conflict_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(120), default="upload", nullable=False)
    status: Mapped[IngestionBatchStatus] = mapped_column(
        Enum(
            IngestionBatchStatus,
            name="ingestionbatchstatus",
            values_callable=lambda items: [item.value for item in items],
        ),
        default=IngestionBatchStatus.QUEUED,
        nullable=False,
    )
    total_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_review_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class MaterialDensityPreset(Base):
    __tablename__ = "material_density_presets"
    __table_args__ = (UniqueConstraint("tenant_id", "material_name", name="uq_material_density_presets_tenant_material"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    material_name: Mapped[str] = mapped_column(String(120), nullable=False)
    density_tons_per_cubic_yard: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    intake_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), nullable=True)
    extraction_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("document_extractions.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), index=True, nullable=True)
    ticket_number: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    truck: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    driver: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    material: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    destination: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    load_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unload_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    miles: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    weight: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    volume_yards: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tons: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    fuel_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_document_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class DocumentExtraction(Base):
    """
    Represents OCR extraction results with AI interpretation and confidence scores.
    Tracks the complete workflow from raw OCR to approved, distributed data.
    """
    __tablename__ = "document_extractions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    intake_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), index=True, nullable=False)
    
    # Document classification
    document_type: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    document_type_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    is_multi_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Hauling company
    company_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    company_name_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    
    # Document identifiers
    ticket_number: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ticket_number_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    invoice_number_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    job_number: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    job_number_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Dates and times
    ticket_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_date_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_time_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_time_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    total_hours_calculated: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Customer/Project
    customer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    customer_name_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_name_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    job_location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    job_location_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Driver/Operator
    driver_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    driver_name_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    driver_signature_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Truck/Trailer
    truck_number: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    truck_number_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    truck_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    truck_type_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Material
    material: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    material_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    material_category: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    origin_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    destination: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    destination_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Quantities
    load_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load_count_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    weight_net_lbs: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    weight_net_lbs_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    tons: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cubic_yards: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cubic_yards_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Rates and totals
    rate_per_ton: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    rate_per_load: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    invoice_total: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    invoice_total_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Processing workflow
    status: Mapped[str] = mapped_column(String(30), default="uploaded", nullable=False, index=True)
    
    # Human review
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    
    # Approval
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    
    # Distribution tracking
    distributed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_created_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tickets.id"), nullable=True)
    
    # OCR raw text
    ocr_raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extracted_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    canonical_profile: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    canonical_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    canonical_payload_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    canonical_discrepancies_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    
    # Audit
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ExtractionCanonicalFact(Base):
    __tablename__ = "extraction_canonical_facts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    extraction_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("document_extractions.id"), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    value_num: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    source_document_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    source_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    authority_level: Mapped[str] = mapped_column(String(40), default="informational", nullable=False)
    effective_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ExtractionDiscrepancy(Base):
    __tablename__ = "extraction_discrepancies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    extraction_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("document_extractions.id"), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    discrepancy_key: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    candidate_values_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommended_value_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


@event.listens_for(AuditLog, "before_update", propagate=True)
def _prevent_audit_log_update(mapper, connection, target):
    _ = mapper, connection, target
    raise ValueError("AuditLog is append-only and cannot be updated")


@event.listens_for(AuditLog, "before_delete", propagate=True)
def _prevent_audit_log_delete(mapper, connection, target):
    _ = mapper, connection, target
    raise ValueError("AuditLog is append-only and cannot be deleted")


class ExtractionIssue(Base):
    """
    Tracks data quality issues, warnings, and flags during OCR/AI extraction.
    """
    __tablename__ = "extraction_issues"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    extraction_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("document_extractions.id"), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    
    # Issue classification
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Suggested correction
    suggested_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    correction_source: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    
    # Resolution
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
