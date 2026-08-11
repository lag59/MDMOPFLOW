from html import unescape

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def _normalize_database_url(value: str) -> str:
    normalized = unescape(value.strip())

    # Common copy/paste issue from dashboards or .env files.
    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        normalized = normalized[1:-1].strip()

    # Railway and some providers expose postgres:// by default.
    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://") :]

    return normalized


class Settings(BaseSettings):
    ENVIRONMENT:str="development"
    SECRET_KEY:str="change-me"
    DATABASE_URL:str="postgresql+psycopg://postgres:OpsFlow2026Secure@localhost:5432/opsflow"
    RATE_LIMIT_REQUESTS_PER_WINDOW:int=300
    RATE_LIMIT_WINDOW_SECONDS:int=60
    ALLOWED_ORIGINS:str=(
        "http://localhost:3000,"
        "https://sincere-quietude-production-e3c9.up.railway.app,"
        "https://www.mdmopflow.com,"
        "https://mdmopflow.com"
    )
    OPENAI_API_KEY:str|None=None
    OPENAI_MODEL:str="gpt-5"
    TICKET_MINIMUM_AUTO_ACCEPT_CONFIDENCE:float=0.85
    TICKET_MINIMUM_REQUIRED_CONFIDENCE:float=0.70
    TICKET_PDF_RENDER_DPI:int=300
    PORT:int=8080
    ACCESS_TOKEN_MINUTES:int=30
    REFRESH_TOKEN_MINUTES:int=20160
    INTAKE_REPLAY_EXPORT_TOKEN_MINUTES:int=5
    SUPER_ADMIN_EMAIL:str="lag59@mdmopflow.com"
    SUPER_ADMIN_PASSWORD:str="ChangeMe123!"
    FOUNDER_DISPLAY_NAME:str="lag59"
    FOUNDER_TITLE:str="Platform Super Admin"
    model_config=SettingsConfigDict(env_file=".env")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "DATABASE_URL must be a non-empty SQLAlchemy URL. "
                "Example: postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"
            )

        normalized = _normalize_database_url(value)

        try:
            make_url(normalized)
        except ArgumentError as exc:
            raise ValueError(
                "DATABASE_URL is invalid. Expected SQLAlchemy format like "
                "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"
            ) from exc

        return normalized


settings=Settings()
