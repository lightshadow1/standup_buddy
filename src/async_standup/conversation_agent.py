"""Conversation agent for generating and analyzing standup conversations using GPT-4."""

import json
import os
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .personas import get_persona, get_persona_system_prompt, list_personas


# Load environment variables
load_dotenv()


# Default system prompt (Steve - The Avoider)
CONVERSATION_GENERATOR_PROMPT = """You are an engineer giving daily standup updates. Generate realistic standup conversation responses.

Context: You're working on an authentication feature and experiencing a realistic progression from healthy work to being stuck.

Day 1-2: Be specific, enthusiastic, show clear progress with concrete details
Day 3: Start becoming vaguer, show some uncertainty
Day 4-5: Be very vague, use hedging language, can't provide specifics, not seeking help

Important patterns to include when stuck:
- Hedging words: "um", "like", "I think", "kind of", "sort of"
- Vague responses: "still working on it", "the usual stuff", "nothing much"
- Can't provide specifics when asked
- Mentions same task multiple days without clear progress
- Avoids asking for help even when struggling

Respond naturally and conversationally."""

CONVERSATION_ANALYZER_PROMPT = """You are an expert at analyzing standup conversations to detect when engineers are stuck.

Analyze the conversation and detect these signals:

1. Vagueness: Lack of specific details, abstract language
2. Hedging: Words like "um", "like", "I think", "kind of", "sort of", "maybe"
3. Specificity: Concrete details vs vague statements
4. Help-seeking: Whether they're asking for help or isolating
5. Progress: Clear next steps vs unclear direction
6. Overconfidence Pattern: High specificity BUT no actual progress (same task, wrong direction)

IMPORTANT - Two types of stuck engineers:
- DEFENSIVE STUCK: Vague, hedging, avoiding detail (HIGH vagueness score)
- OVERCONFIDENT STUCK: Specific, confident, but wrong direction (LOW vagueness, but stuck)

For OVERCONFIDENT pattern, look for:
- Very detailed technical responses (low vagueness)
- Same core task mentioned without completion
- No help-seeking despite lack of progress
- Confident language ("definitely", "clearly", "will work")
- Missing: completion, moving to new tasks, validating approach

Return a JSON object with:
{
  "vagueness_score": 0.0-1.0 (0=specific, 1=very vague),
  "hedging_count": integer count of hedging words,
  "specificity_score": 0.0-1.0 (0=no details, 1=very specific),
  "help_seeking": boolean (true if asking/open to help),
  "progress_indicators": boolean (true if clear next steps AND making progress),
  "repeated_task": string or null (task mentioned multiple times without completion),
  "overconfident_pattern": boolean (true if high specificity but stuck),
  "signals_detected": [list of specific signals found],
  "summary": "brief analysis"
}

Be objective and look for patterns, not just keywords. HIGH SPECIFICITY alone does NOT mean healthy - check for actual progress."""


