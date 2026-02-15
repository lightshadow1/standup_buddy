"""Generate audio files from GPT-4 generated conversations using OpenAI TTS."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

from src.async_standup.conversation_agent import generate_5_day_conversations


# Load environment variables
load_dotenv()


def conversation_to_text(conversation: List[Dict[str, str]]) -> str:
    """Convert a conversation (Q&A list) to a single text string.
    
    Args:
        conversation: List of Q&A exchanges
        
    Returns:
        Full conversation as text (answers only)
    """
    # Join all answers into one narrative
    return " ".join([exchange["a"] for exchange in conversation])


def generate_audio_from_conversations(
    conversations: List[Dict[str, Any]],
    output_dir: str = "data/conversation_audio",
    voice: str = "alloy",
    model: str = "gpt-4o-mini-tts"
) -> List[str]:
    """Generate audio files from conversation data using OpenAI TTS.
    
    Args:
        conversations: List of daily conversations with metadata
        output_dir: Directory to save audio files
        voice: OpenAI TTS voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: TTS model to use (tts-1, tts-1-hd, gpt-4o-mini-tts)
        
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
    
    # Emotional instructions based on day progression
    emotional_instructions = {
        1: "Speak with enthusiasm and confidence. You're making good progress and feeling positive.",
        2: "Speak with steady energy and satisfaction. Things are going well.",
        3: "Speak with slight hesitation and uncertainty. You're starting to feel stuck.",
        4: "Speak with frustration and low energy. You're clearly stuck and struggling.",
        5: "Speak with a defeated and discouraged tone. You've been stuck for days and feel overwhelmed."
    }
    
    for conv_data in conversations:
        day = conv_data["day"]
        conversation = conv_data["conversation"]
        date = (base_date - timedelta(days=5-day)).strftime("%Y-%m-%d")
        
        # Convert conversation to text
        text = conversation_to_text(conversation)
        
        # Generate filename
        filename = f"conversation_day_{day}_{date}.mp3"
        filepath = output_path / filename
        
        # Skip if file already exists
        if filepath.exists():
            print(f"✓ Audio file already exists: {filepath}")
            generated_files.append(str(filepath))
            continue
        
        print(f"Generating audio for Day {day}...")
        print(f"  Text preview: {text[:100]}...")
        
        # Generate speech using OpenAI TTS with emotional instructions
        speech_params = {
            "model": model,
            "voice": voice,
            "input": text
        }
        
        # Add instructions for gpt-4o-mini-tts model
        if model == "gpt-4o-mini-tts":
            speech_params["instructions"] = emotional_instructions.get(day, "")
        
        response = client.audio.speech.create(**speech_params)
        
        # Save audio file
        response.stream_to_file(filepath)
        
        print(f"✓ Generated: {filepath}")
        generated_files.append(str(filepath))
    
    return generated_files


if __name__ == "__main__":
    print("=" * 70)
    print("Generate Audio from Conversations")
    print("=" * 70)
    print()
    
    # Step 1: Generate conversations
    print("Step 1: Generating 5 days of conversations with GPT-4...")
    conversations = generate_5_day_conversations()
    print(f"✅ Generated {len(conversations)} conversations\n")
    
    # Display conversation previews
    print("Conversation previews:")
    for conv in conversations:
        day = conv["day"]
        text = conversation_to_text(conv["conversation"])
        print(f"  Day {day}: {text[:80]}...")
    print()
    
    # Step 2: Generate audio
    print("Step 2: Generating audio files from conversations...")
    audio_files = generate_audio_from_conversations(conversations)
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ Generated {len(audio_files)} audio files:")
    for f in audio_files:
        print(f"  - {f}")
    print()
    print("Next steps:")
    print("  1. Play the audio files to hear the progression")
    print("  2. Send them to Pulse API for transcription + emotion detection")
    print("  3. Analyze with GPT-4 for conversational signals")
    print("  4. Calculate hybrid stuck probability (70% conv + 30% emotion)")
