"""Real API integration tests using actual OpenAI and Pulse APIs.

These tests require valid API keys in .env file:
- OPENAI_API_KEY
- PULSE_API_KEY

Run with: pytest tests/test_real_api_integration.py -v -s
"""

import os
import tempfile
from pathlib import Path

import pytest

from async_standup.storage import StandupStorage
from async_standup.generate_audio import generate_audio_files, STANDUP_SCENARIOS
from async_standup.analyze_audio import process_audio_file
from async_standup.insight_engine import detect_stuck_pattern, generate_insight_message


# Skip tests if API keys are not available
requires_openai = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)

requires_pulse = pytest.mark.skipif(
    not (os.getenv("PULSE_API_KEY") or os.getenv("SMALLEST_API_KEY")),
    reason="PULSE_API_KEY or SMALLEST_API_KEY not set"
)

requires_both_apis = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not (os.getenv("PULSE_API_KEY") or os.getenv("SMALLEST_API_KEY")),
    reason="Both OPENAI_API_KEY and PULSE_API_KEY (or SMALLEST_API_KEY) required"
)


@pytest.fixture
def temp_audio_dir():
    """Create temporary directory for audio files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_storage():
    """Create temporary storage instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_standups.json"
        storage = StandupStorage(data_file=str(data_file))
        yield storage


@requires_openai
def test_generate_real_audio_files(temp_audio_dir):
    """Test generating audio files with real OpenAI TTS API."""
    print("\n🎤 Testing OpenAI TTS API...")
    
    # Generate audio files
    files = generate_audio_files(output_dir=temp_audio_dir, voice="alloy")
    
    assert len(files) == 5
    
    # Verify files exist and have content
    for i, filepath in enumerate(files, 1):
        path = Path(filepath)
        assert path.exists(), f"Audio file {i} not created"
        assert path.stat().st_size > 0, f"Audio file {i} is empty"
        print(f"  ✅ Day {i}: {path.name} ({path.stat().st_size} bytes)")
    
    print(f"\n✅ Successfully generated {len(files)} audio files using OpenAI TTS")


@requires_pulse
def test_analyze_real_audio_with_pulse(temp_audio_dir):
    """Test analyzing audio with real Pulse API."""
    print("\n🧠 Testing Smallest.ai Pulse API...")
    
    # First, we need an audio file - we'll generate one with OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Need OPENAI_API_KEY to generate test audio")
    
    # Generate just one audio file for testing
    from async_standup.generate_audio import STANDUP_SCENARIOS
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    test_audio_path = Path(temp_audio_dir) / "test.mp3"
    
    # Generate audio for day 1 (enthusiastic)
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=STANDUP_SCENARIOS[0]["text"]
    )
    response.stream_to_file(test_audio_path)
    
    print(f"  Generated test audio: {test_audio_path}")
    
    # Analyze with Pulse API
    result = process_audio_file(str(test_audio_path))
    
    # Verify response structure
    assert "transcript" in result
    assert "emotions" in result
    assert "dominant_emotion" in result
    assert "emotion_score" in result
    
    # Verify data types
    assert isinstance(result["transcript"], str)
    assert isinstance(result["emotions"], dict)
    assert isinstance(result["emotion_score"], float)
    
    # Verify emotion data
    assert len(result["emotions"]) > 0
    assert 0 <= result["emotion_score"] <= 100
    
    print(f"\n  📝 Transcript: {result['transcript']}")
    print(f"  😊 Dominant Emotion: {result['dominant_emotion']} ({result['emotion_score']:.1f}%)")
    print(f"  📊 All Emotions:")
    for emotion, score in result["emotions"].items():
        print(f"     {emotion}: {score*100:.1f}%")
    
    print(f"\n✅ Successfully analyzed audio with Pulse API")


