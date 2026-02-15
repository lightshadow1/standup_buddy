"""Unit tests for audio analysis module."""

import pytest

from async_standup.analyze_audio import extract_emotion_data


def test_extract_emotion_data_basic():
    """Test extracting emotion data from a typical API response."""
    api_response = {
        "transcription": "Hello world.",
        "emotions": {
            "happiness": 0.8,
            "sadness": 0.15,
            "disgust": 0.02,
            "fear": 0.03,
            "anger": 0.05
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["transcript"] == "Hello world."
    assert result["dominant_emotion"] == "happiness"
    assert result["emotion_score"] == 80.0
    assert result["emotions"]["happiness"] == 0.8


def test_extract_emotion_data_sadness_dominant():
    """Test when sadness is the dominant emotion."""
    api_response = {
        "transcription": "I'm stuck on this problem.",
        "emotions": {
            "happiness": 0.1,
            "sadness": 0.7,
            "disgust": 0.05,
            "fear": 0.1,
            "anger": 0.05
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["dominant_emotion"] == "sadness"
    assert result["emotion_score"] == 70.0


def test_extract_emotion_data_empty_emotions():
    """Test handling of empty emotions dict."""
    api_response = {
        "transcription": "Test",
        "emotions": {}
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["transcript"] == "Test"
    assert result["dominant_emotion"] == "unknown"
    assert result["emotion_score"] == 0.0
    assert result["emotions"] == {}


def test_extract_emotion_data_missing_transcription():
    """Test handling of missing transcription field."""
    api_response = {
        "emotions": {
            "happiness": 0.5,
            "sadness": 0.5
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["transcript"] == ""
    assert result["dominant_emotion"] in ["happiness", "sadness"]


def test_extract_emotion_data_percentage_conversion():
    """Test that emotion scores are correctly converted to percentages."""
    api_response = {
        "transcription": "Test",
        "emotions": {
            "happiness": 0.654,
            "sadness": 0.346
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["emotion_score"] == 65.4
    assert 0 <= result["emotion_score"] <= 100


def test_extract_emotion_data_preserves_all_emotions():
    """Test that all emotion values are preserved in the result."""
    emotions = {
        "happiness": 0.2,
        "sadness": 0.3,
        "disgust": 0.1,
        "fear": 0.15,
        "anger": 0.25
    }
    
    api_response = {
        "transcription": "Test",
        "emotions": emotions
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["emotions"] == emotions
    assert len(result["emotions"]) == 5


def test_extract_emotion_data_max_emotion():
    """Test that the maximum emotion is correctly identified."""
    api_response = {
        "transcription": "Test",
        "emotions": {
            "happiness": 0.15,
            "sadness": 0.1,
            "disgust": 0.05,
            "fear": 0.95,  # Highest
            "anger": 0.08
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["dominant_emotion"] == "fear"
    assert result["emotion_score"] == 95.0


def test_extract_emotion_data_real_world_example():
    """Test with a realistic example mimicking actual API response."""
    api_response = {
        "status": "success",
        "transcription": "I started working on the auth feature!",
        "words": [
            {"speaker": "speaker_0", "word": "I", "start": 0, "end": 0.1},
            {"speaker": "speaker_0", "word": "started", "start": 0.1, "end": 0.4}
        ],
        "utterances": [
            {
                "text": "I started working on the auth feature!",
                "start": 0,
                "end": 2.5,
                "speaker": "speaker_0"
            }
        ],
        "age": "adult",
        "gender": "male",
        "emotions": {
            "happiness": 0.75,
            "sadness": 0.1,
            "disgust": 0.05,
            "fear": 0.05,
            "anger": 0.05
        },
        "metadata": {
            "filename": "day_1.mp3",
            "duration": 2.5,
            "fileSize": 50000
        }
    }
    
    result = extract_emotion_data(api_response)
    
    assert result["transcript"] == "I started working on the auth feature!"
    assert result["dominant_emotion"] == "happiness"
    assert result["emotion_score"] == 75.0
    assert "happiness" in result["emotions"]
    assert len(result["emotions"]) == 5
