from __future__ import annotations

from fastapi import HTTPException, Request, status

from config import settings


def request_hostname(request: Request) -> str:
    host = request.headers.get("host") or request.headers.get("x-forwarded-host") or ""
    return host.split(",", 1)[0].strip()


def hotel_name_for_request(request: Request) -> str:
    host = request_hostname(request)
    try:
        return settings.hotel_name_for_host(host)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown hotel domain",
        ) from exc
