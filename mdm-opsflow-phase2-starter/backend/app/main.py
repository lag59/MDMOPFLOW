from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, admin
from app.core.config import settings
app=FastAPI(title="MDM OpsFlow API",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.ALLOWED_ORIGINS.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health.router)
app.include_router(admin.router)
@app.get("/")
async def root():
    return {"name":"MDM OpsFlow","tagline":"The AI Operating System for Construction"}
