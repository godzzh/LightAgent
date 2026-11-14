"""日志初始化（loguru）。敏感字段统一在此脱敏。"""
from __future__ import annotations

import sys

from loguru import logger

from app.core.config import settings

_SENSITIVE_KEYS = ("api_key", "authorization", "password", "token", "secret")


def _redact(record):
    msg = record["message"]
    for k in _SENSITIVE_KEYS:
        if k in msg.lower():
            record["message"] = msg[:200] + " ...[redacted]"
            break


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=not settings.DEBUG,
    )
    logger.add("logs/app.log", rotation="20 MB", retention="14 days", encoding="utf-8", level="INFO")
    logger.configure(patcher=_redact)
