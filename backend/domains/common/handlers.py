"""The single exception handler. Every failure leaves the API in the same shape."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from domains.common import error_codes
from domains.common.exceptions import DomainError

logger = logging.getLogger("library.errors")

_DRF_CODE_MAP: dict[type[Exception], str] = {
    drf_exceptions.NotAuthenticated: error_codes.NOT_AUTHENTICATED,
    drf_exceptions.AuthenticationFailed: error_codes.NOT_AUTHENTICATED,
    drf_exceptions.PermissionDenied: error_codes.PERMISSION_DENIED,
    drf_exceptions.NotFound: error_codes.NOT_FOUND,
    drf_exceptions.MethodNotAllowed: error_codes.METHOD_NOT_ALLOWED,
    drf_exceptions.Throttled: error_codes.THROTTLED,
    drf_exceptions.ValidationError: error_codes.VALIDATION_ERROR,
}


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _flatten_validation_details(detail: Any) -> dict[str, Any]:
    """DRF nests validation errors arbitrarily; keep the shape but stringify the leaves."""
    if isinstance(detail, dict):
        return {key: _flatten_validation_details(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return [_flatten_validation_details(item) for item in detail]
    return str(detail)


def _readable_detail(detail: Any) -> str:
    """A sentence for a person.

    DRF's ``detail`` is sometimes a plain string, sometimes a dict of ``ErrorDetail`` objects
    (JWT authentication failures, for one). Stringifying the container leaks a Python repr
    into the response, so unwrap it to the first message it actually contains.
    """
    if detail is None or detail == "":
        return "The request could not be completed."
    if isinstance(detail, dict):
        preferred = detail.get("detail")
        candidates = [preferred] if preferred is not None else list(detail.values())
        return _readable_detail(next(iter(candidates), None))
    if isinstance(detail, list | tuple):
        return " ".join(_readable_detail(item) for item in detail) or (
            "The request could not be completed."
        )
    return str(detail)


def domain_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(exc.to_envelope(), status=exc.status_code)

    if isinstance(exc, Http404):
        return Response(
            _envelope(error_codes.NOT_FOUND, "The requested resource does not exist."),
            status=404,
        )

    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            _envelope(
                error_codes.PERMISSION_DENIED, "You do not have permission to perform this action."
            ),
            status=403,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            _envelope(
                error_codes.VALIDATION_ERROR,
                "The submitted data was invalid.",
                {"non_field_errors": list(exc.messages)},
            ),
            status=400,
        )

    if isinstance(exc, IntegrityError):
        logger.warning("integrity_error", extra={"detail": str(exc)})
        return Response(
            _envelope(
                error_codes.CONFLICT, "That operation conflicts with the current state of the data."
            ),
            status=409,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled — let Django's 500 machinery log it, but keep the envelope contract.
        logger.exception("unhandled_exception")
        return None

    code = next(
        (value for klass, value in _DRF_CODE_MAP.items() if isinstance(exc, klass)),
        error_codes.INTERNAL_ERROR,
    )

    if isinstance(exc, drf_exceptions.ValidationError):
        details = _flatten_validation_details(exc.detail)
        if isinstance(details, list):
            details = {"non_field_errors": details}
        message = "The submitted data was invalid."
        response.data = _envelope(code, message, details)
        return response

    message = _readable_detail(getattr(exc, "detail", None))
    response.data = _envelope(code, message)
    return response
