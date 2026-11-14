"""网络工具：SSRF 防护。"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import ValidationFailedError

_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return any(addr in net for net in _BLOCKED_NETWORKS)


def validate_public_url(url: str) -> str:
    """校验 URL 安全性，返回规范化 URL；不合法则抛错。"""
    if not url or not isinstance(url, str):
        raise ValidationFailedError("URL 不能为空")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValidationFailedError("仅支持 http/https 协议")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationFailedError("URL 缺少主机名")
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise ValidationFailedError("不允许访问内网/本地地址")
    if settings.SSRF_ALLOW_PRIVATE:
        return url

    # 直接是 IP 的情况
    try:
        if _is_private_ip(host):
            raise ValidationFailedError("不允许访问内网/保留地址")
    except ValidationFailedError:
        raise
    except Exception:
        pass

    # 域名解析后校验，防止 DNS 指向内网
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for info in infos:
            ip = info[4][0]
            if _is_private_ip(ip):
                raise ValidationFailedError("目标地址解析到内网/保留地址，已阻止")
    except socket.gaierror:
        raise ValidationFailedError(f"域名无法解析: {host}") from None
    return url
