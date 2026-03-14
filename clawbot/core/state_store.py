"""SQLite-backed pipeline state machine.

Every LinkedIn profile moves through the following states:
  DISCOVERED -> FILTERED_IN -> CONNECTION_SENT -> CONNECTION_ACCEPTED -> MESSAGE_SENT
             -> FILTERED_OUT  (terminal — did not pass filters)
             -> CONNECTION_FAILED  (retryable)
             -> MESSAGE_FAILED     (retryable)
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawbot.utils.exceptions import StateStoreError

logger = logging.getLogger(__name__)

VALID_STATES = {
    "DISCOVERED",
    "FILTERED_IN",
    "FILTERED_OUT",
    "CONNECTION_SENT",
    "CONNECTION_FAILED",
    "CONNECTION_ACCEPTED",
    "MESSAGE_SENT",
    "MESSAGE_FAILED",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    profile_url         TEXT PRIMARY KEY,
    full_name           TEXT,
    state               TEXT NOT NULL,
    state_updated_at    TEXT NOT NULL,
    raw_data_json       TEXT,
    connection_sent_at  TEXT,
    message_sent_at     TEXT,
    message_text        TEXT,
    error_log           TEXT
);
"""

CREATE_RATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rate_buckets (
    bucket_name     TEXT PRIMARY KEY,
    tokens          INTEGER NOT NULL,
    last_refill_at  TEXT NOT NULL
);
"""


class StateStore:
    """Thread-safe SQLite state store for pipeline profiles."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.execute(CREATE_RATE_TABLE_SQL)

    def upsert(
        self,
        profile_url: str,
        state: str,
        full_name: str = "",
        raw_data: dict | None = None,
        message_text: str = "",
        error: str = "",
    ) -> None:
        if state not in VALID_STATES:
            raise StateStoreError(f"Invalid state: {state}")

        now = datetime.now(timezone.utc).isoformat()
        raw_json = json.dumps(raw_data) if raw_data else None

        with self._conn() as conn:
            existing = conn.execute(
                "SELECT profile_url FROM profiles WHERE profile_url = ?",
                (profile_url,),
            ).fetchone()

            if existing:
                updates: dict[str, Any] = {"state": state, "state_updated_at": now}
                if full_name:
                    updates["full_name"] = full_name
                if raw_json:
                    updates["raw_data_json"] = raw_json
                if message_text:
                    updates["message_text"] = message_text
                    updates["message_sent_at"] = now
                if error:
                    updates["error_log"] = error
                if state == "CONNECTION_SENT":
                    updates["connection_sent_at"] = now

                set_clause = ", ".join(f"{k} = ?" for k in updates)
                conn.execute(
                    f"UPDATE profiles SET {set_clause} WHERE profile_url = ?",
                    (*updates.values(), profile_url),
                )
            else:
                conn.execute(
                    """INSERT INTO profiles
                       (profile_url, full_name, state, state_updated_at,
                        raw_data_json, error_log)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (profile_url, full_name, state, now, raw_json, error or None),
                )

    def get_profiles_in_state(self, state: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE state = ?", (state,)
            ).fetchall()
        return [dict(row) for row in rows]

    def already_seen(self, profile_url: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state FROM profiles WHERE profile_url = ?", (profile_url,)
            ).fetchone()
        return row is not None

    def get_profile(self, profile_url: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM profiles WHERE profile_url = ?", (profile_url,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        if result.get("raw_data_json"):
            result["raw_data"] = json.loads(result["raw_data_json"])
        return result

    def count_by_state(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT state, COUNT(*) as cnt FROM profiles GROUP BY state"
            ).fetchall()
        return {row["state"]: row["cnt"] for row in rows}

    # --- Rate bucket helpers (used by rate_limiter.py) ---

    def get_bucket(self, name: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM rate_buckets WHERE bucket_name = ?", (name,)
            ).fetchone()
        return dict(row) if row else None

    def set_bucket(self, name: str, tokens: int, last_refill_at: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO rate_buckets (bucket_name, tokens, last_refill_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(bucket_name) DO UPDATE SET
                     tokens = excluded.tokens,
                     last_refill_at = excluded.last_refill_at""",
                (name, tokens, last_refill_at),
            )
