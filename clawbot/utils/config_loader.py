"""Load and validate config.yaml and .env into a single config object."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from clawbot.utils.exceptions import ConfigError

# Load .env from project root
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def _get_env(key: str, required: bool = True) -> str:
    value = os.environ.get(key)
    if required and not value:
        raise ConfigError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in your values."
        )
    return value or ""


class Config:
    """Flat accessor for all Clawbot configuration."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

        # LinkedIn credentials (from .env only)
        self.linkedin_email: str = _get_env("LINKEDIN_EMAIL")
        self.linkedin_password: str = _get_env("LINKEDIN_PASSWORD")

        # OpenAI (from .env only)
        self.openai_api_key: str = _get_env("OPENAI_API_KEY")

        # Targeting
        t = data["targeting"]
        self.target_roles: list[str] = t["roles"]
        self.target_industries: list[str] = t["industries"]
        self.target_seniority: list[str] = t["seniority"]
        self.target_locations: list[str] = t["locations"]
        self.max_profiles_per_run: int = int(
            os.environ.get("CLAWBOT_MAX_PROFILES", t["max_profiles_per_run"])
        )
        self.connection_degree: int = t.get("connection_degree", 2)

        # Rate limits
        r = data["rate_limits"]
        self.connections_per_day: int = r["connection_requests_per_day"]
        self.connections_per_hour: int = r["connection_requests_per_hour"]
        self.message_delay_min: float = r["message_delay_min_seconds"]
        self.message_delay_max: float = r["message_delay_max_seconds"]
        self.page_delay_min: float = r["page_load_delay_min_seconds"]
        self.page_delay_max: float = r["page_load_delay_max_seconds"]
        self.between_profiles_min: float = r["between_profiles_min_seconds"]
        self.between_profiles_max: float = r["between_profiles_max_seconds"]

        # Schedule
        s = data["schedule"]
        self.scrape_interval_hours: int = s["scrape_interval_hours"]
        self.poll_interval_hours: int = s["acceptance_poll_interval_hours"]
        self.timezone: str = s["timezone"]
        self.run_at_hour: int = s.get("run_at_hour", 9)

        # AI
        a = data["ai"]
        self.ai_model: str = a["model"]
        self.ai_max_tokens: int = a["max_tokens"]
        self.ai_temperature: float = a["temperature"]
        self.ai_persona: str = a["persona"]
        self.product_name: str = a["product_name"]
        self.product_context: str = a["product_context"].strip()
        self.message_max_chars: int = a["message_max_chars"]

        # Browser
        b = data["browser"]
        self.headless: bool = os.environ.get("CLAWBOT_HEADLESS", str(b["headless"])).lower() == "true"
        self.window_width: int = b["window_width"]
        self.window_height: int = b["window_height"]
        self.user_data_dir: str = str(_ROOT / b["user_data_dir"])
        self.implicit_wait: int = b["implicit_wait_seconds"]
        self.page_load_timeout: int = b["page_load_timeout_seconds"]

        # Logging
        lg = data["logging"]
        self.log_level: str = lg["log_level"]
        self.log_file: str = str(_ROOT / lg["log_file"])
        self.export_csv: bool = lg["export_csv_on_run"]
        self.csv_file: str = str(_ROOT / lg["csv_file"])

        # Derived paths
        self.state_db_path: str = str(_ROOT / "data" / "state.db")
        self.cookies_path: str = str(_ROOT / "data" / "cookies" / "linkedin_session.pkl")


def load_config(config_path: str | None = None) -> Config:
    """Load config from YAML file and environment variables."""
    if config_path is None:
        config_path = str(_ROOT / "config" / "config.yaml")

    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return Config(data)
