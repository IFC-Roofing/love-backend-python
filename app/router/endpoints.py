"""
API Router - all endpoints.
"""
from fastapi import APIRouter
from app.router.api.v1 import auth, users, contacts, postcards, mailings

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    contacts.router,
    prefix="/contacts",
    tags=["Contacts"],
)

api_router.include_router(
    postcards.router,
    prefix="/postcards",
    tags=["Postcards"],
)

api_router.include_router(
    mailings.router,
    prefix="/mailings",
    tags=["Mailings"],
)
