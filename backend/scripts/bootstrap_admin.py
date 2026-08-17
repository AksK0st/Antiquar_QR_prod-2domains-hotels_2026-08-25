from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from config import settings
from db import SessionLocal
from models.admin_session import AdminSession
from models.admin_user import AdminUser
from security.sessions import hash_session_token
from security.passwords import hash_password


async def main() -> None:
    if settings.is_production:
        raise RuntimeError("bootstrap_admin.py is disabled in production; use create_admin.py interactively")

    username = os.environ.get("ADMIN_BOOTSTRAP_USERNAME", "").strip()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not username or len(password) < 14:
        raise RuntimeError("ADMIN_BOOTSTRAP_USERNAME and a 14+ character ADMIN_BOOTSTRAP_PASSWORD are required")

    async with SessionLocal() as db:
        existing = (
            await db.execute(select(AdminUser).where(AdminUser.username == username))
        ).scalar_one_or_none()
        if existing is None:
            db.add(AdminUser(username=username, password_hash=hash_password(password)))
            await db.commit()
            print(f"Created test admin: {username}")
        else:
            print(f"Test admin already exists: {username}")

        expired_token = os.environ.get("ADMIN_BOOTSTRAP_EXPIRED_TOKEN")
        if expired_token:
            admin = existing or (
                await db.execute(select(AdminUser).where(AdminUser.username == username))
            ).scalar_one()
            token_hash = hash_session_token(expired_token)
            session = (
                await db.execute(select(AdminSession).where(AdminSession.token_hash == token_hash))
            ).scalar_one_or_none()
            if session is None:
                db.add(
                    AdminSession(
                        admin_id=admin.id,
                        token_hash=token_hash,
                        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                    )
                )
                await db.commit()
                print("Created expired test session")


if __name__ == "__main__":
    asyncio.run(main())
