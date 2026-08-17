from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete

from db import SessionLocal
from models.admin_session import AdminSession


async def main() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            delete(AdminSession).where(AdminSession.expires_at <= datetime.now(timezone.utc))
        )
        await db.commit()
        print(f"Deleted expired sessions: {result.rowcount or 0}")


if __name__ == "__main__":
    asyncio.run(main())
