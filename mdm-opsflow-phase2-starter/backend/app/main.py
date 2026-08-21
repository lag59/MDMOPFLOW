from contextlib import asynccontextmanager
import asyncio
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.api.routes import admin, auth, ai_assignment, ai_assist, billing, core_platform, customer_portal, daily_field_reports, dashboard, document_intake, estimator, extractions, health, intake, onboarding, payroll, projects, tenant_users, tickets, vendor
from app.core.config import settings

from app.db import SessionLocal
from app.migration_safety import assert_schema_is_current
from app.models import PlatformRole, User
from app.observability import bind_request_context, classify_status, clear_request_context, configure_logging
from app.security import hash_password


logger = logging.getLogger(__name__)
rate_limit_lock = asyncio.Lock()
rate_limit_windows: dict[str, deque[float]] = defaultdict(deque)

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    for _ in range(30):
        try:
            if settings.MIGRATION_ENFORCE_SCHEMA_ON_STARTUP:
                from app.db import engine

                assert_schema_is_current(engine)

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
                else:
                    founder.password_hash = hash_password(settings.SUPER_ADMIN_PASSWORD)
                    founder.display_name = settings.FOUNDER_DISPLAY_NAME
                    founder.title = settings.FOUNDER_TITLE
                    founder.platform_role = PlatformRole.PLATFORM_SUPER_ADMIN
                    founder.is_active = True
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
        "description": "Tenant membership listing/assignment plus per-user function-toggle endpoints.",
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
        "name": "Document Intake",
        "description": "OCR document classification, routing policy, and strict review/import JSON endpoints.",
    },
    {
        "name": "Tickets",
        "description": "Ticket CRUD endpoints plus bridge creation from approved intake items.",
    },
    {
        "name": "Daily Field Reports",
        "description": "Mobile-friendly daily field report creation, submission, review, and approval workflow.",
    },
    {
        "name": "Billing & Invoices",
        "description": "Invoice generation and billing calculation endpoints.",
    },
    {
        "name": "Payroll",
        "description": "Timecards, payroll runs, and labor allocation summary endpoints.",
    },
    {
        "name": "Estimator",
        "description": "Takeoff, estimate versioning, bid pipeline, and win/loss workflow endpoints.",
    },
    {
        "name": "Vendor Portal",
        "description": "Purchase orders, invoice submissions, delivery records, and compliance document endpoints.",
    },
    {
        "name": "Customer Portal",
        "description": "Portal-safe project, billing, and document visibility endpoints for customer members.",
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
app.include_router(core_platform.router)
app.include_router(projects.router)
app.include_router(intake.router)
app.include_router(document_intake.router)
app.include_router(tenant_users.router)
app.include_router(tickets.router)
app.include_router(daily_field_reports.router)
app.include_router(billing.router)
app.include_router(payroll.router)
app.include_router(estimator.router)
app.include_router(estimator.estimates_router)
app.include_router(ai_assist.router)
app.include_router(vendor.router)
app.include_router(customer_portal.router)
app.include_router(ai_assignment.router)
app.include_router(extractions.router)
app.include_router(dashboard.router)


_RATE_LIMIT_EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _rate_limit_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.method}:{request.url.path}"


def _get_retry_after_header(request_timestamp: float, window_seconds: int) -> str:
    retry_after = max(1, int(window_seconds - request_timestamp))
    return str(retry_after)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    bind_request_context(request_id=request_id, method=request.method, path=request.url.path)
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if isinstance(exc, SQLAlchemyError):
            logger.exception(
                "database_request_failed",
                extra={
                    "error_classification": "database_error",
                    "status_code": 500,
                    "latency_ms": elapsed_ms,
                },
            )
        else:
            logger.exception(
                "request_failed",
                extra={
                    "error_classification": "internal_error",
                    "status_code": 500,
                    "latency_ms": elapsed_ms,
                },
            )
        clear_request_context()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    logger.info(
        "request_completed",
        extra={
            "status_code": response.status_code,
            "error_classification": classify_status(response.status_code),
            "latency_ms": elapsed_ms,
        },
    )
    clear_request_context()
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _RATE_LIMIT_EXEMPT_PATHS:
        return await call_next(request)

    window_seconds = max(1, settings.RATE_LIMIT_WINDOW_SECONDS)
    max_requests = max(1, settings.RATE_LIMIT_REQUESTS_PER_WINDOW)
    now = time.monotonic()
    key = _rate_limit_key(request)

    async with rate_limit_lock:
        window = rate_limit_windows[key]
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()

        if len(window) >= max_requests:
            retry_after = _get_retry_after_header(now - window[0], window_seconds)
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
            )
            response.headers["Retry-After"] = retry_after
            return response

        window.append(now)

    return await call_next(request)


@app.get(
    "/",
    operation_id="root_get",
    summary="Get API banner",
    description="Returns API name and platform tagline.",
    responses={200: {"description": "API banner returned successfully."}},
)
async def root():
    return {"name": "MDM OpsFlow", "tagline": "The AI Operating System for Construction"}
