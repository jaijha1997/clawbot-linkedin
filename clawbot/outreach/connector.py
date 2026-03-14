"""Sends LinkedIn connection requests."""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import click_with_human_behavior, human_delay
from clawbot.utils.exceptions import ConnectionRequestError

logger = logging.getLogger(__name__)

# Possible selectors for the Connect button — LinkedIn serves different layouts
CONNECT_BUTTON_SELECTORS = [
    "button[aria-label^='Connect']",
    "button[aria-label^='Invite']",
]
MORE_BUTTON_SELECTOR = "button[aria-label='More actions']"
MORE_CONNECT_SELECTOR = "div[aria-label^='Connect']"
MODAL_SEND_SELECTOR = "button[aria-label='Send without a note']"
MODAL_SEND_ALT_SELECTOR = "button[aria-label='Send now']"
PENDING_INDICATOR_SELECTOR = "button[aria-label^='Pending']"


class Connector:
    """Sends connection requests to LinkedIn profiles."""

    def __init__(self, driver: WebDriver, config):
        self.driver = driver
        self.config = config

    def send_request(self, profile_url: str) -> bool:
        """Navigate to the profile and click the Connect button.

        Returns:
            True if the connection request was sent successfully.

        Raises:
            ConnectionRequestError: If the connect button cannot be found or clicked.
        """
        self.driver.get(profile_url)
        human_delay(self.config.page_delay_min, self.config.page_delay_max)

        # Check if already connected or pending
        if self._is_already_connected_or_pending():
            logger.info("Already connected/pending: %s", profile_url)
            return False

        connect_btn = self._find_connect_button()
        if connect_btn is None:
            raise ConnectionRequestError(
                f"Could not find Connect button on: {profile_url}"
            )

        click_with_human_behavior(self.driver, connect_btn)
        human_delay(1, 2)

        # Handle the "Add a note?" modal — always skip note (looks more human)
        self._dismiss_add_note_modal()
        human_delay(1, 3)

        logger.info("Connection request sent to: %s", profile_url)
        return True

    def _find_connect_button(self):
        """Try multiple selectors to locate the Connect button."""
        for selector in CONNECT_BUTTON_SELECTORS:
            btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if btns:
                return btns[0]

        # Some profiles hide Connect behind the "More" overflow menu
        return self._find_connect_in_more_menu()

    def _find_connect_in_more_menu(self):
        more_btns = self.driver.find_elements(By.CSS_SELECTOR, MORE_BUTTON_SELECTOR)
        if not more_btns:
            return None

        click_with_human_behavior(self.driver, more_btns[0])
        human_delay(0.5, 1)

        dropdown_items = self.driver.find_elements(By.CSS_SELECTOR, MORE_CONNECT_SELECTOR)
        return dropdown_items[0] if dropdown_items else None

    def _dismiss_add_note_modal(self) -> None:
        """Click 'Send without a note' if the modal appears."""
        for selector in (MODAL_SEND_SELECTOR, MODAL_SEND_ALT_SELECTOR):
            btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if btns:
                click_with_human_behavior(self.driver, btns[0])
                return

    def _is_already_connected_or_pending(self) -> bool:
        pending = self.driver.find_elements(By.CSS_SELECTOR, PENDING_INDICATOR_SELECTOR)
        connected = self.driver.find_elements(
            By.CSS_SELECTOR, "button[aria-label^='Message']"
        )
        return bool(pending or connected)
