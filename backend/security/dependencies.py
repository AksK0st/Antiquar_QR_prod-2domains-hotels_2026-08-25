from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_db
from models.admin_session import AdminSession
from models.admin_user import AdminUser
from security.sessions import hash_session_token


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    raw_token = request.cookies.get(
        settings.admin_session_cookie_name
    )

    if not raw_token:
        raise unauthorized()

    token_hash = hash_session_token(raw_token)

    result = await db.execute(
        select(AdminSession, AdminUser)
        .join(
            AdminUser,
            AdminUser.id == AdminSession.admin_id,
        )
        .where(
            AdminSession.token_hash == token_hash
        )
    )

    row = result.one_or_none()

    if row is None:
        raise unauthorized()

    session, admin = row

    now = datetime.now(timezone.utc)

    if session.expires_at <= now:
        await db.delete(session)
        await db.commit()

        raise unauthorized()

    if not admin.is_active:
        raise unauthorized()

    return admin