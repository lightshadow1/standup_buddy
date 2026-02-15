#!/usr/bin/env python
"""Quick demo script to test AsyncStandup pipeline."""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from async_standup.storage import StandupStorage
from async_standup.generate_audio import generate_audio_files
from async_standup.analyze_audio import process_audio_file
from async_standup.insight_engine import detect_stuck_pattern, generate_insight_message


# Load environment variables
load_dotenv()


def main():
    """Run the AsyncStandup demo."""
    print("=" * 70)
    print("AsyncStandup Demo - Emotion Detection for Standups")
    print("=" * 70)
    print()
    
    # Check API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        return
    
    if not (os.getenv("PULSE_API_KEY") or os.getenv("SMALLEST_API_KEY")):
        print("❌ Error: PULSE_API_KEY or SMALLEST_API_KEY not found in .env file")
        return
    
    print("✅ API keys loaded\n")
    
    # Initialize storage
    storage = StandupStorage("data/standups.json")
    
    # Step 1: Generate audio files
    print("[Step 1/4] Generating audio files with OpenAI TTS...")
    audio_files = generate_audio_files(output_dir="data/audio", voice="alloy")
    print(f"✅ Generated {len(audio_files)} audio files\n")
    
    # Step 2: Analyze audio files and save results
    print("[Step 2/4] Analyzing audio with Smallest.ai Pulse API...")
    base_date = datetime.now()
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"  Processing Day {i}...", end=" ")
        
        # Analyze audio
        result = process_audio_file(audio_file)
        
        # Create standup entry
        standup = {
            "date": (base_date - timedelta(days=5-i)).strftime("%Y-%m-%d"),
            "day_number": i,
            "transcript": result["transcript"],
            "emotion_score": result["emotion_score"],
            "dominant_emotion": result["dominant_emotion"],
            "emotions": result["emotions"]
        }
        
        # Save to storage
        storage.save_standup(standup)
        
        print(f"✅ {result['dominant_emotion'].capitalize()} ({result['emotion_score']:.1f}%)")
    
    print()
    
    # Step 3: Detect stuck patterns
    print("[Step 3/4] Analyzing for stuck patterns...")
    standups = storage.get_standups_by_range(start_day=1, end_day=5)
    stuck_info = detect_stuck_pattern(standups)
    
    if stuck_info:
        print(f"⚠️  Stuck pattern detected!")
        print(f"   Keyword: '{stuck_info['repeated_keyword']}'")
        print(f"   Occurrences: {stuck_info['keyword_count']} days")
        print(f"   Emotion change: {stuck_info['emotion_delta']:.1f} points")
    else:
        print("ℹ️  No stuck pattern detected")
    
    print()
    
    # Step 4: Display results
    print("[Step 4/4] Displaying emotion progression...")
    print()
    print("=" * 70)
    print("📊 STANDUP EMOTION TIMELINE")
    print("=" * 70)
    print()
    
    for standup in standups:
        day = standup['day_number']
        emotion = standup['dominant_emotion']
        score = standup['emotion_score']
        transcript = standup['transcript']
        
        # Choose emoji based on emotion score
        if score >= 70:
            emoji = "😊"
        elif score >= 50:
            emoji = "😐"
        elif score >= 30:
            emoji = "😟"
        else:
            emoji = "😢"
        
        # Progress bar
        bar_length = int(score / 2)  # Max 50 chars
        bar = "█" * bar_length + "░" * (50 - bar_length)
        
        print(f"Day {day} | {emoji} {emotion.capitalize():10} | {score:5.1f}%")
        print(f"      | {bar}")
        print(f"      | \"{transcript}\"")
        print()
    
    # Show insight message
    print("=" * 70)
    print("💡 INSIGHTS")
    print("=" * 70)
    print()
    
    message = generate_insight_message(stuck_info)
    print(message)
    print()
    
    print("=" * 70)
    print("✅ Demo completed successfully!")
    print("=" * 70)
    print()
    print(f"Data saved to: {storage.data_file}")


if __name__ == "__main__":
    main()
