"""Dataclass definitions for structured activity log events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


EVENT_TYPES = {
    "PROFILE_SCRAPED",
    "FILTER_PASS",
    "FILTER_FAIL",
    "CONNECTION_SENT",
    "CONNECTION_FAILED",
    "CONNECTION_ACCEPTED",
    "MESSAGE_SENT",
    "MESSAGE_FAILED",
    "RATE_LIMITED",
    "POLL_COMPLETE",
    "RUN_STARTED",
    "RUN_COMPLETE",
    "ERROR",
}


@dataclass
class ActivityEvent:
    event_type: str
    run_id: str
    profile_url: str = ""
    profile_name: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "profile_url": self.profile_url,
            "profile_name": self.profile_name,
            "details": self.details,
        }
