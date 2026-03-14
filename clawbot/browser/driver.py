"""Chrome/Selenium WebDriver factory with stealth and anti-detection settings."""

import logging
import os
from pathlib import Path

import undetected_chromedriver as uc
from selenium_stealth import stealth

from clawbot.utils.exceptions import BrowserError

logger = logging.getLogger(__name__)


def create_driver(config) -> uc.Chrome:
    """Create and return a stealth Chrome WebDriver.

    Uses undetected-chromedriver to bypass navigator.webdriver detection
    and selenium-stealth to patch remaining automation fingerprints.
    """
    options = uc.ChromeOptions()

    if config.headless:
        options.add_argument("--headless=new")

    options.add_argument(f"--window-size={config.window_width},{config.window_height}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-infobars")

    # Use a persistent Chrome profile so login state survives restarts
    user_data_dir = Path(config.user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
    except Exception as exc:
        raise BrowserError(f"Failed to launch Chrome: {exc}") from exc

    driver.implicitly_wait(config.implicit_wait)
    driver.set_page_load_timeout(config.page_load_timeout)

    # Apply selenium-stealth patches on top of undetected-chromedriver
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    # Remove `navigator.webdriver` via JS
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        },
    )

    logger.info("Chrome driver started (headless=%s)", config.headless)
    return driver
