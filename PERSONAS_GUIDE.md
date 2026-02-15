# AsyncStandup Personas Guide

This guide documents the 5 engineer personas used to test and demonstrate the AsyncStandup hybrid stuck detection system.

## Overview

Each persona represents a different communication pattern and stuck state. They help validate that the system can:
- ✅ Detect different types of stuck patterns
- ✅ Avoid false positives (healthy engineers flagged as stuck)
- ✅ Avoid false negatives (stuck engineers appearing healthy)

---

## Persona 1: Steve - The Avoider

**Classification**: Defensive Stuck Engineer

**Description**: Stuck on a problem but hasn't admitted it yet. Defensive, avoids detail, refuses help.

### Communication Style
- **Day 1**: Relatively specific, optimistic about progress
- **Day 2**: Starting to get vague
- **Day 3**: Very vague, defensive when probed
- **Day 4**: Can't articulate what was tried
- **Day 5**: Admits timeline slippage, still won't seek help

### Linguistic Patterns
- Heavy hedging: "um", "like", "I think", "kind of", "just"
- Deflects specifics: "It's complicated...", "Just working through issues..."
- Avoids help: "No, I want to figure it out myself"

### Expected Signals
| Metric | Day 1 | Day 5 | Trend |
|--------|-------|-------|-------|
| Vagueness | 10% | 80% | ↑↑↑ |
| Hedging | 3 words | 23 words | ↑↑↑ |
| Specificity | 90% | 20% | ↓↓↓ |
| Help-seeking | False | False | Consistent |
| Stuck Probability | 28% | 73% | 🚨 STUCK |

### Why This Persona
**Tests**: Classic stuck pattern detection (vague + defensive + isolated)

**Detection Difficulty**: ✅ Easy - Clear signals across all dimensions

---

## Persona 2: Sarah - The Overwhelmed

**Classification**: Overwhelmed but Self-Aware

**Description**: Junior engineer who knows she's stuck, feels overwhelmed by options, eventually asks for help.

### Communication Style
- **Day 1-2**: Productive, asking good questions
- **Day 3**: Multiple blockers appear, stress increases
- **Day 4**: Lists many things tried, analysis paralysis
- **Day 5**: Admits stuck, asks for help

### Linguistic Patterns
- Minimal hedging but high uncertainty: "I'm not sure which approach..."
- Provides TOO much detail (information overload)
- Self-aware: "Maybe I should try X? Or Y? I don't know which is right..."
- Eventually seeks help: "Could someone pair with me on this?"

### Expected Signals
| Metric | Day 1 | Day 5 | Trend |
|--------|-------|-------|-------|
| Vagueness | 15% | 30% | ↑ |
| Hedging | 2 words | 10 words | ↑ |
| Specificity | 85% | 70% | ↓ |
| Help-seeking | False | **True** | Emerges |
| Stuck Probability | 20% | 50% | ⚠️ WARNING |

### Why This Persona
**Tests**: Moderate stuck detection + help-seeking behavior (positive sign)

**Detection Difficulty**: ⚠️ Moderate - Not as severe as Steve, but self-awareness is healthy

**Key Insight**: Help-seeking = good sign, lowers stuck severity

---

## Persona 3: Marcus - The Overconfident

**Classification**: Confident but Misguided

**Description**: Senior engineer who sounds on track but is going in the wrong direction due to flawed assumptions.

### Communication Style
- **Day 1-3**: Very specific technical details, sounds impressive
- **Day 4**: Still specific but repeating same approach (no actual progress)
- **Day 5**: Realizes approach is fundamentally wrong

### Linguistic Patterns
- Confident language: "I'm implementing...", "The solution is clearly..."
- High technical detail: "Refactoring auth layer with RS256, token rotation..."
- Never asks for help: "It's under control", "I've got this"
- Day 5 realization: "Wait... the whole approach might be wrong"

### Expected Signals
| Metric | Day 1 | Day 5 | Trend |
|--------|-------|-------|-------|
| Vagueness | 10% | 20% | → |
| Hedging | 1 word | 4 words | → |
| Specificity | 90% | **80%** | High! |
| Help-seeking | False | False | Consistent |
| Stuck Probability | 18% | 45% | ⚠️ WARNING |
| **Repeated Task** | - | "auth refactoring" | 🚨 Key Signal |

### Why This Persona
**Tests**: False negative prevention (high specificity but actually stuck)

**Detection Difficulty**: 🚨 Hard - Looks healthy on surface, needs cross-day analysis

**Key Insight**: Repeated task detection is critical for catching overconfident engineers

---

## Persona 4: Priya - The Healthy Progress

**Classification**: Healthy Engineer (Control/Baseline)

**Description**: Mid-level engineer making consistent progress with good collaboration habits.

### Communication Style
- **Day 1-5**: Steady progress, clear next steps
- Encounters blockers but resolves or escalates appropriately
- Shows variety of work (not stuck on one thing)

### Linguistic Patterns
- Clear, specific: "Yesterday I completed JWT, tested 3 flows. Today adding refresh tokens."
- Concrete metrics: "Finished password reset, got code review, merged. Now on 2FA."
- Appropriate help: "Can someone review my PR?", "Quick question about the spec..."

