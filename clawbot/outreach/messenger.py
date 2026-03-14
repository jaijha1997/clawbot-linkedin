"""Sends personalized messages to accepted LinkedIn connections."""

import json
import logging
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import click_with_human_behavior, human_delay, human_type
from clawbot.utils.exceptions import MessageError

logger = logging.getLogger(__name__)

MESSAGE_BTN_SELECTOR = "button[aria-label^='Message']"
COMPOSE_BOX_SELECTOR = ".msg-form__contenteditable"
SEND_BTN_SELECTOR = "button.msg-form__send-btn"


class Messenger:
    """Sends LinkedIn DMs to accepted connections."""

    def __init__(self, driver: WebDriver, config):
        self.driver = driver
        self.config = config

    def send(self, profile: dict[str, Any], message: str) -> None:
        """Navigate to the profile and send the message via the Message button.

        Args:
            profile: Profile dict with at least 'url' key.
            message: The message text to send.

        Raises:
            MessageError: If the message cannot be sent.
        """
        profile_url = profile["profile_url"]
        self.driver.get(profile_url)
        human_delay(self.config.page_delay_min, self.config.page_delay_max)

        # Click the Message button on the profile
        try:
            msg_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, MESSAGE_BTN_SELECTOR))
            )
        except Exception as exc:
            raise MessageError(
                f"Message button not found on profile: {profile_url}"
            ) from exc

        click_with_human_behavior(self.driver, msg_btn)
        human_delay(1.5, 3)

        # Wait for the compose box
        try:
            compose_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, COMPOSE_BOX_SELECTOR))
            )
        except Exception as exc:
            raise MessageError(f"Message compose box did not appear: {exc}") from exc

        compose_box.click()
        human_delay(0.3, 0.8)
        human_type(compose_box, message)
        human_delay(
            self.config.message_delay_min,
            self.config.message_delay_max,
        )

        # Click Send
        try:
            send_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BTN_SELECTOR))
            )
            click_with_human_behavior(self.driver, send_btn)
        except Exception as exc:
            raise MessageError(f"Failed to click Send button: {exc}") from exc

        human_delay(1, 2)
        logger.info(
            "Message sent to %s (%s)",
            profile.get("full_name", "unknown"),
            profile_url,
        )
