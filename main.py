"""
Love Backend Application Entry Point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.core.middleware import SessionMiddleware
from app.router.endpoints import api_router
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting application...")
    
    # Initialize Redis
    from app.session.session_layer import init_redis
    try:
        init_redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            session_ttl=settings.SESSION_TTL
        )
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
        
        # Auto-create tables in debug mode (use Alembic migrations in production)
        if settings.DEBUG:
            from app.core.database import Base
            from app.model import User, Contact, Postcard, Mailing, ChatRoom, ChatParticipant, ChatMessage
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created (DEBUG mode)")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Ensure upload directory exists for postcard images
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    yield
    
    logger.info("Shutting down...")
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware
app.add_middleware(SessionMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)

# Serve uploaded postcard images at /uploads/... (directory must exist before mount)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Welcome to the Love Backend API!"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
