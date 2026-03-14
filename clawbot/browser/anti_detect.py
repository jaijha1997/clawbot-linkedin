"""Human-like browser interaction helpers to avoid LinkedIn bot detection."""

import random
import time

from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Sleep for a random duration to simulate human reaction time."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def human_type(element: WebElement, text: str) -> None:
    """Type text character-by-character with random inter-key delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.03, 0.15))


def human_scroll(driver: WebDriver, element: WebElement | None = None) -> None:
    """Scroll toward an element with a slight overshoot then correction."""
    if element:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element,
        )
        human_delay(0.5, 1.5)
    else:
        # Scroll down a random amount
        scroll_amount = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        human_delay(0.3, 0.8)


def random_mouse_move(driver: WebDriver) -> None:
    """Move mouse to a random position before an action to appear human."""
    try:
        actions = ActionChains(driver)
        x_offset = random.randint(-200, 200)
        y_offset = random.randint(-100, 100)
        actions.move_by_offset(x_offset, y_offset).perform()
        human_delay(0.1, 0.4)
    except Exception:
        pass  # Mouse move is best-effort; never block the main action


def click_with_human_behavior(driver: WebDriver, element: WebElement) -> None:
    """Scroll to element, move mouse near it, then click."""
    human_scroll(driver, element)
    random_mouse_move(driver)
    human_delay(0.3, 0.8)
    element.click()
