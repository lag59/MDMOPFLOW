from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    ENVIRONMENT:str="development"
    SECRET_KEY:str="change-me"
    DATABASE_URL:str="sqlite:///./mdm_opsflow.db"
    ALLOWED_ORIGINS:str="http://localhost:3000"
    OPENAI_API_KEY:str|None=None
    PORT:int=8080
    model_config=SettingsConfigDict(env_file=".env")
settings=Settings()
