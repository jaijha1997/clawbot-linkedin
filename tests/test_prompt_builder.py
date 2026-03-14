"""Unit tests for GPT prompt builder."""

import pytest
from clawbot.ai.prompt_builder import build_system_prompt, build_user_prompt


def test_system_prompt_contains_persona(mock_config):
    prompt = build_system_prompt(mock_config)
    assert mock_config.ai_persona in prompt
    assert mock_config.product_context in prompt


def test_user_prompt_contains_profile_name(mock_config, sample_profile):
    prompt = build_user_prompt(sample_profile, mock_config)
    assert sample_profile["full_name"] in prompt


def test_user_prompt_contains_role_and_company(mock_config, sample_profile):
    prompt = build_user_prompt(sample_profile, mock_config)
    assert sample_profile["current_role"] in prompt
    assert sample_profile["current_company"] in prompt


def test_user_prompt_contains_product(mock_config, sample_profile):
    prompt = build_user_prompt(sample_profile, mock_config)
    assert mock_config.product_name in prompt


def test_user_prompt_handles_missing_fields(mock_config):
    empty_profile = {"url": "https://www.linkedin.com/in/empty"}
    prompt = build_user_prompt(empty_profile, mock_config)
    assert mock_config.product_name in prompt
    assert "there" in prompt  # Default name fallback


def test_user_prompt_truncates_about(mock_config, sample_profile):
    sample_profile["about"] = "x" * 1000
    prompt = build_user_prompt(sample_profile, mock_config)
    # About is truncated to 500 chars
    assert "x" * 501 not in prompt
