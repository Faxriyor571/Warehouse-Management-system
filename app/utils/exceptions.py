"""Domain-level exceptions.

These are raised by the service/CRUD layers and translated into HTTP responses
by the exception handlers registered in :mod:`app.main`. Keeping them free of
FastAPI/HTTP details keeps the business logic framework-agnostic.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors.

    Attributes:
        message: Human readable, user-facing error message.
        status_code: Suggested HTTP status code for the API layer.
    """

    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404


class ConflictError(AppError):
    """Raised when an operation conflicts with the current state (e.g. duplicate)."""

    status_code = 409


class ValidationError(AppError):
    """Raised when business validation fails (beyond schema validation)."""

    status_code = 422


class InsufficientStockError(ValidationError):
    """Raised when a stock-out requests more quantity than is available."""


class AuthenticationError(AppError):
    """Raised when authentication fails (bad credentials / invalid token)."""

    status_code = 401


class PermissionDeniedError(AppError):
    """Raised when the current user lacks the required permission."""

    status_code = 403
