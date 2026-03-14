"""Custom exception hierarchy for Clawbot."""


class ClawbotError(Exception):
    """Base exception for all Clawbot errors."""


class ConfigError(ClawbotError):
    """Raised when configuration is invalid or missing."""


class BrowserError(ClawbotError):
    """Raised when browser automation fails."""


class LoginError(BrowserError):
    """Raised when LinkedIn login fails."""


class SessionExpiredError(BrowserError):
    """Raised when the LinkedIn session has expired."""


class ScraperError(ClawbotError):
    """Raised when scraping fails."""


class ProfileNotFoundError(ScraperError):
    """Raised when a profile page cannot be loaded."""


class RateLimitExceededError(ClawbotError):
    """Raised when the rate limit budget is exhausted."""


class ConnectionRequestError(ClawbotError):
    """Raised when sending a connection request fails."""


class MessageError(ClawbotError):
    """Raised when sending a message fails."""


class AIError(ClawbotError):
    """Raised when GPT message generation fails."""


class StateStoreError(ClawbotError):
    """Raised when reading/writing pipeline state fails."""
