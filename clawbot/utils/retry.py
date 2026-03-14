"""Exponential backoff retry decorator."""

import functools
import logging
import time

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, base_delay: float = 2.0, exceptions=(Exception,)):
    """Retry a function with exponential backoff on specified exceptions.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        base_delay: Initial delay in seconds; doubles each retry.
        exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts, func.__name__, exc,
                        )
                        raise
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                        attempt, max_attempts, func.__name__, exc, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
        return wrapper
    return decorator