def generate_conversation(
    day: int, 
    task_context: str = "authentication feature",
    persona_name: Optional[str] = None
) -> List[Dict[str, str]]:
    """Generate a realistic standup conversation for a specific day.
    
    Args:
        day: Day number (1-5)
        task_context: What the engineer is working on
        persona_name: Persona to use (steve, sarah, marcus, priya, alex). 
                      If None, uses default prompt.
        
    Returns:
        List of Q&A exchanges: [{"q": "question", "a": "answer"}, ...]
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    client = OpenAI(api_key=api_key)
    
    # Get system prompt based on persona
    if persona_name:
        system_prompt = get_persona_system_prompt(persona_name)
    else:
        system_prompt = CONVERSATION_GENERATOR_PROMPT
    
    # Define questions that adapt based on day
    if day <= 2:
        questions = [
            "What did you work on yesterday?",
            "That sounds good! What are you working on today?",
            "Any blockers or concerns?"
        ]
    elif day == 3:
        questions = [
            "What did you work on yesterday?",
            "Can you tell me more specifically what you accomplished?",
            "What's your plan for today?",
            "Any blockers?"
        ]
    else:  # Days 4-5
        questions = [
            "What did you work on yesterday?",
            "What specifically have you tried so far?",
            "Have you asked anyone for help with this?",
            "How long have you been working on this issue?",
            "What's blocking you from moving forward?"
        ]
    
    conversation = []
    context_messages = [{"role": "system", "content": system_prompt}]
    
    # Add context about the day
    context_messages.append({
        "role": "user",
        "content": f"You are on Day {day} of working on the {task_context}. "
                   f"Respond to standup questions authentically for this day's progression."
    })
    
    # Generate conversation exchange by exchange
    for question in questions:
        context_messages.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=context_messages,
            temperature=0.8,
            max_tokens=150
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Add to conversation history
        context_messages.append({"role": "assistant", "content": answer})
        conversation.append({"q": question, "a": answer})
    
    return conversation


def analyze_conversation(conversation: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze a conversation to extract stuck signals.
    
    Args:
        conversation: List of Q&A exchanges
        
    Returns:
        Dictionary with conversational signals and scores
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    client = OpenAI(api_key=api_key)
    
    # Format conversation for analysis
    conversation_text = "\n".join([
        f"Q: {exchange['q']}\nA: {exchange['a']}"
        for exchange in conversation
    ])
    
    # Analyze with GPT-4
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": CONVERSATION_ANALYZER_PROMPT},
            {"role": "user", "content": f"Analyze this standup conversation:\n\n{conversation_text}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    analysis = json.loads(response.choices[0].message.content)
    
    return analysis


def generate_5_day_conversations(
    task_context: str = "authentication feature",
    persona_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate 5 days of realistic standup conversations showing progression.
    
    Args:
        task_context: What the engineer is working on
        persona_name: Persona to use (steve, sarah, marcus, priya, alex)
        
    Returns:
        List of 5 daily conversations with metadata
    """
    conversations = []
    
    # Get persona info if provided
    persona_info = None
    if persona_name:
        persona = get_persona(persona_name)
        persona_info = {
            "name": persona["name"],
            "archetype": persona["archetype"],
            "classification": persona["classification"]
        }
        print(f"\n🎭 Generating conversations for: {persona['name']} - {persona['archetype']}")
        print(f"   Classification: {persona['classification']}\n")
    
    for day in range(1, 6):
        print(f"Generating Day {day} conversation...")
        
        conversation = generate_conversation(day, task_context, persona_name)
        
        conv_data = {
            "day": day,
            "conversation": conversation,
            "task_context": task_context
        }
        
        if persona_info:
            conv_data["persona"] = persona_info
        
        conversations.append(conv_data)
    
    return conversations


def analyze_5_day_conversations(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze 5 days of conversations to extract signals.
    
    Args:
        conversations: List of daily conversations
        
    Returns:
        List of conversations with analysis added
    """
    analyzed = []
    
    for conv_data in conversations:
        day = conv_data["day"]
        conversation = conv_data["conversation"]
        
        print(f"Analyzing Day {day} conversation...")
        
        analysis = analyze_conversation(conversation)
        
        analyzed.append({
            **conv_data,
            "conversational_signals": analysis
        })
    
    return analyzed


if __name__ == "__main__":
    import sys
    
    # Demo: Generate and analyze 5 days
    print("=" * 70)
    print("Conversation Agent Demo")
    print("=" * 70)
    print()
    
    # Check for persona argument
    persona = None
    if len(sys.argv) > 1:
        persona = sys.argv[1].lower()
        print(f"Using persona: {persona}\n")
    else:
        print("Available personas:", ", ".join(list_personas().keys()))
        print("Usage: python -m src.async_standup.conversation_agent [persona_name]\n")
    
    # Generate
    print("Step 1: Generating 5 days of conversations...")
    conversations = generate_5_day_conversations(persona_name=persona)
    print(f"✅ Generated {len(conversations)} conversations\n")
    
    # Analyze
    print("Step 2: Analyzing conversations...")
    analyzed = analyze_5_day_conversations(conversations)
    print(f"✅ Analyzed {len(analyzed)} conversations\n")
    
    # Display results
    print("=" * 70)
    print("Results")
    print("=" * 70)
    
    for data in analyzed:
        day = data["day"]
        signals = data["conversational_signals"]
        
        print(f"\nDay {day}:")
        print(f"  Vagueness: {signals.get('vagueness_score', 0):.2f}")
        print(f"  Hedging count: {signals.get('hedging_count', 0)}")
        print(f"  Specificity: {signals.get('specificity_score', 0):.2f}")
        print(f"  Help seeking: {signals.get('help_seeking', False)}")
        print(f"  Signals: {', '.join(signals.get('signals_detected', []))}")
        
        # Show sample exchange
        if data["conversation"]:
            first_exchange = data["conversation"][0]
            print(f"  Sample: Q: {first_exchange['q'][:50]}...")
            print(f"          A: {first_exchange['a'][:80]}...")
