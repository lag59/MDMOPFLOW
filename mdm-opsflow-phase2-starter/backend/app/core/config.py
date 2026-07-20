from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT:str="development"
    SECRET_KEY:str="change-me"
    DATABASE_URL:str="sqlite:///./mdm_opsflow.db"
    ALLOWED_ORIGINS:str="http://localhost:3000"
    OPENAI_API_KEY:str|None=None
    PORT:int=8080
    ACCESS_TOKEN_MINUTES:int=30
    REFRESH_TOKEN_MINUTES:int=20160
    SUPER_ADMIN_EMAIL:str="founder@mdmopsflow.com"
    SUPER_ADMIN_PASSWORD:str="ChangeMe123!"
    FOUNDER_DISPLAY_NAME:str="Libia A. Gaviria, RN, BSN"
    FOUNDER_TITLE:str="Founder & CEO"
    model_config=SettingsConfigDict(env_file=".env")


settings=Settings()
