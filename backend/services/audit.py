from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.admin_audit_log import AdminAuditLog
from models.admin_user import AdminUser


async def add_audit_log(
    db: AsyncSession,
    *,
    request: Request,
    action: str,
    admin: AdminUser | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_id=admin.id if admin else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            request_id=getattr(request.state, "request_id", None),
            client_ip=getattr(request.state, "client_ip", None),
            details=details,
        )
    )
