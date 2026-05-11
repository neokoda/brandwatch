import os
from pydantic_settings import BaseSettings
from pydantic import field_validator

_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str

    HUGGINGFACE_API_TOKEN: str = ""
    GOOGLE_AI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "brandwatch/1.0"

    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_EXPIRE_MINUTES: int = 1440

    DEFAULT_ALERT_NEGATIVITY_SURGE_Z: float = 2.5
    DEFAULT_ALERT_VOLUME_SPIKE_Z: float = 3.0
    DEFAULT_ALERT_CRISIS_NEG_SHARE: float = 0.65
    INFLUENCER_FOLLOWER_THRESHOLD: int = 10000

    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_db_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg uses ssl=require, not sslmode=require (psycopg2 param)
        v = v.replace("sslmode=require", "ssl=require")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = _ENV_FILE


settings = Settings()
