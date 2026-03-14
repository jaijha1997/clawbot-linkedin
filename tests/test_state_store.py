"""Unit tests for StateStore."""

import pytest
from clawbot.core.state_store import StateStore
from clawbot.utils.exceptions import StateStoreError


URL = "https://www.linkedin.com/in/test-user"


def test_upsert_and_retrieve(state_store):
    state_store.upsert(URL, state="FILTERED_IN", full_name="Test User")
    profile = state_store.get_profile(URL)
    assert profile is not None
    assert profile["state"] == "FILTERED_IN"
    assert profile["full_name"] == "Test User"


def test_already_seen_returns_true_after_insert(state_store):
    assert state_store.already_seen(URL) is False
    state_store.upsert(URL, state="DISCOVERED")
    assert state_store.already_seen(URL) is True


def test_state_transition(state_store):
    state_store.upsert(URL, state="FILTERED_IN")
    state_store.upsert(URL, state="CONNECTION_SENT")
    profile = state_store.get_profile(URL)
    assert profile["state"] == "CONNECTION_SENT"
    assert profile["connection_sent_at"] is not None


def test_message_text_persisted(state_store):
    state_store.upsert(URL, state="FILTERED_IN")
    state_store.upsert(URL, state="MESSAGE_SENT", message_text="Hello, this is a test message.")
    profile = state_store.get_profile(URL)
    assert profile["message_text"] == "Hello, this is a test message."
    assert profile["message_sent_at"] is not None


def test_invalid_state_raises(state_store):
    with pytest.raises(StateStoreError):
        state_store.upsert(URL, state="INVALID_STATE")


def test_get_profiles_in_state(state_store):
    state_store.upsert(URL + "/a", state="FILTERED_IN")
    state_store.upsert(URL + "/b", state="FILTERED_IN")
    state_store.upsert(URL + "/c", state="CONNECTION_SENT")

    filtered = state_store.get_profiles_in_state("FILTERED_IN")
    assert len(filtered) == 2

    sent = state_store.get_profiles_in_state("CONNECTION_SENT")
    assert len(sent) == 1


def test_count_by_state(state_store):
    state_store.upsert(URL + "/1", state="FILTERED_IN")
    state_store.upsert(URL + "/2", state="FILTERED_OUT")
    state_store.upsert(URL + "/3", state="FILTERED_OUT")

    counts = state_store.count_by_state()
    assert counts["FILTERED_IN"] == 1
    assert counts["FILTERED_OUT"] == 2