### Expected Signals
| Metric | Day 1 | Day 5 | Trend |
|--------|-------|-------|-------|
| Vagueness | 10% | 15% | → |
| Hedging | 2 words | 3 words | → |
| Specificity | 90% | 85% | → |
| Help-seeking | **True** | **True** | Healthy |
| Stuck Probability | 15% | 22% | ✅ ON TRACK |

### Why This Persona
**Tests**: False positive prevention (ensure healthy engineers stay green)

**Detection Difficulty**: ✅ Easy - Should never trigger stuck alerts

**Key Insight**: Variety of tasks + appropriate help-seeking = healthy pattern

---

## Persona 5: Alex - The Burnt Out

**Classification**: Disengaged/Burnout

**Description**: Engineer experiencing burnout, showing up but disengaged and going through motions.

### Communication Style
- **Day 1-2**: Brief but acceptable
- **Day 3-5**: Increasingly terse, low energy

### Linguistic Patterns
- Very short answers: "Same thing as yesterday", "Still working on it", "Nothing new"
- No elaboration when pressed: "I don't know, just trying things", "It's fine"
- Doesn't ask for help (not defensive, just apathetic)

### Expected Signals
| Metric | Day 1 | Day 5 | Trend |
|--------|-------|-------|-------|
| Vagueness | 40% | 75% | ↑↑ |
| Hedging | 5 words | 12 words | ↑ |
| Specificity | 60% | 25% | ↓↓ |
| Help-seeking | False | False | Consistent |
| Stuck Probability | 35% | 65% | 🚨 STUCK |
| **Emotional Pattern** | - | **Flat/neutral** | 🔑 Key Signal |

### Why This Persona
**Tests**: Disengagement detection (different from defensive stuck)

**Detection Difficulty**: ✅ Easy - High vagueness + flat emotions

**Key Insight**: Emotional flatness (not sad, not frustrated, just neutral) distinguishes burnout from stuck

---

## Detection Strategy Summary

### Easy to Detect ✅
- **Steve (Avoider)**: High vagueness + high hedging + no help-seeking
- **Alex (Burnt Out)**: High vagueness + flat emotions

### Moderate Difficulty ⚠️
- **Sarah (Overwhelmed)**: Moderate signals but self-aware (seeks help eventually)
  - Lower intervention urgency due to help-seeking

### Hard to Detect 🚨
- **Marcus (Overconfident)**: Low vagueness but stuck
  - Requires cross-day analysis for repeated tasks
  - False negative risk if only looking at daily metrics

### Healthy Baseline ✅
- **Priya (Healthy)**: Low vagueness + appropriate help-seeking + task variety
  - False positive prevention
  - Gold standard for comparison

---

## Usage

### Running Individual Personas

```bash
# Generate conversations for a specific persona
uv run python -m src.async_standup.conversation_agent steve
uv run python -m src.async_standup.conversation_agent sarah
uv run python -m src.async_standup.conversation_agent marcus
uv run python -m src.async_standup.conversation_agent priya
uv run python -m src.async_standup.conversation_agent alex
```

### Running Comparison Demo

```bash
# Compare all 5 personas side-by-side
uv run python persona_comparison_demo.py
```

This generates 25 conversations (5 per persona) and displays a comparison table.

### Using in Hybrid Demo

```python
from src.async_standup.conversation_agent import generate_5_day_conversations

# Generate with specific persona
conversations = generate_5_day_conversations(persona_name="marcus")
```

---

## Intervention Recommendations

Based on persona patterns, here are suggested interventions:

### 🚨 Steve (Defensive Stuck)
- **Action**: Immediate 1:1, assign pair programming
- **Approach**: Non-judgmental, focus on unblocking
- **Timeline**: Within 24 hours

### ⚠️ Sarah (Overwhelmed)
- **Action**: Technical mentoring, decision-making support
- **Approach**: Help narrow options, boost confidence
- **Timeline**: Within 48 hours

### 🚨 Marcus (Overconfident)
- **Action**: Architecture review, reality check
- **Approach**: Gentle course correction, validate approach early
- **Timeline**: Before more time wasted

### ✅ Priya (Healthy)
- **Action**: None, continue monitoring
- **Approach**: Recognize good work, maintain momentum
- **Timeline**: Regular check-ins

### 🚨 Alex (Burnt Out)
- **Action**: Manager conversation, workload/wellness check
- **Approach**: Address root cause (burnout), not just symptoms
- **Timeline**: Immediate, may need time off

---

## Testing Guidelines

When validating the stuck detection system:

1. **Run all 5 personas** to ensure diverse pattern detection
2. **Check for false positives** (Priya should stay green)
3. **Check for false negatives** (Marcus should be caught despite high specificity)
4. **Validate progression** (Day 1 → Day 5 trends should match expectations)
5. **Test emotional integration** (Alex's flat emotions should be detected)
6. **Verify help-seeking impact** (Sarah's help-seeking should lower severity)

---

## Future Persona Ideas

Additional personas to consider:

- **The Perfectionist**: High specificity but stuck in endless optimization
- **The Multitasker**: Switching between tasks, never finishing any
- **The Silent Struggler**: Minimal communication, hard to assess
- **The Over-Committer**: Taking on too much, spreading too thin
- **The Code Cowboy**: Moving fast but breaking things

---

**Last Updated**: Session 3 (Persona System Implementation)
