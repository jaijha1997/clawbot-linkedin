"""Unit tests for RateLimiter and TokenBucket."""

import pytest
from datetime import datetime, timezone, timedelta
from clawbot.scheduler.rate_limiter import TokenBucket, RateLimiter


def test_token_bucket_consumes_tokens(state_store):
    bucket = TokenBucket("test_hourly", capacity=5, refill_period_seconds=3600, store=state_store)
    assert bucket.consume() is True
    assert bucket.remaining() == 4


def test_token_bucket_exhausts(state_store):
    bucket = TokenBucket("test_daily", capacity=2, refill_period_seconds=86400, store=state_store)
    assert bucket.consume() is True
    assert bucket.consume() is True
    assert bucket.consume() is False  # Exhausted


def test_token_bucket_refills_after_period(state_store):
    bucket = TokenBucket("test_refill", capacity=3, refill_period_seconds=1, store=state_store)
    bucket.consume()
    bucket.consume()
    bucket.consume()
    assert bucket.remaining() == 0

    import time
    time.sleep(1.1)  # Wait for refill period
    assert bucket.remaining() == 3


def test_rate_limiter_consumes_both_buckets(mock_config, state_store):
    limiter = RateLimiter(mock_config, state_store)
    initial_hourly = limiter.hourly.remaining()
    initial_daily = limiter.daily.remaining()

    result = limiter.consume_connection()
    assert result is True
    assert limiter.hourly.remaining() == initial_hourly - 1
    assert limiter.daily.remaining() == initial_daily - 1


def test_rate_limiter_status(mock_config, state_store):
    limiter = RateLimiter(mock_config, state_store)
    status = limiter.status()
    assert "hourly_remaining" in status
    assert "daily_remaining" in status
