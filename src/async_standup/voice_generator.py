"""Voice generation module for AsyncStandup voice demo.

Generates audio for:
- Interviewer questions (Smallest.ai Lightning API)
- Persona responses (OpenAI TTS with emotional instructions)
"""

import os
import time
from typing import Dict, Tuple

import requests
from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables
load_dotenv()


def generate_interviewer_audio(text: str, voice: str = "emily", max_retries: int = 3) -> bytes:
    """Generate interviewer question using Smallest.ai Lightning API.
    
    Args:
        text: Question text to convert to speech
        voice: Voice ID from Smallest.ai Lightning (default: emily)
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Audio data as bytes (audio format)
        
    Raises:
        ValueError: If SMALLEST_API_KEY not found
        Exception: If API call fails after all retries
    """
    api_key = os.getenv("SMALLEST_API_KEY") or os.getenv("PULSE_API_KEY")
    if not api_key:
        raise ValueError("SMALLEST_API_KEY or PULSE_API_KEY not found in environment variables")
    
    url = "https://waves-api.smallest.ai/api/v1/lightning/get_speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "voice_id": voice,
        "sample_rate": 24000,
        "add_wav_header": True
    }
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Set timeout to prevent hanging connections
            response = requests.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=30,  # 30 second timeout
                stream=False  # Don't stream, get full response
            )
            
            if response.status_code == 200:
                return response.content
            else:
                last_error = f"API error: {response.status_code} - {response.text}"
                if response.status_code >= 500:  # Server error, retry
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"Server error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                raise Exception(last_error)
                
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Network error ({type(e).__name__}), retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to generate interviewer audio after {max_retries} attempts: {e}")
        except Exception as e:
            raise Exception(f"Failed to generate interviewer audio: {e}")
    
    raise Exception(f"Failed to generate interviewer audio after {max_retries} attempts: {last_error}")


