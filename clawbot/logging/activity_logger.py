"""Structured JSON Lines activity logger for all pipeline events."""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

from clawbot.logging.log_schema import ActivityEvent

logger = logging.getLogger(__name__)


class ActivityLogger:
    """Writes structured events to a JSON Lines file."""

    def __init__(self, log_file: str, csv_file: str):
        self.log_file = Path(log_file)
        self.csv_file = Path(csv_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: str,
        run_id: str,
        profile_url: str = "",
        profile_name: str = "",
        **details: Any,
    ) -> None:
        event = ActivityEvent(
            event_type=event_type,
            run_id=run_id,
            profile_url=profile_url,
            profile_name=profile_name,
            details=details,
        )
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
        logger.info("[%s] %s — %s", event_type, profile_name or "—", details)

    def export_csv(self) -> None:
        """Flatten the JSONL log into a CSV for spreadsheet review."""
        if not self.log_file.exists():
            return

        rows = []
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                flat = {
                    "timestamp": event.get("timestamp"),
                    "run_id": event.get("run_id"),
                    "event_type": event.get("event_type"),
                    "profile_url": event.get("profile_url"),
                    "profile_name": event.get("profile_name"),
                }
                flat.update(event.get("details", {}))
                rows.append(flat)

        if not rows:
            return

        # Collect all column names preserving insertion order
        all_keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for k in row:
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        self.csv_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported %d log entries to %s", len(rows), self.csv_file)
