"""Unit tests for storage module."""

import json
import tempfile
from pathlib import Path

import pytest

from async_standup.storage import StandupStorage


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_standups.json"
        storage = StandupStorage(data_file=str(data_file))
        yield storage


def test_init_creates_empty_file(temp_storage):
    """Test that initialization creates an empty JSON file."""
    assert temp_storage.data_file.exists()
    standups = temp_storage.load_standups()
    assert standups == []


def test_save_standup_generates_id(temp_storage):
    """Test that saving a standup generates an ID."""
    standup = {
        "date": "2026-02-10",
        "day_number": 1,
        "transcript": "Test standup",
        "emotion_score": 65.0,
        "dominant_emotion": "happiness"
    }
    
    saved = temp_storage.save_standup(standup)
    
    assert saved['id'] == 1
    assert 'created_at' in saved


def test_save_multiple_standups(temp_storage):
    """Test saving multiple standups with auto-incrementing IDs."""
    standup1 = {"day_number": 1, "transcript": "Day 1"}
    standup2 = {"day_number": 2, "transcript": "Day 2"}
    
    saved1 = temp_storage.save_standup(standup1)
    saved2 = temp_storage.save_standup(standup2)
    
    assert saved1['id'] == 1
    assert saved2['id'] == 2
    
    all_standups = temp_storage.load_standups()
    assert len(all_standups) == 2


def test_get_standups_by_range(temp_storage):
    """Test filtering standups by day number range."""
    for day in range(1, 6):
        temp_storage.save_standup({
            "day_number": day,
            "transcript": f"Day {day}"
        })
    
    # Test range filtering
    result = temp_storage.get_standups_by_range(start_day=2, end_day=4)
    assert len(result) == 3
    assert result[0]['day_number'] == 2
    assert result[2]['day_number'] == 4


def test_get_standups_by_range_no_bounds(temp_storage):
    """Test getting all standups without range bounds."""
    for day in range(1, 4):
        temp_storage.save_standup({"day_number": day})
    
    result = temp_storage.get_standups_by_range()
    assert len(result) == 3


def test_get_standups_by_range_sorted(temp_storage):
    """Test that results are sorted by day_number."""
    # Save in non-sequential order
    temp_storage.save_standup({"day_number": 3})
    temp_storage.save_standup({"day_number": 1})
    temp_storage.save_standup({"day_number": 2})
    
    result = temp_storage.get_standups_by_range()
    assert result[0]['day_number'] == 1
    assert result[1]['day_number'] == 2
    assert result[2]['day_number'] == 3


def test_clear_storage(temp_storage):
    """Test clearing all standups."""
    temp_storage.save_standup({"day_number": 1})
    temp_storage.save_standup({"day_number": 2})
    
    temp_storage.clear()
    
    standups = temp_storage.load_standups()
    assert len(standups) == 0


def test_get_by_id(temp_storage):
    """Test retrieving a standup by ID."""
    saved = temp_storage.save_standup({
        "day_number": 1,
        "transcript": "Test"
    })
    
    retrieved = temp_storage.get_by_id(saved['id'])
    assert retrieved is not None
    assert retrieved['id'] == saved['id']
    assert retrieved['transcript'] == "Test"


def test_get_by_id_not_found(temp_storage):
    """Test that get_by_id returns None for non-existent ID."""
    result = temp_storage.get_by_id(999)
    assert result is None


def test_preserves_emotion_data(temp_storage):
    """Test that emotion data is preserved correctly."""
    standup = {
        "day_number": 1,
        "transcript": "Test",
        "emotion_score": 80.5,
        "dominant_emotion": "happiness",
        "emotions": {
            "happiness": 0.805,
            "sadness": 0.15,
            "disgust": 0.02,
            "fear": 0.01,
            "anger": 0.015
        }
    }
    
    saved = temp_storage.save_standup(standup)
    retrieved = temp_storage.get_by_id(saved['id'])
    
    assert retrieved['emotion_score'] == 80.5
    assert retrieved['dominant_emotion'] == "happiness"
    assert retrieved['emotions']['happiness'] == 0.805
