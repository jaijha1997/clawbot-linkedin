"""Shared pytest fixtures for Clawbot tests."""

import os
import pytest
import tempfile
from unittest.mock import MagicMock


@pytest.fixture
def mock_config():
    """Minimal config object for unit tests — no browser or API calls."""
    cfg = MagicMock()
    cfg.target_roles = ["Software Engineer", "Product Manager", "CTO"]
    cfg.target_industries = ["Technology", "SaaS"]
    cfg.target_seniority = ["Senior", "Lead", "Director", "VP", "Head"]
    cfg.target_locations = ["San Francisco Bay Area", "New York City Metropolitan Area"]
    cfg.max_profiles_per_run = 10
    cfg.connection_degree = 2
    cfg.connections_per_day = 20
    cfg.connections_per_hour = 5
    cfg.message_delay_min = 0.01
    cfg.message_delay_max = 0.02
    cfg.page_delay_min = 0.01
    cfg.page_delay_max = 0.02
    cfg.between_profiles_min = 0.01
    cfg.between_profiles_max = 0.02
    cfg.ai_model = "gpt-4o"
    cfg.ai_max_tokens = 300
    cfg.ai_temperature = 0.8
    cfg.ai_persona = "friendly SaaS founder"
    cfg.product_name = "Clawbot"
    cfg.product_context = "Clawbot automates LinkedIn outreach."
    cfg.message_max_chars = 1800
    cfg.gemini_api_key = "test-gemini-key"
    return cfg


@pytest.fixture
def tmp_db(tmp_path):
    """Return a path to a temporary SQLite database for tests."""
    return str(tmp_path / "test_state.db")


@pytest.fixture
def state_store(tmp_db):
    from clawbot.core.state_store import StateStore
    return StateStore(tmp_db)


@pytest.fixture
def sample_profile():
    """A realistic parsed profile dict for testing."""
    return {
        "url": "https://www.linkedin.com/in/jane-doe-test",
        "full_name": "Jane Doe",
        "headline": "Senior Software Engineer at TestCorp",
        "location": "San Francisco Bay Area",
        "about": "Passionate about building scalable systems.",
        "current_role": "Senior Software Engineer",
        "current_company": "TestCorp",
        "experience": [
            {"title": "Senior Software Engineer", "company": "TestCorp", "duration": "2 yrs"},
            {"title": "Software Engineer", "company": "OtherCo", "duration": "3 yrs"},
        ],
        "education": [{"school": "Stanford University", "degree": "BS Computer Science"}],
        "skills": ["Python", "Distributed Systems", "Kubernetes"],
        "connection_degree": 2,
    }
