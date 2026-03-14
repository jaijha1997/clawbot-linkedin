"""Central pipeline orchestrator — zero-touch filter → connect → message."""

import json
import logging
import random
import time
from uuid import uuid4

from clawbot.ai.gpt_client import GPTClient
from clawbot.browser.driver import create_driver
from clawbot.browser.session import LinkedInSession
from clawbot.core.state_store import StateStore
from clawbot.logging.activity_logger import ActivityLogger
from clawbot.outreach.acceptance_poller import AcceptancePoller
from clawbot.outreach.connector import Connector
from clawbot.outreach.messenger import Messenger
from clawbot.scheduler.rate_limiter import RateLimiter
from clawbot.scraper.filter_engine import FilterEngine
from clawbot.scraper.profile_parser import ProfileParser
from clawbot.scraper.search import ProfileSearcher
from clawbot.utils.exceptions import (
    ClawbotError,
    ConnectionRequestError,
    MessageError,
    ProfileNotFoundError,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """Drives the full Clawbot pipeline end-to-end."""

    def __init__(self, config):
        self.config = config
        self.store = StateStore(config.state_db_path)
        self.activity_log = ActivityLogger(config.log_file, config.csv_file)
        self.rate_limiter = RateLimiter(config, self.store)
        self.gpt = GPTClient(config)
        self._driver = None

    def run_pipeline(self) -> dict:
        """Execute one full pipeline run.

        Stages:
          1. Scrape and filter profiles
          2. Send connection requests to filtered-in profiles
          3. Poll for accepted connections
          4. Send personalized messages to accepted connections

        Returns:
            A summary dict with counts for each stage.
        """
        run_id = str(uuid4())
        logger.info("=== Clawbot run starting: %s ===", run_id)
        self.activity_log.log("RUN_STARTED", run_id=run_id)

        summary = {
            "run_id": run_id,
            "scraped": 0,
            "filtered_in": 0,
            "filtered_out": 0,
            "connections_sent": 0,
            "connections_failed": 0,
            "connections_accepted": 0,
            "messages_sent": 0,
            "messages_failed": 0,
        }

        driver = self._get_driver()
        session = LinkedInSession(driver, self.config)
        session.ensure_logged_in()

        # --- Stage 1: Scrape and filter ---
        logger.info("Stage 1: Scraping and filtering profiles...")
        searcher = ProfileSearcher(driver, self.config)
        parser = ProfileParser(driver, self.config)
        filter_engine = FilterEngine(self.config)

        profile_urls = searcher.collect_profile_urls()
        summary["scraped"] = len(profile_urls)

        for url in profile_urls:
            if self.store.already_seen(url):
                continue
            self.activity_log.log("PROFILE_SCRAPED", run_id=run_id, profile_url=url)

            try:
                profile = parser.parse(url)
            except ProfileNotFoundError as exc:
                logger.warning("Could not parse profile %s: %s", url, exc)
                self.store.upsert(url, state="FILTERED_OUT", error=str(exc))
                continue

            passed, reason = filter_engine.evaluate(profile)
            if passed:
                self.store.upsert(
                    url,
                    state="FILTERED_IN",
                    full_name=profile.get("full_name", ""),
                    raw_data=profile,
                )
                self.activity_log.log(
                    "FILTER_PASS", run_id=run_id,
                    profile_url=url, profile_name=profile.get("full_name", ""),
                )
                summary["filtered_in"] += 1
            else:
                self.store.upsert(url, state="FILTERED_OUT", full_name=profile.get("full_name", ""))
                self.activity_log.log(
                    "FILTER_FAIL", run_id=run_id,
                    profile_url=url, profile_name=profile.get("full_name", ""),
                    reason=reason,
                )
                summary["filtered_out"] += 1

            time.sleep(random.uniform(
                self.config.between_profiles_min,
                self.config.between_profiles_max,
            ))

        # --- Stage 2: Send connection requests ---
        logger.info("Stage 2: Sending connection requests...")
        connector = Connector(driver, self.config)
        candidates = self.store.get_profiles_in_state("FILTERED_IN")

        for profile_row in candidates:
            if not self.rate_limiter.consume_connection():
                logger.warning("Rate limit reached — pausing connection requests.")
                self.activity_log.log(
                    "RATE_LIMITED", run_id=run_id,
                    profile_url=profile_row["profile_url"],
                    **self.rate_limiter.status(),
                )
                break

            url = profile_row["profile_url"]
            try:
                sent = connector.send_request(url)
                if sent:
                    self.store.upsert(url, state="CONNECTION_SENT")
                    self.activity_log.log(
                        "CONNECTION_SENT", run_id=run_id,
                        profile_url=url,
                        profile_name=profile_row.get("full_name", ""),
                    )
                    summary["connections_sent"] += 1
            except ConnectionRequestError as exc:
                self.store.upsert(url, state="CONNECTION_FAILED", error=str(exc))
                self.activity_log.log(
                    "CONNECTION_FAILED", run_id=run_id,
                    profile_url=url, error=str(exc),
                )
                summary["connections_failed"] += 1

            time.sleep(random.uniform(
                self.config.between_profiles_min,
                self.config.between_profiles_max,
            ))

        # --- Stage 3: Poll for accepted connections ---
        logger.info("Stage 3: Polling for accepted connections...")
        poller = AcceptancePoller(driver, self.store, self.config)
        accepted_count = poller.update_accepted_connections()
        summary["connections_accepted"] = accepted_count
        self.activity_log.log(
            "POLL_COMPLETE", run_id=run_id,
            newly_accepted=accepted_count,
        )

        # --- Stage 4: Send messages to accepted connections ---
        logger.info("Stage 4: Sending messages to accepted connections...")
        messenger = Messenger(driver, self.config)
        accepted_profiles = self.store.get_profiles_in_state("CONNECTION_ACCEPTED")

        for profile_row in accepted_profiles:
            url = profile_row["profile_url"]
            raw_data = {}
            if profile_row.get("raw_data_json"):
                try:
                    raw_data = json.loads(profile_row["raw_data_json"])
                except json.JSONDecodeError:
                    raw_data = {}

            # Merge DB row with parsed data for GPT context
            profile_for_gpt = {**raw_data, "profile_url": url}

            try:
                message = self.gpt.generate_message(profile_for_gpt)
                messenger.send(profile_row, message)
                self.store.upsert(url, state="MESSAGE_SENT", message_text=message)
                self.activity_log.log(
                    "MESSAGE_SENT", run_id=run_id,
                    profile_url=url,
                    profile_name=profile_row.get("full_name", ""),
                    message_preview=message[:100],
                )
                summary["messages_sent"] += 1
            except (MessageError, ClawbotError) as exc:
                self.store.upsert(url, state="MESSAGE_FAILED", error=str(exc))
                self.activity_log.log(
                    "MESSAGE_FAILED", run_id=run_id,
                    profile_url=url, error=str(exc),
                )
                summary["messages_failed"] += 1

            time.sleep(random.uniform(
                self.config.message_delay_min,
                self.config.message_delay_max,
            ))

        # --- Finalize ---
        if self.config.export_csv:
            self.activity_log.export_csv()

        cost = self.gpt.cost_report()
        summary["gpt_cost_usd"] = cost["estimated_cost_usd"]
        summary["state_counts"] = self.store.count_by_state()

        summary_without_run_id = {k: v for k, v in summary.items() if k != "run_id"}
        self.activity_log.log("RUN_COMPLETE", run_id=run_id, **summary_without_run_id)
        logger.info("=== Run complete: %s ===", run_id)
        logger.info("Summary: %s", summary)
        return summary

    def _get_driver(self):
        if self._driver is None:
            self._driver = create_driver(self.config)
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None
