"""Generate full Q&A conversation audio with interviewer and engineer voices.

Uses:
- Smallest.ai Lightning API for interviewer questions (professional, neutral voice)
- OpenAI TTS for engineer answers (with emotional progression)
"""

import os
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

from src.async_standup.conversation_agent import generate_5_day_conversations


# Load environment variables
load_dotenv()


def generate_interviewer_audio_smallest(
    text: str,
    output_file: str,
    voice_id: str = "emily"  # Professional female voice
) -> str:
    """Generate audio for interviewer questions using Smallest.ai Lightning API.
    
    Args:
        text: Question text
        output_file: Path to save audio file
        voice_id: Voice ID (emily, arnav, etc.)
        
    Returns:
        Path to generated audio file
    """
    api_key = os.getenv("SMALLEST_API_KEY") or os.getenv("PULSE_API_KEY")
    if not api_key:
        raise ValueError("SMALLEST_API_KEY or PULSE_API_KEY not found")
    
    url = "https://waves-api.smallest.ai/api/v1/lightning/get_speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "voice_id": voice_id,
        "sample_rate": 24000,
        "add_wav_header": True
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file
    else:
        raise Exception(f"Smallest.ai API error: {response.status_code} - {response.text}")


def generate_engineer_audio_openai(
    text: str,
    output_file: str,
    day: int,
    voice: str = "alloy"
) -> str:
    """Generate audio for engineer answers using OpenAI TTS with emotional instructions.
    
    Args:
        text: Answer text
        output_file: Path to save audio file
        day: Day number (1-5) for emotional progression
        voice: OpenAI voice ID
        
    Returns:
        Path to generated audio file
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    client = OpenAI(api_key=api_key)
    
    # Emotional instructions based on day
    emotional_instructions = {
        1: "Speak with enthusiasm and confidence. You're making good progress and feeling positive.",
        2: "Speak with steady energy and satisfaction. Things are going well.",
        3: "Speak with slight hesitation and uncertainty. You're starting to feel stuck.",
        4: "Speak with frustration and low energy. You're clearly stuck and struggling.",
        5: "Speak with a defeated and discouraged tone. You've been stuck for days and feel overwhelmed."
    }
    
    speech_params = {
        "model": "gpt-4o-mini-tts",
        "voice": voice,
        "input": text,
        "instructions": emotional_instructions.get(day, "")
    }
    
    response = client.audio.speech.create(**speech_params)
    response.stream_to_file(output_file)
    
    return output_file


def combine_audio_files(audio_files: List[str], output_file: str, pause_ms: int = 800) -> str:
    """Combine multiple audio files with pauses between them using ffmpeg.
    
    Args:
        audio_files: List of audio file paths to combine
        output_file: Output file path
        pause_ms: Pause duration in milliseconds between clips
        
    Returns:
        Path to combined audio file
    """
    # Create a concat filter for ffmpeg
    # For each file, add it to the filter_complex with adelay
    
    filter_parts = []
    inputs = []
    
    for i, audio_file in enumerate(audio_files):
        inputs.extend(["-i", audio_file])
        
        # Add delay after each clip except the last
        if i < len(audio_files) - 1:
            # Add adelay in milliseconds
            filter_parts.append(f"[{i}:a]adelay={i * pause_ms}|{i * pause_ms}[a{i}]")
        else:
            filter_parts.append(f"[{i}:a]adelay={i * pause_ms}|{i * pause_ms}[a{i}]")
    
    # Concatenate all processed audio
    concat_input = "".join([f"[a{i}]" for i in range(len(audio_files))])
    filter_parts.append(f"{concat_input}concat=n={len(audio_files)}:v=0:a=1[out]")
    
    filter_complex = ";".join(filter_parts)
    
    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        output_file
    ]
    
    # Run ffmpeg
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"ffmpeg error: {result.stderr}")
    
    return output_file


def generate_full_conversation_audio(
    conversations: List[Dict[str, Any]],
    output_dir: str = "data/full_conversation_audio"
) -> List[str]:
    """Generate full Q&A conversation audio files for all days.
    
    Args:
        conversations: List of daily conversations
        output_dir: Output directory
        
    Returns:
        List of generated audio file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for individual clips
    temp_dir = output_path / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    generated_files = []
    base_date = datetime.now()
    
    for conv_data in conversations:
        day = conv_data["day"]
        conversation = conv_data["conversation"]
        date = (base_date - timedelta(days=5-day)).strftime("%Y-%m-%d")
        
        print(f"\n{'='*70}")
        print(f"Generating Day {day} full conversation audio...")
        print(f"{'='*70}")
        
        # Generate audio for each Q&A exchange
        exchange_files = []
        
        for i, exchange in enumerate(conversation):
            question = exchange["q"]
            answer = exchange["a"]
            
            print(f"\nExchange {i+1}/{len(conversation)}:")
            print(f"  Q: {question[:60]}...")
            print(f"  A: {answer[:60]}...")
            
            # Generate interviewer question audio
            question_file = temp_dir / f"day{day}_q{i+1}.wav"
            print(f"  → Generating interviewer audio (Smallest.ai)...")
            generate_interviewer_audio_smallest(question, str(question_file))
            exchange_files.append(str(question_file))
            
            # Generate engineer answer audio
            answer_file = temp_dir / f"day{day}_a{i+1}.wav"
            print(f"  → Generating engineer audio (OpenAI)...")
            generate_engineer_audio_openai(answer, str(answer_file), day)
            exchange_files.append(str(answer_file))
        
        # Combine all exchanges into one file
        output_file = output_path / f"full_conversation_day_{day}_{date}.mp3"
        print(f"\n  ✓ Combining {len(exchange_files)} audio clips...")
        combine_audio_files(exchange_files, str(output_file), pause_ms=800)
        
        generated_files.append(str(output_file))
        print(f"  ✅ Saved: {output_file}")
    
    # Clean up temp files
    print(f"\n{'='*70}")
    print("Cleaning up temporary files...")
    for temp_file in temp_dir.glob("*"):
        temp_file.unlink()
    temp_dir.rmdir()
    
    return generated_files


if __name__ == "__main__":
    print("=" * 70)
    print("FULL Q&A CONVERSATION AUDIO GENERATOR")
    print("=" * 70)
    print()
    print("Interviewer: Smallest.ai Lightning API (emily voice)")
    print("Engineer: OpenAI TTS (alloy voice with emotional progression)")
    print()
    
    # Step 1: Generate conversations
    print("Step 1: Generating 5-day conversations with GPT-4...")
    print("-" * 70)
    conversations = generate_5_day_conversations()
    print(f"✅ Generated {len(conversations)} conversations\n")
    
    # Step 2: Generate full conversation audio
    print("Step 2: Generating full Q&A audio files...")
    print("-" * 70)
    audio_files = generate_full_conversation_audio(conversations)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Generated {len(audio_files)} full conversation audio files:")
    for f in audio_files:
        print(f"  - {f}")
    print()
    print("🎧 Listen to hear the full Q&A conversations!")
    print("   Interviewer questions → Engineer answers with emotional progression")
    print()
