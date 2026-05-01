"""
Core Configuration — Pydantic Settings
=======================================
Loads all environment variables into a validated, typed config object.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/midnight_scholar"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI
    OPENAI_API_KEY: str = ""

    # Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "midnight_scholar_docs"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "midnight-scholar-pdfs"
    AWS_REGION: str = "ap-south-1"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    APP_NAME: str = "Midnight Scholar"
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
