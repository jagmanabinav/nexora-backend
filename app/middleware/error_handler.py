"""FastAPI middleware for request context and error handling."""

import logging
import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.constants import REQUEST_ID_HEADER
from app.core.exceptions import NexoraException
from app.core.logging import get_logger
from app.core.security import generate_request_id

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Generate or get request ID
        request_id = request.headers.get(REQUEST_ID_HEADER.lower()) or generate_request_id()

        # Store in request state for later access
        request.state.request_id = request_id

        # Add to response headers
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        except NexoraException as exc:
            process_time = time.time() - start_time
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "fields": exc.fields,
                    },
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                headers={
                    "X-Process-Time": str(process_time),
                    REQUEST_ID_HEADER: getattr(request.state, "request_id", "unknown"),
                },
            )
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"Unhandled exception: {str(exc)}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred",
                        "fields": [],
                    },
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                headers={
                    "X-Process-Time": str(process_time),
                    REQUEST_ID_HEADER: getattr(request.state, "request_id", "unknown"),
                },
            )
