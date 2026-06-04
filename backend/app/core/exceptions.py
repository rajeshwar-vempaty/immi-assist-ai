"""Application exceptions and handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RateLimitExceeded(AppError):
    def __init__(self, message: str = "Daily request limit exceeded."):
        super().__init__(message, status_code=429)


class LLMResponseError(AppError):
    def __init__(self, message: str = "Failed to parse structured response from LLM."):
        super().__init__(message, status_code=502)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "status": exc.status_code,
                "request_id": request_id,
            },
        )

