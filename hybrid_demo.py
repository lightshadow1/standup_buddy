"""Hybrid demo: Conversational + Emotional Stuck Detection.

Pipeline:
1. GPT-4 generates realistic 5-day conversations
2. Convert conversations to audio using OpenAI TTS
3. Pulse API transcribes audio and extracts emotions
4. GPT-4 analyzes conversations for conversational signals
5. Calculate hybrid stuck probability (70% conv + 30% emotion)
6. Display results with detailed breakdown
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

from src.async_standup.conversation_agent import (
    generate_5_day_conversations,
    analyze_conversation
)
from src.async_standup.analyze_audio import process_audio_file
from src.async_standup.insight_engine import (
    calculate_stuck_probability,
    format_hybrid_insight
)
from src.async_standup.storage import StandupStorage
from generate_conversation_audio import generate_audio_from_conversations


# Load environment variables
load_dotenv()


def conversation_to_text(conversation: List[Dict[str, str]]) -> str:
    """Convert a conversation (Q&A list) to a single text string.
    
    Args:
        conversation: List of Q&A exchanges
        
    Returns:
        Full conversation as text (answers only)
    """
    return " ".join([exchange["a"] for exchange in conversation])


def run_hybrid_demo(
    output_dir: str = "data/hybrid_demo",
    save_to_storage: bool = True
) -> List[Dict[str, Any]]:
    """Run the full hybrid stuck detection pipeline.
    
    Args:
        output_dir: Directory for audio files and results
        save_to_storage: Whether to save results to JSON storage
        
    Returns:
        List of daily results with all signals and stuck probability
    """
    print("=" * 80)
    print("ASYNCSTANDUP HYBRID DEMO: Conversational + Emotional Stuck Detection")
    print("=" * 80)
    print()
    
    # Initialize storage
    storage = None
    if save_to_storage:
        storage_path = Path(output_dir) / "hybrid_standups.json"
        storage = StandupStorage(str(storage_path))
        storage.clear()  # Clear previous data
    
    # Step 1: Generate conversations with GPT-4
    print("Step 1: Generating realistic 5-day conversations with GPT-4...")
    print("-" * 80)
    conversations = generate_5_day_conversations()
    print(f"✅ Generated {len(conversations)} conversations\n")
    
    # Step 2: Generate audio from conversations
    print("Step 2: Converting conversations to audio with OpenAI TTS...")
    print("-" * 80)
    audio_dir = Path(output_dir) / "audio"
    audio_files = generate_audio_from_conversations(
        conversations,
        output_dir=str(audio_dir)
    )
    print(f"✅ Generated {len(audio_files)} audio files\n")
    
    # Step 3: Analyze audio with Pulse API
    print("Step 3: Analyzing audio with Pulse API (transcription + emotions)...")
    print("-" * 80)
    results = []
    base_date = datetime.now()
    
    for conv_data, audio_file in zip(conversations, audio_files):
        day = conv_data["day"]
        conversation = conv_data["conversation"]
        date = (base_date - timedelta(days=5-day)).strftime("%Y-%m-%d")
        
        print(f"Processing Day {day}...")
        
        # Analyze audio with Pulse API
        pulse_result = process_audio_file(audio_file)
        transcript = pulse_result.get("transcript", "")
        emotions = pulse_result.get("emotions", {})
        emotion_score = pulse_result.get("emotion_score", 0.0)
        dominant_emotion = pulse_result.get("dominant_emotion", "neutral")
        
        print(f"  ✓ Pulse: {dominant_emotion} ({emotion_score:.1f}%), {len(transcript)} chars transcribed")
        
        # Step 4: Analyze conversation with GPT-4
        conversational_signals = analyze_conversation(conversation)
        
        print(f"  ✓ GPT-4: vagueness={conversational_signals.get('vagueness_score', 0):.2f}, "
              f"hedging={conversational_signals.get('hedging_count', 0)}")
        
        # Step 5: Calculate hybrid stuck probability
        stuck_result = calculate_stuck_probability(
            conversational_signals=conversational_signals,
            emotions=emotions
        )
        
        stuck_prob = stuck_result['stuck_probability']
        status = stuck_result['status']
        
        print(f"  ✓ Hybrid: {stuck_prob:.1%} ({status})\n")
        
        # Compile results
        result = {
            "day_number": day,
            "date": date,
            "conversation": conversation,
            "transcript": transcript,
            "emotion_score": emotion_score,
            "dominant_emotion": dominant_emotion,
            "emotions": emotions,
            "conversational_signals": conversational_signals,
            "stuck_probability": stuck_prob,
            "stuck_status": status,
            "audio_file": audio_file
        }
        
        results.append(result)
        
        # Save to storage if enabled
        if storage:
            storage.save_standup(result)
    
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()
    
    # Display detailed results
    for result in results:
        day = result["day_number"]
        stuck_result = {
            'stuck_probability': result['stuck_probability'],
            'conversational_score': calculate_stuck_probability(
                conversational_signals=result['conversational_signals']
            )['conversational_score'],
            'emotional_score': calculate_stuck_probability(
                emotions=result['emotions']
            )['emotional_score'],
            'status': result['stuck_status'],
            'breakdown': calculate_stuck_probability(
                conversational_signals=result['conversational_signals'],
                emotions=result['emotions']
            )['breakdown']
        }
        
        insight = format_hybrid_insight(
            day=day,
            stuck_probability=stuck_result['stuck_probability'],
            conversational_score=stuck_result['conversational_score'],
            emotional_score=stuck_result['emotional_score'],
            status=stuck_result['status'],
            breakdown=stuck_result['breakdown']
        )
        
        print(insight)
        print()
    
    # Overall summary
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    
    # Track progression
    day1 = results[0]
    day5 = results[4]
    
    print(f"Progression from Day 1 → Day 5:")
    print(f"  Stuck Probability: {day1['stuck_probability']:.1%} → {day5['stuck_probability']:.1%}")
    print(f"  Status: {day1['stuck_status']} → {day5['stuck_status']}")
    print(f"  Emotion: {day1['dominant_emotion']} ({day1['emotion_score']:.1f}%) → "
          f"{day5['dominant_emotion']} ({day5['emotion_score']:.1f}%)")
    print(f"  Vagueness: {day1['conversational_signals'].get('vagueness_score', 0):.2f} → "
          f"{day5['conversational_signals'].get('vagueness_score', 0):.2f}")
    print(f"  Hedging: {day1['conversational_signals'].get('hedging_count', 0)} → "
          f"{day5['conversational_signals'].get('hedging_count', 0)}")
    print()
    
    # Recommendations
    stuck_days = [r for r in results if r['stuck_status'] == 'stuck']
    warning_days = [r for r in results if r['stuck_status'] == 'warning']
    
    if stuck_days:
        print(f"🚨 {len(stuck_days)} day(s) showing STUCK pattern - immediate intervention recommended")
    if warning_days:
        print(f"⚠️  {len(warning_days)} day(s) showing WARNING signs - monitor closely")
    if not stuck_days and not warning_days:
        print("✅ All days on track - no intervention needed")
    
    print()
    
    if save_to_storage:
        print(f"💾 Data saved to: {storage.data_file}")
    
    print(f"🎵 Audio files saved to: {audio_dir}")
    print()
    
    return results


if __name__ == "__main__":
    try:
        results = run_hybrid_demo()
        print("=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
