from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_db
from models.admin_session import AdminSession
from models.admin_user import AdminUser
from schemas.admin_auth import AdminLoginRequest, AdminLoginResponse
from security.dependencies import get_current_admin
from security.passwords import verify_password_or_dummy
from security.rate_limit import login_rate_limiter
from security.sessions import generate_session_token, hash_session_token
from services.audit import add_audit_log


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["admin-auth"])


@router.get("/me")
async def me(admin: AdminUser = Depends(get_current_admin)):
    return {"id": admin.id, "username": admin.username}


@router.post("/login", response_model=AdminLoginResponse)
async def login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    client_ip = getattr(request.state, "client_ip", "unknown")
    retry_after = await login_rate_limiter.check(ip=client_ip, username=payload.username)
    if retry_after is not None:
        logger.warning(
            "Admin login rate limited",
            extra={
                "event": "admin_login_rate_limited",
                "client_ip": client_ip,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    result = await db.execute(select(AdminUser).where(AdminUser.username == payload.username))
    admin = result.scalar_one_or_none()
    password_hash = admin.password_hash if admin is not None else None
    password_valid = verify_password_or_dummy(
        payload.password.get_secret_value(),
        password_hash,
    )

    if admin is None or not admin.is_active or not password_valid:
        await login_rate_limiter.record_failure(ip=client_ip, username=payload.username)
        logger.warning(
            "Admin login failed",
            extra={
                "event": "admin_login_failed",
                "client_ip": client_ip,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    await login_rate_limiter.record_success(ip=client_ip, username=payload.username)
    now = datetime.now(timezone.utc)
    await db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))

    raw_token = generate_session_token()
    session = AdminSession(
        admin_id=admin.id,
        token_hash=hash_session_token(raw_token),
        expires_at=now + timedelta(hours=settings.admin_session_ttl_hours),
    )
    db.add(session)
    await add_audit_log(
        db,
        request=request,
        action="auth.login",
        admin=admin,
        entity_type="admin_user",
        entity_id=admin.id,
    )
    await db.commit()

    ttl_seconds = settings.admin_session_ttl_hours * 60 * 60
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path="/",
        max_age=ttl_seconds,
    )

    logger.info(
        "Admin login succeeded",
        extra={
            "event": "admin_login_success",
            "admin_username": admin.username,
            "client_ip": client_ip,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return AdminLoginResponse(authenticated=True, username=admin.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    raw_token = request.cookies.get(settings.admin_session_cookie_name)
    if raw_token:
        await db.execute(
            delete(AdminSession).where(
                AdminSession.token_hash == hash_session_token(raw_token)
            )
        )

    await add_audit_log(
        db,
        request=request,
        action="auth.logout",
        admin=admin,
        entity_type="admin_user",
        entity_id=admin.id,
    )
    await db.commit()

    response.delete_cookie(
        key=settings.admin_session_cookie_name,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="strict",
    )
    logger.info(
        "Admin logout",
        extra={
            "event": "admin_logout",
            "admin_username": admin.username,
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
