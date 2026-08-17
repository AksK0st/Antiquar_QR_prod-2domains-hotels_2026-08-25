from __future__ import annotations

from sqlalchemy.exc import IntegrityError


def _walk_exception(exc: BaseException):
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = getattr(current, "__cause__", None) or getattr(current, "orig", None)


def integrity_sqlstate(exc: IntegrityError) -> str | None:
    for current in _walk_exception(exc):
        value = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
        if value:
            return str(value)
    return None


def integrity_constraint(exc: IntegrityError) -> str | None:
    for current in _walk_exception(exc):
        value = getattr(current, "constraint_name", None)
        if value:
            return str(value)
        diag = getattr(current, "diag", None)
        value = getattr(diag, "constraint_name", None) if diag else None
        if value:
            return str(value)
    return None
