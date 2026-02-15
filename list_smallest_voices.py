"""List available voices from Smallest.ai Lightning API."""

import os
import json
from dotenv import load_dotenv
from smallestai.waves import WavesClient

load_dotenv()

def main():
    api_key = os.getenv("SMALLEST_API_KEY") or os.getenv("PULSE_API_KEY")
    if not api_key:
        print("❌ No API key found. Set SMALLEST_API_KEY or PULSE_API_KEY in .env")
        return
    
    print("=" * 70)
    print("SMALLEST.AI LIGHTNING VOICES")
    print("=" * 70)
    print()
    
    client = WavesClient(api_key=api_key)
    
    # Get available models
    print("📦 Available Models:")
    try:
        models = client.get_models()
        print(json.dumps(models, indent=2))
    except Exception as e:
        print(f"  Error getting models: {e}")
    print()
    
    # Get available languages
    print("🌍 Available Languages:")
    try:
        languages = client.get_languages()
        print(json.dumps(languages, indent=2))
    except Exception as e:
        print(f"  Error getting languages: {e}")
    print()
    
    # Get available voices for lightning model
    print("🎤 Available Voices (lightning model):")
    try:
        voices = client.get_voices(model="lightning")
        print(json.dumps(voices, indent=2))
        print()
        print(f"Total: {len(voices) if isinstance(voices, list) else 'N/A'} voices")
    except Exception as e:
        print(f"  Error getting voices: {e}")
    print()
    
    # Get available voices for lightning-v2 model
    print("🎤 Available Voices (lightning-v2 model):")
    try:
        voices_v2 = client.get_voices(model="lightning-v2")
        data = json.loads(voices_v2) if isinstance(voices_v2, str) else voices_v2
        voice_list = data.get('voices', [])
        
        print(f"Total: {len(voice_list)} voices\n")
        
        # Group by accent
        accents = {}
        for v in voice_list:
            accent = v['tags'].get('accent', 'unknown')
            if accent not in accents:
                accents[accent] = []
            accents[accent].append(v)
        
        for accent, voices_in_accent in sorted(accents.items()):
            print(f"  {accent.upper()} accent:")
            for v in voices_in_accent:
                gender = v['tags'].get('gender', 'unknown')
                age = v['tags'].get('age', 'unknown')
                usecases = ', '.join(v['tags'].get('usecases', [])[:2])
                print(f"    • {v['voiceId']} ({v['displayName']}) - {gender}, {age}")
                if usecases:
                    print(f"      Usecases: {usecases}")
            print()
    except Exception as e:
        print(f"  Error getting lightning-v2 voices: {e}")
    print()
    
    # Get cloned voices (if any)
    print("👤 Your Cloned Voices:")
    try:
        cloned = client.get_cloned_voices()
        if cloned:
            print(json.dumps(cloned, indent=2))
        else:
            print("  No cloned voices found")
    except Exception as e:
        print(f"  Error getting cloned voices: {e}")
    print()

if __name__ == "__main__":
    main()
