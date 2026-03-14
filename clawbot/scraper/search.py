"""LinkedIn people search URL builder and profile URL paginator."""

import logging
import urllib.parse
from typing import Generator

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import human_delay, human_scroll

logger = logging.getLogger(__name__)

# CSS selectors for LinkedIn search results (as of 2024 — update if LinkedIn changes)
RESULT_LINK_SELECTOR = "a.app-aware-link[href*='/in/']"
NEXT_PAGE_SELECTOR = "button[aria-label='Next']"


def _build_search_url(keywords: str, page: int = 1) -> str:
    params = {
        "keywords": keywords,
        "origin": "GLOBAL_SEARCH_HEADER",
        "sid": "clawbot",
    }
    if page > 1:
        params["page"] = str(page)
    return "https://www.linkedin.com/search/results/people/?" + urllib.parse.urlencode(params)


class ProfileSearcher:
    """Searches LinkedIn people and yields profile URLs."""

    def __init__(self, driver: WebDriver, config):
        self.driver = driver
        self.config = config

    def collect_profile_urls(self) -> list[str]:
        """Collect up to max_profiles_per_run profile URLs matching targeting config."""
        seen: set[str] = set()
        urls: list[str] = []
        max_profiles = self.config.max_profiles_per_run

        # Build search keywords from roles + seniority
        keywords = " OR ".join(self.config.target_roles[:3])

        page = 1
        while len(urls) < max_profiles:
            search_url = _build_search_url(keywords, page)
            logger.info("Searching page %d: %s", page, search_url)
            self.driver.get(search_url)
            human_delay(self.config.page_delay_min, self.config.page_delay_max)

            page_urls = self._extract_profile_urls_from_page()
            new_urls = [u for u in page_urls if u not in seen]

            if not new_urls:
                logger.info("No new profiles on page %d — stopping search.", page)
                break

            for url in new_urls:
                if len(urls) >= max_profiles:
                    break
                seen.add(url)
                urls.append(url)

            if not self._has_next_page():
                break

            page += 1
            human_delay(2, 5)

        logger.info("Collected %d profile URLs.", len(urls))
        return urls

    def _extract_profile_urls_from_page(self) -> list[str]:
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, RESULT_LINK_SELECTOR))
            )
        except Exception:
            logger.warning("No profile links found on search results page.")
            return []

        elements = self.driver.find_elements(By.CSS_SELECTOR, RESULT_LINK_SELECTOR)
        urls = []
        for el in elements:
            href = el.get_attribute("href") or ""
            # Normalize to base profile URL (strip query params and trailing slash)
            if "/in/" in href:
                base = href.split("?")[0].rstrip("/")
                if base not in urls:
                    urls.append(base)
        return urls

    def _has_next_page(self) -> bool:
        buttons = self.driver.find_elements(By.CSS_SELECTOR, NEXT_PAGE_SELECTOR)
        return bool(buttons and buttons[0].is_enabled())
