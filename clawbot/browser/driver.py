"""Chrome/Selenium WebDriver factory with stealth and anti-detection settings."""

import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from clawbot.utils.exceptions import BrowserError

logger = logging.getLogger(__name__)


def create_driver(config):
    """Create and return a stealth Chrome WebDriver.

    Uses webdriver-manager to download the correct ARM64 chromedriver on Apple
    Silicon, and selenium-stealth to patch automation fingerprints.
    """
    options = Options()

    if config.headless:
        options.add_argument("--headless=new")

    options.add_argument(f"--window-size={config.window_width},{config.window_height}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Persistent Chrome profile so login state survives restarts
    user_data_dir = Path(config.user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as exc:
        raise BrowserError(f"Failed to launch Chrome: {exc}") from exc

    driver.implicitly_wait(config.implicit_wait)
    driver.set_page_load_timeout(config.page_load_timeout)

    # Apply selenium-stealth patches
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    # Remove navigator.webdriver via JS
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
