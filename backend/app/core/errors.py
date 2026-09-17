"""Application error hierarchy and structured exception handlers.

All API errors are returned in a single envelope:

    {"error": {"code": ..., "message": ..., "details": [...]}}
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_DEFAULT_DETAILS: list = []


def _error_payload(code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or _DEFAULT_DETAILS}}


class AppError(Exception):
    """Base class for all application-level errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: list | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class GeoValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "GEOJSON_VALIDATION_ERROR"


class ResponsibilityUnresolvedError(AppError):
    """Raised by routing when no deterministic responsibility can be established."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "RESPONSIBILITY_UNRESOLVED"


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("Handled %s on %s: %s", exc.code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.code, exc.message, exc.details),
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": ".".join(str(p) for p in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload("VALIDATION_ERROR", "Request validation failed", details),
    )


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    }.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=_error_payload(code, message))


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach structured handlers to a FastAPI application."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)