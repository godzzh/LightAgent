"""统一业务异常与全局异常处理。"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """业务异常基类，code 对应统一响应体中的 code。"""

    http_status: int = status.HTTP_400_BAD_REQUEST
    code: int = 40000

    def __init__(self, message: str, *, code: Optional[int] = None, data: Any = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.data = data


class NotFoundError(AppError):
    http_status = status.HTTP_404_NOT_FOUND
    code = 40400


class UnauthorizedError(AppError):
    http_status = status.HTTP_401_UNAUTHORIZED
    code = 40100


class ForbiddenError(AppError):
    http_status = status.HTTP_403_FORBIDDEN
    code = 40300


class ConflictError(AppError):
    http_status = status.HTTP_409_CONFLICT
    code = 40900


class ValidationFailedError(AppError):
    http_status = status.HTTP_400_BAD_REQUEST
    code = 40001


def _body(code: int, message: str, data: Any, request_id: str) -> dict:
    return {"code": code, "message": message, "data": data, "request_id": request_id}


def register_exception_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        rid = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=exc.http_status,
            content=_body(exc.code, exc.message, exc.data, rid),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        rid = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.status_code * 100, str(exc.detail), None, rid),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        rid = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=422,
            content=_body(40001, "参数校验失败", exc.errors(), rid),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "")
        logger.exception(f"unhandled error rid={rid}: {exc}")
        return JSONResponse(
            status_code=500,
            content=_body(50000, "服务内部错误", None, rid),
        )
