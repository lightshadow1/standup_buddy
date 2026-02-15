"""Audio generation module using OpenAI TTS."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables
load_dotenv()


# Standup scenarios with emotional progression
STANDUP_SCENARIOS: List[Dict[str, str]] = [
    {
        "day": 1,
        "text": "I started working on the auth feature!",
        "instructions": "Speak with enthusiasm and excitement, like you're starting something new and you're really happy about it.",
    },
    {
        "day": 2,
        "text": "Making progress on auth, got login working.",
        "instructions": "Speak with moderate energy and satisfaction, showing steady progress.",
    },
    {
        "day": 3,
        "text": "Still on auth... token refresh is tricky.",
        "instructions": "Speak with slight uncertainty and concern, energy is lower than before.",
    },
    {
        "day": 4,
        "text": "Stuck on auth, can't figure out token expiration.",
        "instructions": "Speak with frustration and low energy, showing you're struggling and stuck.",
    },
    {
        "day": 5,
        "text": "Still stuck on auth... been three days now.",
        "instructions": "Speak with a defeated and sad tone, very low energy, feeling discouraged.",
    },
]


def generate_audio_files(
    output_dir: str = "data/audio",
    voice: str = "alloy",
    model: str = "gpt-4o-mini-tts"
) -> List[str]:
    """Generate 5 days of standup audio files using OpenAI TTS.
    
    Args:
        output_dir: Directory to save audio files
        voice: OpenAI TTS voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: TTS model to use (tts-1 or tts-1-hd)
        
    Returns:
        List of generated file paths
    """
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=api_key)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    
    # Calculate dates (5 consecutive days starting from today)
    base_date = datetime.now()
    
    for scenario in STANDUP_SCENARIOS:
        day_num = scenario["day"]
        date = (base_date - timedelta(days=5-day_num)).strftime("%Y-%m-%d")
        
        # Generate filename
        filename = f"day_{day_num}_{date}.mp3"
        filepath = output_path / filename
        
        # Skip if file already exists
        if filepath.exists():
            print(f"✓ Audio file already exists: {filepath}")
            generated_files.append(str(filepath))
            continue
        
        print(f"Generating audio for Day {day_num}: {scenario['text']}")
        
        # Generate speech using OpenAI TTS with emotional instructions
        speech_params = {
            "model": model,
            "voice": voice,
            "input": scenario["text"]
        }
        
        # Add instructions for gpt-4o-mini-tts model
        if model == "gpt-4o-mini-tts" and "instructions" in scenario:
            speech_params["instructions"] = scenario["instructions"]
        
        response = client.audio.speech.create(**speech_params)
        
        # Save audio file
        response.stream_to_file(filepath)
        
        print(f"✓ Generated: {filepath}")
        generated_files.append(str(filepath))
    
    return generated_files


def get_scenario_for_day(day: int) -> Dict[str, str]:
    """Get standup scenario for a specific day.
    
    Args:
        day: Day number (1-5)
        
    Returns:
        Scenario dictionary
        
    Raises:
        ValueError: If day is out of range
    """
    if day < 1 or day > 5:
        raise ValueError(f"Day must be between 1 and 5, got {day}")
    
    return STANDUP_SCENARIOS[day - 1]


if __name__ == "__main__":
    # Generate audio files when run directly
    print("Generating standup audio files...")
    files = generate_audio_files()
    print(f"\nGenerated {len(files)} audio files:")
    for f in files:
        print(f"  - {f}")
