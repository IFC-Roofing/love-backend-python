"""
Application settings.
All secrets loaded from AWS Secrets Manager at startup.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # AWS
    AWS_REGION: str = "us-east-1"
    COGNITO_REGION: str = "us-east-1"

    # Database (loaded from Secrets Manager)
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None

    # Cognito (loaded from Secrets Manager)
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    COGNITO_CLIENT_SECRET: Optional[str] = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    SESSION_TTL: int = 86400  # 24 hours in seconds

    # S3 (when set, postcards and profile images are stored in S3)
    S3_BUCKET_NAME: Optional[str] = None
    S3_REGION: Optional[str] = None  # defaults to AWS_REGION

    # Direct Mail Manager (physical postcard mailing). Set in .env.
    DIRECT_MAIL_MANAGER_API_URL: Optional[str] = None
    DIRECT_MAIL_MANAGER_API_KEY: Optional[str] = None
    DMM_FROM_ADDRESS: Optional[str] = None
    DMM_SENDER_COPY_ADDRESS: Optional[str] = None

    # Optional
    DEBUG: bool = False
    PROJECT_NAME: str = "Love Backend"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Local uploads fallback when S3_BUCKET_NAME is not set
    UPLOAD_DIR: str = "uploads"

    # Plat API (Rails) – for contact sync script
    PLAT_API_URL: Optional[str] = None  # e.g. http://localhost:3000 or http://host.docker.internal:3000
    PLAT_API_TOKEN: Optional[str] = None
    PLAT_SYNC_USER_ID: Optional[str] = None  # Our backend user UUID that will own synced contacts

    @property
    def use_s3(self) -> bool:
        return bool(self.S3_BUCKET_NAME)

    @property
    def use_dmm(self) -> bool:
        return bool(self.DIRECT_MAIL_MANAGER_API_URL and self.DIRECT_MAIL_MANAGER_API_KEY)

    @property
    def s3_region(self) -> str:
        return self.S3_REGION or self.AWS_REGION

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Load secrets from AWS Secrets Manager only when DB creds aren't already
# provided via environment variables (e.g. in Docker / local dev).
if not settings.DB_HOST:
    from app.aws.secrets import get_secret

    _db_secret = get_secret("love-backend/db", region_name=settings.AWS_REGION)
    settings.DB_HOST = _db_secret["host"]
    settings.DB_PORT = int(_db_secret.get("port", 5432))
    settings.DB_NAME = _db_secret["database"]
    settings.DB_USER = _db_secret["username"]
    settings.DB_PASS = _db_secret["password"]

    _cognito_secret = get_secret("love-backend/cognito", region_name=settings.COGNITO_REGION)
    settings.COGNITO_USER_POOL_ID = _cognito_secret["user_pool_id"]
    settings.COGNITO_CLIENT_ID = _cognito_secret["client_id"]
    settings.COGNITO_CLIENT_SECRET = _cognito_secret.get("client_secret")
# When DB_HOST is set (e.g. Docker with .env.docker), Cognito must be set in env:
# COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET in .env.docker
