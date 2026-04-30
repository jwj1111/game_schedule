"""管理员认证接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from backend.app.auth import create_access_token, get_current_auth, is_admin_password_configured, verify_admin_password
from backend.app.config import AUTH_TOKEN_EXPIRE_SECONDS
from backend.app.schemas import AuthLoginRequest, AuthLoginResponse, AuthStatusResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthLoginResponse)
def login(body: AuthLoginRequest):
    """使用内部管理员密码登录。"""
    if not is_admin_password_configured():
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="管理员密码未配置")
    if not verify_admin_password(body.password):
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="管理员密码错误")

    return AuthLoginResponse(
        token=create_access_token(),
        is_admin=True,
        auth_type="password",
        expires_in=AUTH_TOKEN_EXPIRE_SECONDS,
    )


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(auth=Depends(get_current_auth)):
    """查询当前请求的管理员登录状态。"""
    return AuthStatusResponse(
        is_admin=bool(auth.get("is_admin")),
        auth_type=auth.get("auth_type"),
        expires_at=auth.get("expires_at"),
    )


@router.post("/logout")
def logout():
    """JWT 模式下由前端清除 token；保留接口便于后续接 session/微信。"""
    return {"ok": True}
