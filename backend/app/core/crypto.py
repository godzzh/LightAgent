"""API Key 等敏感字段的对称加密。密钥由 SECRET_KEY 派生。"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except (InvalidToken, ValueError):
        return ""


def mask_secret(plain_or_cipher: str, keep: int = 4) -> str:
    """返回脱敏展示用字符串，例如 sk-1***a2b3"""
    if not plain_or_cipher:
        return ""
    plain = decrypt_secret(plain_or_cipher) or plain_or_cipher
    if len(plain) <= keep * 2:
        return "******"
    return f"{plain[:keep]}******{plain[-keep:]}"
