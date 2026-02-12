"""
Session Middleware - loads session from Redis for each request.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
from app.session import extract_token, get_session


class SessionMiddleware(BaseHTTPMiddleware):
    """Loads session from Redis based on Authorization header."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Initialize empty session
        request.state.session = {}
        request.state.token = None
        
        # Try to load session from Redis if token present
        auth_header = request.headers.get("authorization")
        token = extract_token(auth_header)
        
        if token:
            user_data = get_session(token)
            if user_data:
                request.state.session = user_data
                request.state.token = token
        
        response = await call_next(request)
        return response
