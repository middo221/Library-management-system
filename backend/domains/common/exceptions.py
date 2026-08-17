"""Domain exceptions.

Services raise these; they know nothing about HTTP beyond a suggested status code, which
keeps ``services.py`` free of DRF imports while still letting the handler answer sensibly.
"""

from typing import Any

from domains.common import error_codes


class DomainError(Exception):
    """Base class for every business-rule failure."""

    code: str = error_codes.CONFLICT
    message: str = "The request could not be completed."
    status_code: int = 409

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        self.status_code = status_code or self.status_code
        super().__init__(self.message)

    def to_envelope(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class ValidationError(DomainError):
    code = error_codes.VALIDATION_ERROR
    message = "The submitted data was invalid."
    status_code = 400


class NotFoundError(DomainError):
    code = error_codes.NOT_FOUND
    message = "The requested resource does not exist."
    status_code = 404


class PermissionDeniedError(DomainError):
    code = error_codes.PERMISSION_DENIED
    message = "You do not have permission to perform this action."
    status_code = 403


class ConflictError(DomainError):
    """A rule about the current state of the world was violated."""

    code = error_codes.CONFLICT
    status_code = 409
