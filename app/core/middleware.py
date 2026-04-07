"""Request ID injection and error handling middleware."""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger_with_context


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request_id into context."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Bind logger to request
        logger = get_logger_with_context(request_id=request_id)
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(process_time * 1000, 2)
            )
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(exc),
                duration_ms=round(process_time * 1000, 2),
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Centralized exception handling."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger = get_logger_with_context(request_id=request_id)
            logger.error("unhandled_exception", error=str(exc), exc_info=True)
            
            # Don't leak stack traces in production
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "detail": "An unexpected error occurred"
                }
            )