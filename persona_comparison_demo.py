"""Compare all 5 personas side-by-side to demonstrate different stuck patterns."""

from src.async_standup.conversation_agent import generate_5_day_conversations, analyze_5_day_conversations
from src.async_standup.personas import PERSONAS


def run_persona_comparison():
    """Run conversation generation and analysis for all 5 personas."""
    
    print("=" * 80)
    print("AsyncStandup Persona Comparison Demo")
    print("=" * 80)
    print()
    print("Generating and analyzing 5 days of conversations for each persona...")
    print("This will take a few minutes (25 conversations total, 5 per persona)")
    print()
    
    results = {}
    
    for persona_name in PERSONAS.keys():
        persona = PERSONAS[persona_name]
        
        print("\n" + "=" * 80)
        print(f"🎭 {persona['name']} - {persona['archetype']}")
        print(f"   {persona['description']}")
        print("=" * 80)
        
        # Generate conversations
        conversations = generate_5_day_conversations(persona_name=persona_name)
        
        # Analyze conversations
        analyzed = analyze_5_day_conversations(conversations)
        
        results[persona_name] = analyzed
        
        # Display brief summary
        print(f"\n✅ Completed {persona['name']}")
        day_1 = analyzed[0]["conversational_signals"]
        day_5 = analyzed[4]["conversational_signals"]
        
        print(f"   Day 1: Vagueness {day_1.get('vagueness_score', 0):.0%}, Hedging {day_1.get('hedging_count', 0)}")
        print(f"   Day 5: Vagueness {day_5.get('vagueness_score', 0):.0%}, Hedging {day_5.get('hedging_count', 0)}")
        print()
    
    # Display comparison table
    print("\n" + "=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)
    print()
    
    # Header
    print(f"{'Persona':<15} {'Day':<5} {'Vagueness':<12} {'Hedging':<10} {'Specificity':<12} {'Help?':<8} {'Status'}")
    print("-" * 80)
    
    for persona_name, analyzed_convs in results.items():
        persona = PERSONAS[persona_name]
        
        for data in analyzed_convs:
            day = data["day"]
            signals = data["conversational_signals"]
            
            vagueness = signals.get("vagueness_score", 0)
            hedging = signals.get("hedging_count", 0)
            specificity = signals.get("specificity_score", 0)
            help_seeking = signals.get("help_seeking", False)
            
            # Estimate stuck probability (simplified)
            conv_score = (vagueness * 0.3 + (1 - specificity) * 0.3 + 
                         min(hedging / 20, 1.0) * 0.2 + 
                         (0 if help_seeking else 1) * 0.2)
            
            if conv_score > 0.5:
                status = "⚠️ WARNING"
            elif conv_score > 0.35:
                status = "⚠️ WATCH"
            else:
                status = "✅ OK"
            
            name_display = persona["name"] if day == 1 else ""
            
            print(f"{name_display:<15} {day:<5} {vagueness:>10.0%}  {hedging:>8}  {specificity:>10.0%}  {str(help_seeking):>6}  {status}")
        
        print()
    
    # Summary insights
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print()
    
    print("🎭 Steve (The Avoider): Defensive stuck engineer")
    print("   • High vagueness progression (10% → 80%)")
    print("   • Dramatic hedging increase (3 → 23 words)")
    print("   • Never seeks help (False throughout)")
    print("   • Classic stuck pattern: Vague + Defensive + Isolated")
    print()
    
    print("🎭 Sarah (The Overwhelmed): Self-aware but paralyzed")
    print("   • Moderate vagueness (15% → 30%)")
    print("   • Stays specific but shows uncertainty")
    print("   • Help-seeking emerges (False → True by Day 5)")
    print("   • Healthy signal: Recognizes need for help")
    print()
    
    print("🎭 Marcus (The Overconfident): Confident but wrong direction")
    print("   • Low vagueness (10% → 20%)")
    print("   • Very low hedging (1 → 4 words)")
    print("   • Sounds great but repeats same task")
    print("   • Tricky case: High specificity but still stuck")
    print()
    
    print("🎭 Priya (The Healthy Progress): Baseline for comparison")
    print("   • Low vagueness throughout (10% → 15%)")
    print("   • Minimal hedging (2 → 3 words)")
    print("   • Appropriate help-seeking (True)")
    print("   • Gold standard: Specific + Collaborative + Progressive")
    print()
    
    print("🎭 Alex (The Burnt Out): Disengaged engineer")
    print("   • High vagueness (40% → 75%)")
    print("   • Moderate hedging (5 → 12 words)")
    print("   • Terse, minimal responses")
    print("   • Key differentiator: Flat emotions (not sad, just apathetic)")
    print()
    
    print("=" * 80)
    print("DETECTION STRATEGY")
    print("=" * 80)
    print()
    print("✅ Easy to detect:")
    print("   • Steve: High vagueness + high hedging + no help-seeking")
    print("   • Alex: High vagueness + short responses + flat emotions")
    print()
    print("⚠️ Moderate difficulty:")
    print("   • Sarah: Moderate signals but self-aware (eventually asks for help)")
    print()
    print("🚨 Hard to detect (false negative risk):")
    print("   • Marcus: Low vagueness but stuck (need repeated_task detection)")
    print("   • Requires analyzing patterns across days, not just individual metrics")
    print()
    print("✅ Healthy engineer (avoid false positive):")
    print("   • Priya: Low vagueness + appropriate help-seeking + clear progress")
    print("   • Key: Variety of tasks, not stuck on one thing")
    print()


if __name__ == "__main__":
    run_persona_comparison()
