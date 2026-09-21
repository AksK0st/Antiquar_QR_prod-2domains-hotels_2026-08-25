from __future__ import annotations

from fastapi import HTTPException, Request, status

from config import settings


def request_hostname(request: Request) -> str:
    # За прокси сначала доверяем исходному host.
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    )

    # На случай "host1, host2"
    host = host.split(",", 1)[0].strip().lower()

    # Убираем :5173 / :8000
    if ":" in host:
        host = host.rsplit(":", 1)[0]

    return host


def hotel_name_for_request(request: Request) -> str:
    host = request_hostname(request)

    try:
        return settings.hotel_name_for_host(host)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown hotel domain",
        ) from exc