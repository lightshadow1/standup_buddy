"""Pulse API integration for audio transcription and emotion detection."""

import os
from pathlib import Path
from typing import Dict, Any

import httpx
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


PULSE_API_URL = "https://waves-api.smallest.ai/api/v1/pulse/get_text"


def analyze_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Analyze audio file using Smallest.ai Pulse API.
    
    Args:
        audio_file_path: Path to audio file
        
    Returns:
        Dictionary containing transcription and emotion data
        
    Raises:
        ValueError: If API key is missing
        httpx.HTTPError: If API request fails
    """
    # Support both PULSE_API_KEY and SMALLEST_API_KEY
    api_key = os.getenv("PULSE_API_KEY") or os.getenv("SMALLEST_API_KEY")
    if not api_key:
        raise ValueError("PULSE_API_KEY or SMALLEST_API_KEY not found in environment variables")
    
    # Read audio file
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Make API request with emotion detection enabled
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/octet-stream"
    }
    
    # Enable emotion detection via query parameter
    params = {
        "emotion_detection": "true"
    }
    
    response = httpx.post(
        PULSE_API_URL,
        headers=headers,
        params=params,
        content=audio_data,
        timeout=30.0
    )
    
    response.raise_for_status()
    
    return response.json()


def extract_emotion_data(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract emotion data from Pulse API response.
    
    Args:
        api_response: Raw API response from Pulse
        
    Returns:
        Dictionary with:
            - transcript: Transcribed text
            - emotions: Dict of emotion scores (0.0-1.0)
            - dominant_emotion: Emotion with highest score
            - emotion_score: Dominant emotion score as percentage (0-100)
    """
    # Extract transcription
    transcript = api_response.get("transcription", "")
    
    # Extract emotions
    emotions = api_response.get("emotions", {})
    
    # Find dominant emotion
    if emotions:
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        emotion_name = dominant_emotion[0]
        emotion_value = dominant_emotion[1]
    else:
        emotion_name = "unknown"
        emotion_value = 0.0
    
    # Convert to percentage
    emotion_score = emotion_value * 100
    
    return {
        "transcript": transcript,
        "emotions": emotions,
        "dominant_emotion": emotion_name,
        "emotion_score": emotion_score
    }


def process_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Process audio file: transcribe and extract emotions.
    
    This is a convenience function that combines API call and data extraction.
    
    Args:
        audio_file_path: Path to audio file
        
    Returns:
        Dictionary with transcript and emotion data
    """
    api_response = analyze_audio_file(audio_file_path)
    return extract_emotion_data(api_response)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_audio.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    print(f"Analyzing {audio_file}...")
    
    result = process_audio_file(audio_file)
    
    print(f"\nTranscript: {result['transcript']}")
    print(f"Dominant Emotion: {result['dominant_emotion']} ({result['emotion_score']:.1f}%)")
    print(f"\nAll Emotions:")
    for emotion, score in result['emotions'].items():
        print(f"  {emotion}: {score*100:.1f}%")
