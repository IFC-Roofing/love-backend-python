"""
Application exceptions with frontend-friendly messages.
"""
from fastapi import HTTPException, status
from typing import Optional


class AppException(HTTPException):
    """Base exception with code, message, and hint."""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        hint: Optional[str] = None
    ):
        detail = {"code": code, "message": message}
        if hint:
            detail["hint"] = hint
        super().__init__(status_code=status_code, detail=detail)


class EmailAlreadyExists(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="EMAIL_EXISTS",
            message="This email is already registered.",
            hint="Try logging in instead."
        )


class InvalidCredentials(AppException):
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message=message
        )


class NotAuthenticated(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="NOT_AUTHENTICATED",
            message="You are not logged in.",
            hint="Please login to access this resource."
        )


class SessionExpired(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SESSION_EXPIRED",
            message="Your session has expired.",
            hint="Please login again."
        )


class NotFound(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"{resource} not found."
        )


class Forbidden(AppException):
    def __init__(self, message: str = "You don't have permission to access this resource."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message
        )
