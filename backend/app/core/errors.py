from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, code="not_found")


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409, code="conflict")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401, code="unauthorized")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403, code="forbidden")


class BusinessRuleError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400, code="business_rule")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )
