from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.routes import admin, auth, ai_assignment, billing, health, intake, onboarding, projects, tenant_users, tickets, extractions
from app.core.config import settings

from app.db import SessionLocal
from app.models import PlatformRole, User
from app.security import hash_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    for _ in range(30):
        try:
            with SessionLocal() as db:
                founder = db.query(User).filter(User.email == settings.SUPER_ADMIN_EMAIL.lower()).first()
                if founder is None:
                    founder = User(
                        email=settings.SUPER_ADMIN_EMAIL.lower(),
                        password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                        display_name=settings.FOUNDER_DISPLAY_NAME,
                        title=settings.FOUNDER_TITLE,
                        platform_role=PlatformRole.PLATFORM_SUPER_ADMIN,
                    )
                    db.add(founder)
                    db.commit()
            break
        except OperationalError:
            time.sleep(1)
    else:
        raise RuntimeError("Database unavailable after startup retries")

    yield


openapi_tags = [
    {
        "name": "Health",
        "description": "Service liveness and environment diagnostics endpoint.",
    },
    {
        "name": "Authentication",
        "description": "Registration, login, session introspection, refresh, and logout endpoints.",
    },
    {
        "name": "Onboarding",
        "description": "Tenant bootstrap and initial account setup endpoints.",
    },
    {
        "name": "Projects",
        "description": "Tenant-scoped project CRUD endpoints.",
    },
    {
        "name": "Tenant Users",
        "description": "Tenant membership listing and assignment endpoints.",
    },
    {
        "name": "Platform Administration",
        "description": "Super-admin platform insights, audit, and permissions preview endpoints.",
    },
    {
        "name": "Intake Hub",
        "description": "Document intake, batch processing, extraction utilities, and review workflow endpoints.",
    },
    {
        "name": "Tickets",
        "description": "Ticket CRUD endpoints plus bridge creation from approved intake items.",
    },
    {
        "name": "Billing & Invoices",
        "description": "Invoice generation and billing calculation endpoints.",
    },
    {
        "name": "Extractions",
        "description": "Document extraction review, approval, and distribution workflow endpoints.",
    },
]

app = FastAPI(title="MDM OpsFlow API", version="0.1.0", lifespan=lifespan, openapi_tags=openapi_tags)
configured_origins = [x.strip() for x in settings.ALLOWED_ORIGINS.split(",") if x.strip()]
required_prod_origins = [
    "https://www.mdmopflow.com",
    "https://mdmopflow.com",
    "https://sincere-quietude-production-e3c9.up.railway.app",
]
allowed_origins = list(dict.fromkeys(configured_origins + required_prod_origins))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(projects.router)
app.include_router(intake.router)
app.include_router(tenant_users.router)
app.include_router(tickets.router)
app.include_router(billing.router)
app.include_router(ai_assignment.router)
app.include_router(extractions.router)


@app.get(
    "/",
    operation_id="root_get",
    summary="Get API banner",
    description="Returns API name and platform tagline.",
    responses={200: {"description": "API banner returned successfully."}},
)
async def root():
    return {"name": "MDM OpsFlow", "tagline": "The AI Operating System for Construction"}