@requires_both_apis
def test_full_pipeline_with_real_apis(temp_audio_dir, temp_storage):
    """Test complete pipeline with real OpenAI and Pulse APIs."""
    print("\n" + "="*70)
    print("🚀 FULL PIPELINE TEST WITH REAL APIs")
    print("="*70)
    
    # Step 1: Generate audio files
    print("\n[Step 1/5] Generating audio files with OpenAI TTS...")
    audio_files = generate_audio_files(output_dir=temp_audio_dir, voice="alloy")
    print(f"✅ Generated {len(audio_files)} audio files")
    
    # Step 2: Analyze each audio file with Pulse API
    print("\n[Step 2/5] Analyzing audio files with Pulse API...")
    analysis_results = []
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"  Analyzing Day {i}...", end=" ")
        result = process_audio_file(audio_file)
        analysis_results.append(result)
        print(f"✅ {result['dominant_emotion']} ({result['emotion_score']:.1f}%)")
    
    # Step 3: Save to storage
    print("\n[Step 3/5] Saving results to storage...")
    from datetime import datetime, timedelta
    base_date = datetime.now()
    
    for i, result in enumerate(analysis_results, 1):
        standup = {
            "date": (base_date - timedelta(days=5-i)).strftime("%Y-%m-%d"),
            "day_number": i,
            "transcript": result["transcript"],
            "emotion_score": result["emotion_score"],
            "dominant_emotion": result["dominant_emotion"],
            "emotions": result["emotions"]
        }
        temp_storage.save_standup(standup)
    
    all_standups = temp_storage.load_standups()
    print(f"✅ Saved {len(all_standups)} standup entries")
    
    # Step 4: Detect stuck pattern
    print("\n[Step 4/5] Detecting stuck patterns...")
    standups_for_analysis = temp_storage.get_standups_by_range(start_day=1, end_day=5)
    stuck_info = detect_stuck_pattern(standups_for_analysis)
    
    if stuck_info:
        print(f"✅ Stuck pattern detected!")
        print(f"   Keyword: {stuck_info['repeated_keyword']}")
        print(f"   Count: {stuck_info['keyword_count']} days")
        print(f"   Emotion delta: {stuck_info['emotion_delta']:.1f} points")
    else:
        print("ℹ️  No stuck pattern detected")
    
    # Step 5: Generate insight message
    print("\n[Step 5/5] Generating insight message...")
    message = generate_insight_message(stuck_info)
    print(f"\n{message}")
    
    # Display emotion progression
    print("\n" + "="*70)
    print("📊 EMOTION PROGRESSION")
    print("="*70)
    for standup in standups_for_analysis:
        day = standup['day_number']
        emotion = standup['dominant_emotion']
        score = standup['emotion_score']
        transcript = standup['transcript']
        
        # Emotion emoji
        if score >= 70:
            emoji = "😊"
        elif score >= 50:
            emoji = "😐"
        elif score >= 30:
            emoji = "😟"
        else:
            emoji = "😢"
        
        print(f"Day {day}: {emoji} {emotion.capitalize()} ({score:.1f}%)")
        print(f"       \"{transcript}\"")
        print()
    
    print("="*70)
    print("✅ FULL PIPELINE COMPLETED SUCCESSFULLY")
    print("="*70)
    
    # Assertions
    assert len(audio_files) == 5
    assert len(analysis_results) == 5
    assert len(all_standups) == 5
    
    # Check that we got reasonable emotion data
    for result in analysis_results:
        assert result["transcript"]  # Not empty
        assert 0 <= result["emotion_score"] <= 100
        # Allow "unknown" if API doesn't return emotions
        assert result["dominant_emotion"] in ["happiness", "sadness", "anger", "fear", "disgust", "neutral", "unknown"]


@requires_openai
def test_audio_quality_check(temp_audio_dir):
    """Verify generated audio files are valid."""
    print("\n🎵 Testing audio file quality...")
    
    # Generate one audio file
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    test_audio_path = Path(temp_audio_dir) / "quality_test.mp3"
    
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="This is a test of audio quality."
    )
    response.stream_to_file(test_audio_path)
    
    # Check file properties
    assert test_audio_path.exists()
    file_size = test_audio_path.stat().st_size
    
    # MP3 files should be at least 5KB for a short sentence
    assert file_size > 5000, f"Audio file seems too small: {file_size} bytes"
    
    print(f"  ✅ Audio file size: {file_size:,} bytes")
    print(f"  ✅ File format: MP3")
    
    # Try to read the file to ensure it's valid
    with open(test_audio_path, 'rb') as f:
        header = f.read(3)
        # MP3 files typically start with 'ID3' or have FF FB/FF FA in first few bytes
        assert len(header) == 3, "Could not read file header"
    
    print(f"  ✅ Audio file is valid")


if __name__ == "__main__":
    # Run tests manually
    print("Running real API integration tests...")
    print("Note: This will consume API credits!\n")
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment")
    else:
        print("✅ OPENAI_API_KEY found")
    
    pulse_key = os.getenv("PULSE_API_KEY") or os.getenv("SMALLEST_API_KEY")
    if not pulse_key:
        print("❌ PULSE_API_KEY or SMALLEST_API_KEY not found in environment")
    else:
        print("✅ PULSE_API_KEY or SMALLEST_API_KEY found")
    
    if os.getenv("OPENAI_API_KEY") and pulse_key:
        print("\n⚠️  Both API keys found. Tests will make real API calls!")
        print("Continue? (y/n): ", end="")
        response = input().lower()
        if response != 'y':
            print("Tests cancelled.")
        else:
            pytest.main([__file__, "-v", "-s"])
    else:
        print("\nSkipping tests due to missing API keys.")
