"""Unit tests for insight engine module."""

import pytest

from async_standup.insight_engine import (
    extract_keywords,
    find_repeated_keywords,
    calculate_emotion_delta,
    detect_stuck_pattern,
    generate_insight_message
)


def test_extract_keywords_basic():
    """Test basic keyword extraction."""
    text = "I started working on the auth feature"
    keywords = extract_keywords(text)
    
    assert "started" in keywords
    assert "working" in keywords
    assert "auth" in keywords
    assert "feature" in keywords
    # Stop words should be filtered
    assert "the" not in keywords
    assert "on" not in keywords


def test_extract_keywords_removes_short_words():
    """Test that short words are filtered."""
    text = "I am on it now"
    keywords = extract_keywords(text, min_length=3)
    
    # All words are too short or stop words
    assert len(keywords) == 0


def test_extract_keywords_case_insensitive():
    """Test that keywords are lowercased."""
    text = "Auth AUTH authentication"
    keywords = extract_keywords(text)
    
    assert all(kw.islower() for kw in keywords)
    assert "auth" in keywords
    assert "authentication" in keywords


def test_find_repeated_keywords():
    """Test finding repeated keywords across multiple standups."""
    standups = [
        {"transcript": "Working on auth feature"},
        {"transcript": "Still working on auth"},
        {"transcript": "Auth is taking longer"},
    ]
    
    repeated = find_repeated_keywords(standups, min_occurrences=3)
    
    assert len(repeated) > 0
    # 'auth' appears in all 3 standups
    auth_entry = next((kw for kw, cnt in repeated if kw == "auth"), None)
    assert auth_entry is not None
    
    # Check that it's sorted by count
    if len(repeated) > 1:
        assert repeated[0][1] >= repeated[1][1]


def test_find_repeated_keywords_no_repeats():
    """Test when no keywords repeat enough times."""
    standups = [
        {"transcript": "Working on login"},
        {"transcript": "Fixed the database"},
        {"transcript": "Updated the docs"},
    ]
    
    repeated = find_repeated_keywords(standups, min_occurrences=3)
    
    assert len(repeated) == 0


def test_calculate_emotion_delta():
    """Test emotion delta calculation."""
    standups = [
        {"day_number": 1, "emotion_score": 75.0},
        {"day_number": 2, "emotion_score": 60.0},
        {"day_number": 3, "emotion_score": 50.0},
    ]
    
    delta = calculate_emotion_delta(standups, baseline_day=1)
    
    assert delta == -25.0  # 50.0 - 75.0


def test_calculate_emotion_delta_improvement():
    """Test emotion delta when emotion improves."""
    standups = [
        {"day_number": 1, "emotion_score": 50.0},
        {"day_number": 2, "emotion_score": 75.0},
    ]
    
    delta = calculate_emotion_delta(standups)
    
    assert delta == 25.0  # Positive delta = improvement


def test_calculate_emotion_delta_empty():
    """Test emotion delta with empty list."""
    delta = calculate_emotion_delta([])
    assert delta == 0.0


def test_detect_stuck_pattern_positive():
    """Test stuck pattern detection when pattern exists."""
    standups = [
        {
            "day_number": 1,
            "transcript": "Started working on auth feature",
            "emotion_score": 75.0
        },
        {
            "day_number": 2,
            "transcript": "Still on auth, got login working",
            "emotion_score": 60.0
        },
        {
            "day_number": 3,
            "transcript": "Auth token refresh is tricky",
            "emotion_score": 50.0
        },
        {
            "day_number": 4,
            "transcript": "Stuck on auth token expiration",
            "emotion_score": 40.0
        },
        {
            "day_number": 5,
            "transcript": "Still stuck on auth issues",
            "emotion_score": 35.0
        }
    ]
    
    result = detect_stuck_pattern(standups)
    
    assert result is not None
    assert result["is_stuck"] is True
    assert result["repeated_keyword"] == "auth"
    assert result["keyword_count"] == 5
    assert result["emotion_delta"] < -10
    assert "pairing" in result["recommendation"].lower()


def test_detect_stuck_pattern_no_keyword_repeat():
    """Test when keywords don't repeat enough."""
    standups = [
        {"day_number": 1, "transcript": "Working on login", "emotion_score": 75.0},
        {"day_number": 2, "transcript": "Fixed the database", "emotion_score": 60.0},
        {"day_number": 3, "transcript": "Updated the docs", "emotion_score": 50.0},
    ]
    
    result = detect_stuck_pattern(standups)
    
    assert result is None


def test_detect_stuck_pattern_no_emotion_decline():
    """Test when emotion doesn't decline enough."""
    standups = [
        {"day_number": 1, "transcript": "Working on auth", "emotion_score": 75.0},
        {"day_number": 2, "transcript": "Still on auth", "emotion_score": 74.0},
        {"day_number": 3, "transcript": "Auth progressing", "emotion_score": 73.0},
    ]
    
    result = detect_stuck_pattern(standups)
    
    assert result is None


def test_detect_stuck_pattern_too_few_days():
    """Test with insufficient data (< 3 days)."""
    standups = [
        {"day_number": 1, "transcript": "Working on auth", "emotion_score": 75.0},
        {"day_number": 2, "transcript": "Still on auth", "emotion_score": 40.0},
    ]
    
    result = detect_stuck_pattern(standups)
    
    assert result is None


def test_generate_insight_message_with_stuck_pattern():
    """Test message generation for stuck pattern."""
    stuck_info = {
        "is_stuck": True,
        "repeated_keyword": "auth",
        "keyword_count": 5,
        "emotion_delta": -40.0,
        "days_affected": 5,
        "recommendation": "Consider pairing session or escalation"
    }
    
    message = generate_insight_message(stuck_info)
    
    assert "⚠️" in message
    assert "auth" in message
    assert "5 consecutive days" in message
    assert "40.0 percentage points" in message
    assert "pairing session" in message


def test_generate_insight_message_no_pattern():
    """Test message generation when no pattern detected."""
    message = generate_insight_message(None)
    
    assert "No stuck pattern detected" in message


def test_generate_insight_message_not_stuck():
    """Test message when stuck flag is False."""
    stuck_info = {"is_stuck": False}
    
    message = generate_insight_message(stuck_info)
    
    assert "No stuck pattern detected" in message


def test_edge_case_all_same_transcript():
    """Test with all identical transcripts."""
    standups = [
        {"day_number": i, "transcript": "Working on auth", "emotion_score": 75.0 - i*10}
        for i in range(1, 6)
    ]
    
    result = detect_stuck_pattern(standups)
    
    # Should detect pattern: repeated 'auth' + emotion decline
    assert result is not None
    assert result["is_stuck"] is True


def test_keyword_extraction_with_punctuation():
    """Test keyword extraction handles punctuation correctly."""
    text = "Working on auth... can't figure out token!"
    keywords = extract_keywords(text)
    
    assert "working" in keywords
    assert "auth" in keywords
    assert "figure" in keywords
    assert "token" in keywords
