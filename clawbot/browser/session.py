"""LinkedIn login, session validation, and cookie persistence."""

import logging
import pickle
import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import human_delay, human_type
from clawbot.utils.exceptions import LoginError, SessionExpiredError

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"


class LinkedInSession:
    """Manages LinkedIn authentication state."""

    def __init__(self, driver: WebDriver, config):
        self.driver = driver
        self.config = config
        self.cookies_path = Path(config.cookies_path)
        self.cookies_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_logged_in(self) -> None:
        """Guarantee an active LinkedIn session; login if needed."""
        if self._try_restore_session():
            logger.info("Session restored from saved state.")
            return
        logger.info("No valid session found — performing fresh login.")
        self._login()

    def _try_restore_session(self) -> bool:
        """Attempt to restore session via Chrome profile (preferred) or cookies."""
        self.driver.get(LINKEDIN_FEED_URL)
        human_delay(2, 4)
        if self._is_logged_in():
            return True

        # Fallback: load pickled cookies
        if not self.cookies_path.exists():
            return False

        try:
            self.driver.get("https://www.linkedin.com")
            with open(self.cookies_path, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            self.driver.get(LINKEDIN_FEED_URL)
            human_delay(2, 4)
            return self._is_logged_in()
        except Exception as exc:
            logger.warning("Cookie restore failed: %s", exc)
            return False

    def _is_logged_in(self) -> bool:
        return "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url

    def _login(self) -> None:
        self.driver.get(LINKEDIN_LOGIN_URL)
        human_delay(2, 4)

        try:
            wait = WebDriverWait(self.driver, 15)
            email_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
        except Exception as exc:
            raise LoginError(f"Login page elements not found: {exc}") from exc

        human_type(email_field, self.config.linkedin_email)
        human_delay(0.5, 1.5)
        human_type(password_field, self.config.linkedin_password)
        human_delay(0.3, 0.8)
        password_field.send_keys(Keys.RETURN)

        # Wait for redirect to feed
        try:
            WebDriverWait(self.driver, 20).until(
                lambda d: "feed" in d.current_url or "check" in d.current_url
            )
        except Exception as exc:
            raise LoginError("Login did not redirect to feed — check credentials.") from exc

        if "checkpoint" in self.driver.current_url or "check" in self.driver.current_url:
            raise LoginError(
                "LinkedIn triggered a security checkpoint. "
                "Complete it manually, then re-run Clawbot."
            )

        logger.info("Login successful.")
        self._save_cookies()

    def _save_cookies(self) -> None:
        cookies = self.driver.get_cookies()
        with open(self.cookies_path, "wb") as f:
            pickle.dump(cookies, f)
        logger.debug("Cookies saved to %s", self.cookies_path)
