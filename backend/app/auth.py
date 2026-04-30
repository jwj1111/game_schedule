"""
轻量管理员认证：内部密码登录 + HMAC 签名 token。

当前阶段不引入账号体系；后续接微信时，只需要替换登录校验逻辑，
业务写接口仍复用 require_admin。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import ADMIN_PASSWORD, AUTH_SECRET_KEY, AUTH_TOKEN_EXPIRE_SECONDS

_bearer = HTTPBearer(auto_error=False)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(payload: str) -> str:
    digest = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def is_admin_password_configured() -> bool:
    return bool(ADMIN_PASSWORD)


def verify_admin_password(password: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(str(password), ADMIN_PASSWORD)


def create_access_token() -> str:
    now = int(time.time())
    payload = {
        "sub": "admin",
        "is_admin": True,
        "auth_type": "password",
        "iat": now,
        "exp": now + AUTH_TOKEN_EXPIRE_SECONDS,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{encoded_payload}.{_sign(encoded_payload)}"


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = _sign(encoded_payload)
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None

    if expires_at < int(time.time()):
        return None
    if payload.get("sub") != "admin" or payload.get("is_admin") is not True:
        return None
    return payload


def get_current_auth(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return {"is_admin": False, "auth_type": None}

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return {"is_admin": False, "auth_type": None}

    return {
        "is_admin": True,
        "auth_type": payload.get("auth_type", "password"),
        "expires_at": payload.get("exp"),
    }


def require_admin(auth: dict[str, Any] = Depends(get_current_auth)) -> dict[str, Any]:
    if not auth.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要管理员权限",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth
