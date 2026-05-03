from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger


logger = get_logger(__name__)


class AppException(Exception):
    """项目统一业务异常。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APP_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


def build_error_response(
    *,
    message: str,
    error_code: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    """构造统一错误响应。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_code": error_code,
            "message": message,
            "details": details,
        },
    )


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """处理项目内主动抛出的业务异常。"""
    return build_error_response(
        message=exc.message,
        error_code=exc.error_code,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 FastAPI/Starlette HTTP 异常。"""
    return build_error_response(
        message=str(exc.detail),
        error_code="HTTP_ERROR",
        status_code=exc.status_code,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数校验异常。"""
    return build_error_response(
        message="请求参数校验失败。",
        error_code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底处理未捕获异常，避免向前端暴露内部堆栈。"""
    logger.exception("未处理异常：%s %s", request.method, request.url.path, exc_info=exc)
    return build_error_response(
        message="服务内部异常，请稍后重试。",
        error_code="INTERNAL_SERVER_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """向 FastAPI 应用注册统一异常处理器。"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
