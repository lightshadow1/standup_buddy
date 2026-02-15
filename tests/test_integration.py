"""Integration tests for the full AsyncStandup pipeline."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from async_standup.storage import StandupStorage
from async_standup.generate_audio import get_scenario_for_day
from async_standup.analyze_audio import extract_emotion_data
from async_standup.insight_engine import detect_stuck_pattern, generate_insight_message


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_standups.json"
        storage = StandupStorage(data_file=str(data_file))
        yield storage


def test_full_pipeline_with_mocked_data(temp_storage):
    """Test the full pipeline from scenarios to stuck pattern detection."""
    
    # Step 1: Get scenarios (simulating audio generation)
    scenarios = []
    for day in range(1, 6):
        scenario = get_scenario_for_day(day)
        scenarios.append(scenario)
    
    assert len(scenarios) == 5
    
    # Step 2: Simulate Pulse API responses and save to storage
    base_date = datetime.now()
    
    # Simulate realistic emotion progression
    mock_emotions = [
        {"happiness": 0.75, "sadness": 0.10, "disgust": 0.05, "fear": 0.05, "anger": 0.05},
        {"happiness": 0.60, "sadness": 0.20, "disgust": 0.05, "fear": 0.10, "anger": 0.05},
        {"happiness": 0.45, "sadness": 0.30, "disgust": 0.05, "fear": 0.15, "anger": 0.05},
        {"happiness": 0.30, "sadness": 0.40, "disgust": 0.05, "fear": 0.20, "anger": 0.05},
        {"happiness": 0.20, "sadness": 0.50, "disgust": 0.05, "fear": 0.20, "anger": 0.05},
    ]
    
    for i, scenario in enumerate(scenarios):
        # Simulate API response
        api_response = {
            "transcription": scenario["text"],
            "emotions": mock_emotions[i]
        }
        
        # Extract emotion data
        emotion_data = extract_emotion_data(api_response)
        
        # Create standup entry
        standup = {
            "date": (base_date - timedelta(days=5-scenario["day"])).strftime("%Y-%m-%d"),
            "day_number": scenario["day"],
            "transcript": emotion_data["transcript"],
            "emotion_score": emotion_data["emotion_score"],
            "dominant_emotion": emotion_data["dominant_emotion"],
            "emotions": emotion_data["emotions"]
        }
        
        # Save to storage
        temp_storage.save_standup(standup)
    
    # Step 3: Verify data was saved correctly
    all_standups = temp_storage.load_standups()
    assert len(all_standups) == 5
    
    # Step 4: Get standups for analysis
    standups_for_analysis = temp_storage.get_standups_by_range(start_day=1, end_day=5)
    assert len(standups_for_analysis) == 5
    
    # Step 5: Detect stuck pattern
    stuck_info = detect_stuck_pattern(standups_for_analysis)
    
    # Verify stuck pattern was detected
    assert stuck_info is not None
    assert stuck_info["is_stuck"] is True
    assert stuck_info["repeated_keyword"] == "auth"
    assert stuck_info["keyword_count"] == 5  # All 5 days mention "auth"
    assert stuck_info["emotion_delta"] < -10  # Significant decline
    
    # Step 6: Generate insight message
    message = generate_insight_message(stuck_info)
    assert "⚠️" in message
    assert "Stuck Pattern Detected" in message
    assert "auth" in message
    assert "pairing" in message.lower()
    
    print("\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"\n✅ Processed {len(scenarios)} standup scenarios")
    print(f"✅ Saved {len(all_standups)} standup entries to storage")
    print(f"✅ Detected stuck pattern: {stuck_info['repeated_keyword']}")
    print(f"✅ Emotion decline: {stuck_info['emotion_delta']:.1f} points")
    print(f"\nGenerated Insight:\n{message}")


def test_emotion_progression_tracking(temp_storage):
    """Test that emotion scores decline over time as expected."""
    
    # Create 5 days of standups with declining emotions
    for day in range(1, 6):
        standup = {
            "day_number": day,
            "date": f"2026-02-{10+day}",
            "transcript": f"Working on auth feature day {day}",
            "emotion_score": 80.0 - (day * 10),  # 70, 60, 50, 40, 30
            "dominant_emotion": "happiness" if day <= 2 else "sadness",
            "emotions": {}
        }
        temp_storage.save_standup(standup)
    
    # Retrieve and verify
    standups = temp_storage.get_standups_by_range()
    
    # Check emotion decline
    assert standups[0]["emotion_score"] == 70.0
    assert standups[4]["emotion_score"] == 30.0
    
    # Verify pattern detection works
    stuck_info = detect_stuck_pattern(standups)
    assert stuck_info is not None
    assert stuck_info["emotion_delta"] == -40.0


def test_no_pattern_when_emotions_stable(temp_storage):
    """Test that no stuck pattern is detected when emotions are stable."""
    
    for day in range(1, 6):
        standup = {
            "day_number": day,
            "date": f"2026-02-{10+day}",
            "transcript": f"Working on different feature {day}",  # Different topics
            "emotion_score": 75.0,  # Stable emotions
            "dominant_emotion": "happiness",
            "emotions": {}
        }
        temp_storage.save_standup(standup)
    
    standups = temp_storage.get_standups_by_range()
    stuck_info = detect_stuck_pattern(standups)
    
    # Should not detect pattern - no emotion decline
    assert stuck_info is None


def test_scenarios_match_expected_progression():
    """Test that built-in scenarios show expected emotional progression."""
    
    # Get all scenarios
    scenarios = [get_scenario_for_day(i) for i in range(1, 6)]
    
    # Day 1 should be enthusiastic
    assert "started" in scenarios[0]["text"].lower()
    assert "enthusiasm" in scenarios[0]["instructions"].lower()
    
    # Day 5 should show being stuck
    assert "stuck" in scenarios[4]["text"].lower()
    assert "defeated" in scenarios[4]["instructions"].lower()
    
    # All days should mention "auth"
    for scenario in scenarios:
        assert "auth" in scenario["text"].lower()


def test_data_persistence(temp_storage):
    """Test that data persists correctly in JSON storage."""
    
    # Save some data
    standup = {
        "day_number": 1,
        "date": "2026-02-14",
        "transcript": "Test transcript",
        "emotion_score": 75.0,
        "dominant_emotion": "happiness",
        "emotions": {"happiness": 0.75, "sadness": 0.25}
    }
    
    saved = temp_storage.save_standup(standup)
    saved_id = saved["id"]
    
    # Retrieve by ID
    retrieved = temp_storage.get_by_id(saved_id)
    
    assert retrieved is not None
    assert retrieved["transcript"] == "Test transcript"
    assert retrieved["emotion_score"] == 75.0
    assert retrieved["emotions"]["happiness"] == 0.75


if __name__ == "__main__":
    # Run integration test manually
    print("Running integration test...\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StandupStorage(str(Path(tmpdir) / "test.json"))
        test_full_pipeline_with_mocked_data(storage)
