"""Profile filter engine — applies targeting rules from config."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FilterEngine:
    """Evaluates a parsed profile against targeting configuration.

    Each filter method returns (passed: bool, reason: str).
    The engine is fail-fast: the first failing filter short-circuits.
    """

    def __init__(self, config):
        self.config = config

    def evaluate(self, profile: dict[str, Any]) -> tuple[bool, str]:
        """Run all filters against the profile.

        Returns:
            (True, "PASS") if the profile passes all filters.
            (False, reason) if any filter rejects the profile.
        """
        checks = [
            self._filter_connection_degree,
            self._filter_by_role,
            self._filter_by_seniority,
            self._filter_by_location,
        ]
        for check in checks:
            passed, reason = check(profile)
            if not passed:
                return False, reason
        return True, "PASS"

    def _filter_connection_degree(self, profile: dict[str, Any]) -> tuple[bool, str]:
        degree = profile.get("connection_degree", 3)
        if degree == 1:
            return False, "SKIP_1ST_DEGREE"
        if degree == 3:
            return False, "SKIP_3RD_DEGREE"
        return True, ""

    def _filter_by_role(self, profile: dict[str, Any]) -> tuple[bool, str]:
        target_roles = [r.lower() for r in self.config.target_roles]
        headline = profile.get("headline", "").lower()
        current_role = profile.get("current_role", "").lower()
        combined = headline + " " + current_role

        for role in target_roles:
            # Full phrase match first (most precise)
            if role in combined:
                return True, ""
            # Fallback: all significant words must match (avoids single-word false positives)
            words = [w for w in role.split() if len(w) > 3]
            if words and all(w in combined for w in words):
                return True, ""

        return False, f"ROLE_MISMATCH: '{profile.get('headline', '')}'"

    def _filter_by_seniority(self, profile: dict[str, Any]) -> tuple[bool, str]:
        target_seniority = [s.lower() for s in self.config.target_seniority]
        headline = profile.get("headline", "").lower()
        current_role = profile.get("current_role", "").lower()
        combined = headline + " " + current_role

        for level in target_seniority:
            if level in combined:
                return True, ""

        return False, f"SENIORITY_MISMATCH: '{profile.get('headline', '')}'"

    def _filter_by_location(self, profile: dict[str, Any]) -> tuple[bool, str]:
        if not self.config.target_locations:
            return True, ""  # No location filter configured

        profile_location = profile.get("location", "").lower()
        for loc in self.config.target_locations:
            loc_lower = loc.lower()
            # Check if any significant word from the target location appears in the profile location
            # and vice versa (bidirectional partial match)
            loc_words = [w for w in loc_lower.replace(",", " ").split() if len(w) > 3]
            profile_words = [w for w in profile_location.replace(",", " ").split() if len(w) > 3]
            if any(w in profile_location for w in loc_words) or any(w in loc_lower for w in profile_words):
                return True, ""

        return False, f"LOCATION_MISMATCH: '{profile.get('location', '')}'"
