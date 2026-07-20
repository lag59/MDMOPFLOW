from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
import time

from app.api.routes import admin, auth, health, onboarding, projects, tenant_users
from app.core.config import settings

from app.db import SessionLocal
from app.models import PlatformRole, User
from app.security import hash_password

app=FastAPI(title="MDM OpsFlow API",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.ALLOWED_ORIGINS.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(projects.router)
app.include_router(tenant_users.router)


@app.on_event("startup")
def on_startup():
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
            return
        except OperationalError:
            time.sleep(1)

    raise RuntimeError("Database unavailable after startup retries")


@app.get("/")
async def root():
    return {"name":"MDM OpsFlow","tagline":"The AI Operating System for Construction"}
