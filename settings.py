

from pydantic_settings import BaseSettings
from pydantic_settings.main import SettingsConfigDict



class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    DATABASE_URL: str = "postgresql+asyncpg://myuser:mypassword@localhost:5433/mydb"
    REDIS_URL: str = "redis://localhost:6380"
    DEDUP_STRICT_MODE: bool = False
    DEDUP_TTL_SECONDS: int  = 86400

settings = Settings()