def generate_persona_audio(
    text: str,
    persona_name: str,
    day: int = 1
) -> bytes:
    """Generate persona response using OpenAI TTS with emotional context.
    
    Args:
        text: Answer text to convert to speech
        persona_name: Persona identifier (steve, sarah, marcus, priya, alex)
        day: Day number (1-5) to adjust emotional tone
        
    Returns:
        Audio data as bytes (MP3 format)
        
    Raises:
        ValueError: If OPENAI_API_KEY not found or invalid persona
        Exception: If API call fails
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    # Get voice and instructions for persona
    try:
        voice, instructions = get_persona_voice_config(persona_name, day)
    except KeyError:
        raise ValueError(f"Unknown persona: {persona_name}")
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            instructions=instructions
        )
        return response.content
    except Exception as e:
        raise Exception(f"Failed to generate persona audio: {e}")


def get_persona_voice_config(persona_name: str, day: int) -> Tuple[str, str]:
    """Get voice and emotional instructions for a persona on a specific day.
    
    Args:
        persona_name: Persona identifier
        day: Day number (1-5)
        
    Returns:
        Tuple of (voice_id, instructions)
    """
    voice_map = {
        "steve": ("onyx", get_steve_instructions(day)),
        "sarah": ("shimmer", get_sarah_instructions(day)),
        "marcus": ("echo", get_marcus_instructions(day)),
        "priya": ("alloy", get_priya_instructions(day)),
        "alex": ("fable", get_alex_instructions(day))
    }
    
    return voice_map[persona_name.lower()]


# Emotional instructions for each persona by day

def get_steve_instructions(day: int) -> str:
    """Emotional instructions for Steve (The Avoider - defensive, declining confidence)."""
    instructions = {
        1: "Speak with moderate confidence but slight hesitation. Sound engaged.",
        2: "Speak with increasing uncertainty and a slightly defensive tone. Less confident.",
        3: "Speak defensively, avoid being specific, sound evasive and uncomfortable.",
        4: "Speak with frustration and low energy, very defensive. Sound stuck.",
        5: "Speak with resignation and defeat, still avoiding help. Sound exhausted."
    }
    return instructions.get(day, instructions[1])


def get_sarah_instructions(day: int) -> str:
    """Emotional instructions for Sarah (The Overwhelmed - anxious, self-aware)."""
    instructions = {
        1: "Speak with enthusiasm and energy. Sound confident and productive.",
        2: "Speak with slight concern creeping in. Still energetic but thoughtful.",
        3: "Speak with stress and uncertainty. Sound overwhelmed by options.",
        4: "Speak with anxiety and analysis paralysis. Many options, can't decide.",
        5: "Speak with relief when asking for help. Stressed but self-aware."
    }
    return instructions.get(day, instructions[1])


def get_marcus_instructions(day: int) -> str:
    """Emotional instructions for Marcus (The Overconfident - confident but misguided)."""
    instructions = {
        1: "Speak with strong confidence and authority. Very specific and technical.",
        2: "Speak with confidence and detail. Sound like an expert.",
        3: "Speak with continued confidence. Technical and assured.",
        4: "Speak with confidence but start to sound repetitive. Still assured.",
        5: "Speak with sudden realization and concern. Confidence drops as understanding dawns."
    }
    return instructions.get(day, instructions[1])


def get_priya_instructions(day: int) -> str:
    """Emotional instructions for Priya (The Healthy Progress - balanced, collaborative)."""
    instructions = {
        1: "Speak with clarity and calm confidence. Professional and specific.",
        2: "Speak with steady energy and clear progress. Collaborative.",
        3: "Speak with continued clarity. Describe concrete accomplishments.",
        4: "Speak with positive energy. Show clear progression and teamwork.",
        5: "Speak with satisfaction and forward momentum. Healthy communication."
    }
    return instructions.get(day, instructions[1])


def get_alex_instructions(day: int) -> str:
    """Emotional instructions for Alex (The Burnt Out - flat, disengaged)."""
    instructions = {
        1: "Speak with low energy and minimal enthusiasm. Brief responses.",
        2: "Speak with flat tone and disengagement. Very brief.",
        3: "Speak with apathy and minimal effort. Sound tired and detached.",
        4: "Speak with very low energy. Terse, minimal responses. Disengaged.",
        5: "Speak with complete flatness. No emotion, just going through motions."
    }
    return instructions.get(day, instructions[1])


# Mapping of persona names to descriptions (for UI display)
PERSONA_DESCRIPTIONS: Dict[str, str] = {
    "steve": "The Avoider - Defensive, stuck but won't admit it",
    "sarah": "The Overwhelmed - Self-aware but paralyzed by options",
    "marcus": "The Overconfident - Confident but going in wrong direction",
    "priya": "The Healthy Progress - Collaborative, making steady progress",
    "alex": "The Burnt Out - Disengaged, going through the motions"
}


if __name__ == "__main__":
    # Test audio generation
    print("Testing voice generation...")
    print()
    
    # Test interviewer audio
    print("1. Testing interviewer audio (Smallest.ai Lightning)...")
    try:
        question = "What did you work on yesterday?"
        audio = generate_interviewer_audio(question)
        print(f"   ✅ Generated {len(audio)} bytes of audio")
        
        # Save test file
        with open("test_interviewer.mp3", "wb") as f:
            f.write(audio)
        print(f"   💾 Saved to test_interviewer.mp3")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test persona audio
    print("2. Testing persona audio (OpenAI TTS)...")
    for persona in ["steve", "priya"]:
        try:
            answer = "I'm working on the authentication feature."
            audio = generate_persona_audio(answer, persona, day=1)
            print(f"   ✅ {persona.capitalize()}: Generated {len(audio)} bytes")
            
            # Save test file
            with open(f"test_{persona}.mp3", "wb") as f:
                f.write(audio)
            print(f"   💾 Saved to test_{persona}.mp3")
        except Exception as e:
            print(f"   ❌ {persona.capitalize()} error: {e}")
    
    print()
    print("Voice generation tests complete!")
    print("Play the generated MP3 files to verify audio quality.")
