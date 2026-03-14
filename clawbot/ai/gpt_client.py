"""Gemini AI client with retry, token tracking, and response validation."""

import logging
from typing import Any

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

from clawbot.ai.prompt_builder import build_system_prompt, build_user_prompt
from clawbot.utils.exceptions import AIError
from clawbot.utils.retry import retry

logger = logging.getLogger(__name__)

# Approximate cost per 1K tokens for gemini-1.5-pro
COST_PER_1K_INPUT = 0.00125
COST_PER_1K_OUTPUT = 0.005


class GPTClient:
    """Wraps the Gemini API for personalized LinkedIn message generation."""

    def __init__(self, config):
        self.config = config
        genai.configure(api_key=config.gemini_api_key)
        self._model = genai.GenerativeModel(
            model_name=config.ai_model,
            generation_config=genai.GenerationConfig(
                max_output_tokens=config.ai_max_tokens,
                temperature=config.ai_temperature,
            ),
        )
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @retry(max_attempts=3, base_delay=5.0, exceptions=(ResourceExhausted, ServiceUnavailable))
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

        # Gemini combines system + user via the system_instruction param
        model = genai.GenerativeModel(
            model_name=self.config.ai_model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=self.config.ai_max_tokens,
                temperature=self.config.ai_temperature,
            ),
        )

        try:
            response = model.generate_content(user_prompt)
        except (ResourceExhausted, ServiceUnavailable):
            raise  # Let @retry handle these
        except Exception as exc:
            raise AIError(f"Gemini call failed: {exc}") from exc

        # Track token usage
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            output_tokens = getattr(meta, "candidates_token_count", 0) or 0
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            cost = (
                input_tokens / 1000 * COST_PER_1K_INPUT
                + output_tokens / 1000 * COST_PER_1K_OUTPUT
            )
            logger.debug(
                "Gemini call: %d in / %d out tokens — $%.4f",
                input_tokens, output_tokens, cost,
            )

        try:
            message = response.text.strip()
        except Exception as exc:
            raise AIError(f"Gemini returned no text: {exc}") from exc

        self._validate_message(message, profile.get("full_name", ""))
        return message

    def _validate_message(self, message: str, recipient_name: str) -> None:
        if not message:
            raise AIError("Gemini returned an empty message.")
        if len(message) > self.config.message_max_chars:
            raise AIError(
                f"Gemini message too long: {len(message)} chars "
                f"(max {self.config.message_max_chars})."
            )
        refusal_signals = ["I'm sorry", "I cannot", "I can't", "I'm unable"]
        if any(sig in message for sig in refusal_signals):
            raise AIError(f"Gemini returned a refusal response for {recipient_name}.")

    def cost_report(self) -> dict[str, Any]:
        input_cost = self._total_input_tokens / 1000 * COST_PER_1K_INPUT
        output_cost = self._total_output_tokens / 1000 * COST_PER_1K_OUTPUT
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 4),
        }
