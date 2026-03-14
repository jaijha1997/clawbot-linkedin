"""Unit tests for FilterEngine."""

import pytest
from clawbot.scraper.filter_engine import FilterEngine


def test_passes_matching_profile(mock_config, sample_profile):
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is True
    assert reason == "PASS"


def test_rejects_1st_degree(mock_config, sample_profile):
    sample_profile["connection_degree"] = 1
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is False
    assert "1ST_DEGREE" in reason


def test_rejects_3rd_degree(mock_config, sample_profile):
    sample_profile["connection_degree"] = 3
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is False
    assert "3RD_DEGREE" in reason


def test_rejects_wrong_role(mock_config, sample_profile):
    sample_profile["headline"] = "Accountant at TestCorp"
    sample_profile["current_role"] = "Accountant"
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is False
    assert "ROLE_MISMATCH" in reason


def test_rejects_wrong_seniority(mock_config, sample_profile):
    sample_profile["headline"] = "Junior Software Engineer at TestCorp"
    sample_profile["current_role"] = "Junior Software Engineer"
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is False
    assert "SENIORITY_MISMATCH" in reason


def test_rejects_wrong_location(mock_config, sample_profile):
    sample_profile["location"] = "London, United Kingdom"
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is False
    assert "LOCATION_MISMATCH" in reason


def test_no_location_filter_passes_any_location(mock_config, sample_profile):
    mock_config.target_locations = []
    sample_profile["location"] = "Anywhere, World"
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is True


def test_partial_location_match(mock_config, sample_profile):
    sample_profile["location"] = "San Francisco, CA"
    engine = FilterEngine(mock_config)
    passed, reason = engine.evaluate(sample_profile)
    assert passed is True
