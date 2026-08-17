import asyncio

from config import settings
from security.rate_limit import LoginRateLimiter


def test_login_limiter_blocks_and_resets() -> None:
    old = (
        settings.admin_login_rate_limit_attempts,
        settings.admin_login_rate_limit_window_seconds,
        settings.admin_login_block_seconds,
    )
    settings.admin_login_rate_limit_attempts = 3
    settings.admin_login_rate_limit_window_seconds = 60
    settings.admin_login_block_seconds = 300

    async def scenario() -> None:
        limiter = LoginRateLimiter()
        assert await limiter.check(ip="203.0.113.1", username="admin") is None
        for _ in range(3):
            await limiter.record_failure(ip="203.0.113.1", username="admin")
        assert (await limiter.check(ip="203.0.113.1", username="admin")) is not None
        await limiter.record_success(ip="203.0.113.1", username="admin")
        assert await limiter.check(ip="203.0.113.1", username="admin") is None

    try:
        asyncio.run(scenario())
    finally:
        (
            settings.admin_login_rate_limit_attempts,
            settings.admin_login_rate_limit_window_seconds,
            settings.admin_login_block_seconds,
        ) = old
