import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
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


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    company_type: Mapped[str] = mapped_column(String(120), nullable=False)
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
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


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


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), index=True, nullable=False)
    intake_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("intake_items.id"), nullable=True)
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
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
