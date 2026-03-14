"""OpenAI GPT client with retry, cost tracking, and response validation."""

import logging
from typing import Any

from openai import OpenAI, RateLimitError, APIError

from clawbot.ai.prompt_builder import build_system_prompt, build_user_prompt
from clawbot.utils.exceptions import AIError
from clawbot.utils.retry import retry

logger = logging.getLogger(__name__)

# Approximate cost per 1K tokens for gpt-4o (update if pricing changes)
COST_PER_1K_INPUT = 0.005
COST_PER_1K_OUTPUT = 0.015


class GPTClient:
    """Wraps the OpenAI API for personalized LinkedIn message generation."""

    def __init__(self, config):
        self.config = config
        self._client = OpenAI(api_key=config.openai_api_key)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @retry(max_attempts=3, base_delay=5.0, exceptions=(RateLimitError, APIError))
    def generate_message(self, profile: dict[str, Any]) -> str:
        """Generate a personalized outreach message for the given profile.

        Args:
            profile: Parsed profile dict from ProfileParser.

        Returns:
            The generated message text.

        Raises:
            AIError: If generation fails or the response is invalid.
        """
        system_prompt = build_system_prompt(self.config)
        user_prompt = build_user_prompt(profile, self.config)

        try:
            response = self._client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.config.ai_max_tokens,
                temperature=self.config.ai_temperature,
            )
        except (RateLimitError, APIError):
            raise  # Let @retry handle these
        except Exception as exc:
            raise AIError(f"OpenAI call failed: {exc}") from exc

        usage = response.usage
        if usage:
            self._total_input_tokens += usage.prompt_tokens
            self._total_output_tokens += usage.completion_tokens
            cost = (
                usage.prompt_tokens / 1000 * COST_PER_1K_INPUT
                + usage.completion_tokens / 1000 * COST_PER_1K_OUTPUT
            )
            logger.debug(
                "GPT call: %d in / %d out tokens — $%.4f",
                usage.prompt_tokens, usage.completion_tokens, cost,
            )

        message = response.choices[0].message.content or ""
        message = message.strip()

        self._validate_message(message, profile.get("full_name", ""))
        return message

    def _validate_message(self, message: str, recipient_name: str) -> None:
        if not message:
            raise AIError("GPT returned an empty message.")
        if len(message) > self.config.message_max_chars:
            raise AIError(
                f"GPT message too long: {len(message)} chars "
                f"(max {self.config.message_max_chars})."
            )
        # Detect refusals (GPT occasionally refuses to write promotional content)
        refusal_signals = ["I'm sorry", "I cannot", "I can't", "I'm unable"]
        if any(sig in message for sig in refusal_signals):
            raise AIError(f"GPT returned a refusal response for {recipient_name}.")

    def cost_report(self) -> dict[str, Any]:
        input_cost = self._total_input_tokens / 1000 * COST_PER_1K_INPUT
        output_cost = self._total_output_tokens / 1000 * COST_PER_1K_OUTPUT
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 4),
        }
