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

    # Optional
    DEBUG: bool = False
    PROJECT_NAME: str = "Love Backend"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Load secrets from AWS Secrets Manager only when DB creds aren't already
# provided via environment variables (e.g. in Docker / local dev).
if not settings.DB_HOST:
    from app.aws.secrets import get_secret

    _db_secret = get_secret('love-backend/db', region_name=settings.AWS_REGION)
    settings.DB_HOST = _db_secret['host']
    settings.DB_PORT = int(_db_secret.get('port', 5432))
    settings.DB_NAME = _db_secret['database']
    settings.DB_USER = _db_secret['username']
    settings.DB_PASS = _db_secret['password']

    _cognito_secret = get_secret('love-backend/cognito', region_name=settings.COGNITO_REGION)
    settings.COGNITO_USER_POOL_ID = _cognito_secret['user_pool_id']
    settings.COGNITO_CLIENT_ID = _cognito_secret['client_id']
    settings.COGNITO_CLIENT_SECRET = _cognito_secret.get('client_secret')
