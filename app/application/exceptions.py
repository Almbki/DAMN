"""Application-level exceptions.

The API layer maps these to HTTP status codes; services raise them instead of
``HTTPException`` so the application layer stays framework free.
"""

from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    """Base class for expected, user-facing application errors."""

    code: str = "application_error"
    http_status: int = 400

    def __init__(self, message: str = "", *, detail: Any = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__
        self.detail = detail


class NotFoundError(ApplicationError):
    code = "not_found"
    http_status = 404


class PermissionDeniedError(ApplicationError):
    code = "permission_denied"
    http_status = 403


class AuthenticationError(ApplicationError):
    code = "unauthorized"
    http_status = 401


class ConflictError(ApplicationError):
    code = "conflict"
    http_status = 409


class ReplanNotEligibleError(ConflictError):
    code = "replan_not_eligible"


class DomainValidationError(ApplicationError):
    code = "validation_error"
    http_status = 422
