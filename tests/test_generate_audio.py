"""Unit tests for audio generation module."""

import pytest

from async_standup.generate_audio import get_scenario_for_day, STANDUP_SCENARIOS


def test_get_scenario_for_day_1():
    """Test retrieving scenario for day 1."""
    scenario = get_scenario_for_day(1)
    assert scenario["day"] == 1
    assert "auth feature" in scenario["text"]
    assert "enthusiasm" in scenario["instructions"].lower()


def test_get_scenario_for_day_5():
    """Test retrieving scenario for day 5."""
    scenario = get_scenario_for_day(5)
    assert scenario["day"] == 5
    assert "stuck" in scenario["text"].lower()
    assert "defeated" in scenario["instructions"].lower()


def test_get_scenario_for_day_invalid_low():
    """Test that invalid day number (too low) raises ValueError."""
    with pytest.raises(ValueError, match="Day must be between 1 and 5"):
        get_scenario_for_day(0)


def test_get_scenario_for_day_invalid_high():
    """Test that invalid day number (too high) raises ValueError."""
    with pytest.raises(ValueError, match="Day must be between 1 and 5"):
        get_scenario_for_day(6)


def test_standup_scenarios_count():
    """Test that we have exactly 5 scenarios."""
    assert len(STANDUP_SCENARIOS) == 5


def test_standup_scenarios_structure():
    """Test that all scenarios have required fields."""
    for i, scenario in enumerate(STANDUP_SCENARIOS, 1):
        assert "day" in scenario
        assert "text" in scenario
        assert "instructions" in scenario
        assert scenario["day"] == i


def test_emotional_progression():
    """Test that scenarios show emotional decline."""
    # Check that keywords indicate declining emotion
    day1_text = STANDUP_SCENARIOS[0]["text"].lower()
    day5_text = STANDUP_SCENARIOS[4]["text"].lower()
    
    # Day 1 should be positive
    assert "started" in day1_text or "!" in day1_text
    
    # Day 5 should show being stuck
    assert "stuck" in day5_text
    assert "days" in day5_text  # Mentions multiple days


def test_auth_keyword_appears_all_days():
    """Test that 'auth' keyword appears in all 5 days."""
    for scenario in STANDUP_SCENARIOS:
        assert "auth" in scenario["text"].lower()
