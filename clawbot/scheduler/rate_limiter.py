"""Token bucket rate limiter with SQLite-persisted state.

Bucket state is stored in the database so limits are correctly
enforced across process restarts.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawbot.core.state_store import StateStore

logger = logging.getLogger(__name__)


class TokenBucket:
    """A persistent token bucket for rate limiting.

    Args:
        name: Unique bucket identifier (used as the DB key).
        capacity: Maximum tokens in the bucket.
        refill_period_seconds: How often the bucket fully refills.
        store: The StateStore instance for persistence.
    """

    def __init__(
        self,
        name: str,
        capacity: int,
        refill_period_seconds: int,
        store: "StateStore",
    ):
        self.name = name
        self.capacity = capacity
        self.refill_period = timedelta(seconds=refill_period_seconds)
        self._store = store
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        row = self._store.get_bucket(self.name)
        if row is None:
            now = datetime.now(timezone.utc).isoformat()
            self._store.set_bucket(self.name, self.capacity, now)

    def _maybe_refill(self) -> int:
        """Check if the refill period has elapsed; if so, reset tokens."""
        row = self._store.get_bucket(self.name)
        last_refill = datetime.fromisoformat(row["last_refill_at"])
        now = datetime.now(timezone.utc)
        if now - last_refill >= self.refill_period:
            self._store.set_bucket(self.name, self.capacity, now.isoformat())
            logger.info("Bucket '%s' refilled to %d tokens.", self.name, self.capacity)
            return self.capacity
        return row["tokens"]

    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from the bucket.

        Returns:
            True if tokens were available and consumed, False if exhausted.
        """
        available = self._maybe_refill()
        if available < tokens:
            logger.warning(
                "Bucket '%s' exhausted (%d/%d available).",
                self.name, available, self.capacity,
            )
            return False
        new_tokens = available - tokens
        row = self._store.get_bucket(self.name)
        self._store.set_bucket(self.name, new_tokens, row["last_refill_at"])
        logger.debug("Bucket '%s': %d tokens remaining.", self.name, new_tokens)
        return True

    def remaining(self) -> int:
        return self._maybe_refill()


class RateLimiter:
    """Manages hourly and daily connection request buckets."""

    def __init__(self, config, store: "StateStore"):
        self.hourly = TokenBucket(
            name="connections_hourly",
            capacity=config.connections_per_hour,
            refill_period_seconds=3600,
            store=store,
        )
        self.daily = TokenBucket(
            name="connections_daily",
            capacity=config.connections_per_day,
            refill_period_seconds=86400,
            store=store,
        )

    def can_connect(self) -> bool:
        """Check both buckets without consuming — for dry-run checks."""
        return self.hourly.remaining() > 0 and self.daily.remaining() > 0

    def consume_connection(self) -> bool:
        """Consume one connection slot from both hourly and daily buckets."""
        if not self.can_connect():
            return False
        self.hourly.consume()
        self.daily.consume()
        return True

    def status(self) -> dict[str, int]:
        return {
            "hourly_remaining": self.hourly.remaining(),
            "daily_remaining": self.daily.remaining(),
        }
