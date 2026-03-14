"""Polls LinkedIn to detect newly accepted connection requests."""

import logging
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import human_delay, human_scroll

if TYPE_CHECKING:
    from clawbot.core.state_store import StateStore

logger = logging.getLogger(__name__)

CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"
CONNECTION_CARD_SELECTOR = "li.mn-connection-card"
CONNECTION_LINK_SELECTOR = "a.mn-connection-card__link"


class AcceptancePoller:
    """Detects accepted connections by scraping the My Network connections page."""

    def __init__(self, driver: WebDriver, store: "StateStore", config):
        self.driver = driver
        self.store = store
        self.config = config

    def update_accepted_connections(self) -> int:
        """Check the connections page and update state for newly accepted profiles.

        Returns:
            Number of profiles transitioned to CONNECTION_ACCEPTED.
        """
        logger.info("Polling for accepted connections...")
        self.driver.get(CONNECTIONS_URL)
        human_delay(self.config.page_delay_min, self.config.page_delay_max)

        # Scroll to load all recent connections
        for _ in range(3):
            human_scroll(self.driver)
            human_delay(1, 2)

        # Get all profile URLs from the connections page
        connection_urls = self._scrape_connection_urls()
        logger.info("Found %d connections on the connections page.", len(connection_urls))

        # Cross-reference with profiles in CONNECTION_SENT state
        pending = self.store.get_profiles_in_state("CONNECTION_SENT")
        pending_urls = {p["profile_url"] for p in pending}

        newly_accepted = 0
        for url in connection_urls:
            normalized = url.rstrip("/").split("?")[0]
            if normalized in pending_urls:
                self.store.upsert(normalized, state="CONNECTION_ACCEPTED")
                logger.info("Connection accepted: %s", normalized)
                newly_accepted += 1

        logger.info("%d new connections accepted.", newly_accepted)
        return newly_accepted

    def _scrape_connection_urls(self) -> list[str]:
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, CONNECTION_CARD_SELECTOR))
            )
        except Exception:
            logger.warning("No connection cards found on the connections page.")
            return []

        links = self.driver.find_elements(By.CSS_SELECTOR, CONNECTION_LINK_SELECTOR)
        urls = []
        for link in links:
            href = link.get_attribute("href") or ""
            if "/in/" in href:
                urls.append(href.split("?")[0].rstrip("/"))
        return urls
