"""
API Router - all endpoints.
"""
from fastapi import APIRouter
from app.router.api.v1 import auth, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["Users"]
)
