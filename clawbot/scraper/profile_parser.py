"""Extracts structured data from a LinkedIn profile page."""

import logging
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from clawbot.browser.anti_detect import human_delay, human_scroll
from clawbot.utils.exceptions import ProfileNotFoundError

logger = logging.getLogger(__name__)

# CSS selectors — update these if LinkedIn changes its DOM structure
SELECTORS = {
    "name": "h1.text-heading-xlarge",
    "headline": ".text-body-medium.break-words",
    "location": ".text-body-small.inline.t-black--light.break-words",
    "about": "#about ~ .display-flex .full-width span[aria-hidden='true']",
    "experience_section": "#experience",
    "education_section": "#education",
    "skills_section": "#skills",
    "connect_degree": ".dist-value",
}


def _safe_text(driver: WebDriver, css: str, default: str = "") -> str:
    try:
        el = driver.find_element(By.CSS_SELECTOR, css)
        return el.text.strip()
    except Exception:
        return default


def _safe_texts(driver: WebDriver, css: str) -> list[str]:
    try:
        els = driver.find_elements(By.CSS_SELECTOR, css)
        return [el.text.strip() for el in els if el.text.strip()]
    except Exception:
        return []


class ProfileParser:
    """Parses a LinkedIn profile page into a structured dict."""

    def __init__(self, driver: WebDriver, config):
        self.driver = driver
        self.config = config

    def parse(self, profile_url: str) -> dict[str, Any]:
        """Navigate to the profile URL and extract all relevant data."""
        self.driver.get(profile_url)
        human_delay(self.config.page_delay_min, self.config.page_delay_max)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["name"]))
            )
        except Exception as exc:
            raise ProfileNotFoundError(
                f"Profile page did not load: {profile_url}"
            ) from exc

        # Scroll to load lazy sections
        human_scroll(self.driver)
        human_delay(1, 2)
        human_scroll(self.driver)
        human_delay(0.5, 1)

        profile: dict[str, Any] = {
            "url": profile_url,
            "full_name": _safe_text(self.driver, SELECTORS["name"]),
            "headline": _safe_text(self.driver, SELECTORS["headline"]),
            "location": _safe_text(self.driver, SELECTORS["location"]),
            "about": self._parse_about(),
            "current_role": "",
            "current_company": "",
            "experience": self._parse_experience(),
            "education": self._parse_education(),
            "skills": self._parse_skills(),
            "connection_degree": self._parse_connection_degree(),
        }

        # Derive current role/company from first experience entry
        if profile["experience"]:
            first = profile["experience"][0]
            profile["current_role"] = first.get("title", "")
            profile["current_company"] = first.get("company", "")

        return profile

    def _parse_about(self) -> str:
        try:
            els = self.driver.find_elements(
                By.CSS_SELECTOR,
                "section[data-section='summary'] span[aria-hidden='true']",
            )
            if els:
                return " ".join(el.text.strip() for el in els if el.text.strip())
        except Exception:
            pass
        return _safe_text(self.driver, SELECTORS["about"])

    def _parse_experience(self) -> list[dict[str, str]]:
        entries = []
        try:
            section = self.driver.find_element(By.ID, "experience")
            items = section.find_elements(
                By.CSS_SELECTOR, "li.artdeco-list__item"
            )
            for item in items[:5]:  # Cap at 5 experience entries
                title = ""
                company = ""
                duration = ""
                spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
                texts = [s.text.strip() for s in spans if s.text.strip()]
                if texts:
                    title = texts[0]
                if len(texts) > 1:
                    company = texts[1]
                if len(texts) > 2:
                    duration = texts[2]
                if title:
                    entries.append({"title": title, "company": company, "duration": duration})
        except Exception:
            pass
        return entries

    def _parse_education(self) -> list[dict[str, str]]:
        entries = []
        try:
            section = self.driver.find_element(By.ID, "education")
            items = section.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item")
            for item in items[:3]:
                spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
                texts = [s.text.strip() for s in spans if s.text.strip()]
                if texts:
                    entries.append({
                        "school": texts[0],
                        "degree": texts[1] if len(texts) > 1 else "",
                    })
        except Exception:
            pass
        return entries

    def _parse_skills(self) -> list[str]:
        try:
            section = self.driver.find_element(By.ID, "skills")
            spans = section.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
            return [s.text.strip() for s in spans if s.text.strip()][:10]
        except Exception:
            return []

    def _parse_connection_degree(self) -> int:
        """Return 1, 2, or 3 based on the connection degree badge."""
        text = _safe_text(self.driver, SELECTORS["connect_degree"])
        if "1st" in text:
            return 1
        if "2nd" in text:
            return 2
        return 3
