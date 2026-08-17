from __future__ import annotations

import asyncio
import hashlib
import time
from collections import deque
from dataclasses import dataclass, field

from config import settings


@dataclass
class _Bucket:
    attempts: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class LoginRateLimiter:
    """Small single-process limiter for the single-replica production profile.

    It limits both source IP and username hashes. If the API is scaled to multiple
    replicas, replace this with a shared Redis/proxy limiter.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _username_key(username: str) -> str:
        digest = hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()
        return f"user:{digest}"

    async def check(self, *, ip: str, username: str) -> int | None:
        now = time.monotonic()
        keys = (f"ip:{ip}", self._username_key(username))

        async with self._lock:
            retry_after = 0
            for key in keys:
                bucket = self._buckets.get(key)
                if bucket and bucket.blocked_until > now:
                    retry_after = max(retry_after, int(bucket.blocked_until - now) + 1)
            return retry_after or None

    async def record_failure(self, *, ip: str, username: str) -> None:
        now = time.monotonic()
        window_start = now - settings.admin_login_rate_limit_window_seconds
        keys = (f"ip:{ip}", self._username_key(username))

        async with self._lock:
            for key in keys:
                bucket = self._buckets.setdefault(key, _Bucket())
                while bucket.attempts and bucket.attempts[0] < window_start:
                    bucket.attempts.popleft()
                bucket.attempts.append(now)
                if len(bucket.attempts) >= settings.admin_login_rate_limit_attempts:
                    bucket.blocked_until = now + settings.admin_login_block_seconds
                    bucket.attempts.clear()

            # Opportunistic cleanup to keep long-running process memory bounded.
            if len(self._buckets) > 10_000:
                stale_before = now - max(
                    settings.admin_login_rate_limit_window_seconds,
                    settings.admin_login_block_seconds,
                ) * 2
                self._buckets = {
                    key: bucket
                    for key, bucket in self._buckets.items()
                    if bucket.blocked_until > now
                    or (bucket.attempts and bucket.attempts[-1] > stale_before)
                }

    async def record_success(self, *, ip: str, username: str) -> None:
        keys = (f"ip:{ip}", self._username_key(username))
        async with self._lock:
            for key in keys:
                self._buckets.pop(key, None)


login_rate_limiter = LoginRateLimiter()
