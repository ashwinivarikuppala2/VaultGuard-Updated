import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    DuplicateEntityException,
    EntityNotFoundException,
    FileSizeLimitException,
    InactiveOrganizationException,
    InactiveUserException,
    TokenValidationException,
    VaultGuardException,
)
from app.core.responses import error_response

logger = logging.getLogger("vaultguard.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundException)
    async def not_found_handler(request: Request, exc: EntityNotFoundException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=envelope.model_dump(mode="json"))

    @app.exception_handler(DuplicateEntityException)
    async def duplicate_handler(request: Request, exc: DuplicateEntityException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=envelope.model_dump(mode="json"))

    @app.exception_handler(AuthenticationException)
    async def auth_failed_handler(request: Request, exc: AuthenticationException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(mode="json"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(TokenValidationException)
    async def token_invalid_handler(request: Request, exc: TokenValidationException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(mode="json"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationException)
    async def forbidden_handler(request: Request, exc: AuthorizationException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=envelope.model_dump(mode="json"))

    @app.exception_handler(InactiveUserException)
    @app.exception_handler(InactiveOrganizationException)
    async def inactive_account_handler(request: Request, exc: VaultGuardException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=envelope.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        errors = exc.errors()
        envelope = error_response(
            code="VALIDATION_ERROR",
            message="Request input validation failed.",
            details=errors,
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(mode="json"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(
            code="HTTP_ERROR",
            message=str(exc.detail),
            details=None,
            trace_id=trace_id,
        )
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))

    @app.exception_handler(FileSizeLimitException)
    async def file_too_large_handler(request: Request, exc: FileSizeLimitException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(code=exc.code, message=exc.message, details=exc.details, trace_id=trace_id)
        return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content=envelope.model_dump(mode="json"))

    @app.exception_handler(VaultGuardException)
    async def domain_exception_handler(request: Request, exc: VaultGuardException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        envelope = error_response(
            code=exc.code or "BAD_REQUEST",
            message=exc.message,
            details=exc.details,
            trace_id=trace_id,
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=envelope.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def global_unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        logger.critical(f"[{trace_id}] Unhandled crash: {str(exc)}", exc_info=True)
        envelope = error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=envelope.model_dump(mode="json"),
        )

