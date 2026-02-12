"""
FastAPI dependencies for route protection.
"""
from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.exceptions import NotAuthenticated, SessionExpired
from typing import Dict, Any

# Security scheme for OpenAPI docs (shows lock icon and Authorization header)
bearer_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="JWT token from login endpoint"
)


async def validate_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Validates session loaded by middleware.
    
    Returns:
        User data dict with user_id, email, is_active
        
    Raises:
        NotAuthenticated: No token provided
        SessionExpired: Token not found in Redis
    """
    if not request.state.token:
        raise NotAuthenticated()
    
    if not request.state.session:
        raise SessionExpired()
    
    return request.state.session


def get_current_token(request: Request) -> str:
    """Get current token from request state."""
    if not request.state.token:
        raise NotAuthenticated()
    return request.state.token
