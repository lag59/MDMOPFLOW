from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT:str="development"
    SECRET_KEY:str="change-me"
    DATABASE_URL:str="sqlite:///./mdm_opsflow.db"
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
    SUPER_ADMIN_EMAIL:str="founder@mdmopsflow.com"
    SUPER_ADMIN_PASSWORD:str="ChangeMe123!"
    FOUNDER_DISPLAY_NAME:str="Libia A. Gaviria, RN, BSN"
    FOUNDER_TITLE:str="Founder & CEO"
    model_config=SettingsConfigDict(env_file=".env")


settings=Settings()
