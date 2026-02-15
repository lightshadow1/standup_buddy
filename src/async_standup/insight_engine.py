"""Insight engine for detecting stuck patterns in standups."""

import re
from collections import Counter
from typing import List, Dict, Any, Optional


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text.
    
    Args:
        text: Input text
        min_length: Minimum word length to consider
        
    Returns:
        List of lowercased keywords
    """
    # Remove punctuation and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter by minimum length and remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'is', 'was', 'are', 'been', 'be', 'have',
                  'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                  'can', 'may', 'might', 'must', 'that', 'this', 'these', 'those',
                  'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his',
                  'her', 'its', 'our', 'their', 'me', 'him', 'us', 'them', 'myself',
                  'got', 'get', 'now'}
    
    keywords = [w for w in words if len(w) >= min_length and w not in stop_words]
    
    return keywords


def find_repeated_keywords(
    standups: List[Dict[str, Any]],
    min_occurrences: int = 3
) -> List[tuple[str, int]]:
    """Find keywords that appear repeatedly across standups.
    
    Args:
        standups: List of standup dictionaries with 'transcript' field
        min_occurrences: Minimum number of times a keyword must appear
        
    Returns:
        List of (keyword, count) tuples sorted by count (descending)
    """
    all_keywords = []
    
    for standup in standups:
        transcript = standup.get('transcript', '')
        keywords = extract_keywords(transcript)
        all_keywords.extend(keywords)
    
    # Count occurrences
    keyword_counts = Counter(all_keywords)
    
    # Filter by minimum occurrences
    repeated = [(kw, count) for kw, count in keyword_counts.items() 
                if count >= min_occurrences]
    
    # Sort by count (descending)
    repeated.sort(key=lambda x: x[1], reverse=True)
    
    return repeated


def calculate_emotion_delta(
    standups: List[Dict[str, Any]],
    baseline_day: int = 1
) -> float:
    """Calculate emotion score change from baseline day to latest day.
    
    Args:
        standups: List of standup dictionaries sorted by day_number
        baseline_day: Day number to use as baseline (typically 1)
        
    Returns:
        Emotion score delta (negative means decline)
    """
    if not standups:
        return 0.0
    
    # Find baseline standup
    baseline = next((s for s in standups if s.get('day_number') == baseline_day), None)
    if not baseline:
        baseline = standups[0]
    
    # Use last standup as current
    current = standups[-1]
    
    baseline_score = baseline.get('emotion_score', 0.0)
    current_score = current.get('emotion_score', 0.0)
    
    return current_score - baseline_score


def detect_stuck_pattern(
    standups: List[Dict[str, Any]],
    min_keyword_occurrences: int = 3,
    emotion_decline_threshold: float = 10.0
) -> Optional[Dict[str, Any]]:
    """Detect if engineer is stuck based on repeated keywords and emotion decline.
    
    Args:
        standups: List of standup dictionaries
        min_keyword_occurrences: Minimum times a keyword must repeat
        emotion_decline_threshold: Minimum emotion decline to flag (percentage points)
        
    Returns:
        Dict with stuck pattern info if detected, None otherwise:
            - is_stuck: Boolean
            - repeated_keyword: Most repeated keyword
            - keyword_count: Number of occurrences
            - emotion_delta: Emotion score change
            - recommendation: Suggested action
    """
    if len(standups) < 3:
        return None  # Need at least 3 days to detect pattern
    
    # Find repeated keywords
    repeated_keywords = find_repeated_keywords(standups, min_keyword_occurrences)
    
    # Calculate emotion change
    emotion_delta = calculate_emotion_delta(standups)
    
    # Check if stuck pattern exists
    has_repeated_keyword = len(repeated_keywords) > 0
    has_emotion_decline = emotion_delta <= -emotion_decline_threshold
    
    if has_repeated_keyword and has_emotion_decline:
        top_keyword, count = repeated_keywords[0]
        
        return {
            "is_stuck": True,
            "repeated_keyword": top_keyword,
            "keyword_count": count,
            "emotion_delta": emotion_delta,
            "days_affected": len(standups),
            "recommendation": "Consider pairing session or escalation"
        }
    
    return None


def calculate_stuck_probability(
    conversational_signals: Optional[Dict[str, Any]] = None,
    emotions: Optional[Dict[str, float]] = None,
    conversational_weight: float = 0.7,
    emotional_weight: float = 0.3
) -> Dict[str, Any]:
    """Calculate hybrid stuck probability combining conversational and emotional signals.
    
    Formula:
        conversational_score = (
            vagueness * 0.3 +
            (1 - specificity) * 0.3 +
            (hedging / 20) * 0.2 +  # Normalize hedging count
            (0 if help_seeking else 1) * 0.2
        )
        
        emotional_score = (
            (sadness + frustration) * 0.4 +
            (1 - (happiness + excitement)) * 0.3 +
            (anxiety * 0.3)
        ) normalized to 0-1
        
        stuck_probability = conversational_score * 0.7 + emotional_score * 0.3
    
    Thresholds:
        > 0.7: Stuck (immediate intervention needed)
        0.4-0.7: Warning (monitor closely)
        < 0.4: On track (healthy)
    
    Args:
        conversational_signals: Dict with vagueness_score, hedging_count, 
                               specificity_score, help_seeking, progress_indicators
        emotions: Dict with emotion percentages from Pulse API
        conversational_weight: Weight for conversational signals (default: 0.7)
        emotional_weight: Weight for emotional signals (default: 0.3)
        
    Returns:
        Dict with:
            - stuck_probability: float (0.0-1.0)
            - conversational_score: float (0.0-1.0)
            - emotional_score: float (0.0-1.0)
            - status: str ("stuck", "warning", "on_track")
            - breakdown: Dict with component scores
    """
    conversational_score = 0.0
    emotional_score = 0.0
    breakdown: Dict[str, Any] = {}
    
    # Calculate conversational score
    if conversational_signals:
        vagueness = conversational_signals.get('vagueness_score', 0.0)
        specificity = conversational_signals.get('specificity_score', 1.0)
        hedging_count = conversational_signals.get('hedging_count', 0)
        help_seeking = conversational_signals.get('help_seeking', True)
        
        # Normalize hedging (cap at 20 for score calculation)
        hedging_normalized = min(hedging_count / 20.0, 1.0)
        
        conversational_score = (
            vagueness * 0.3 +
            (1 - specificity) * 0.3 +
            hedging_normalized * 0.2 +
            (0.0 if help_seeking else 1.0) * 0.2
        )
        
        breakdown['conversational'] = {
            'vagueness': vagueness,
            'lack_of_specificity': 1 - specificity,
            'hedging': hedging_normalized,
            'avoiding_help': 0.0 if help_seeking else 1.0
        }
    
    # Calculate emotional score
    if emotions:
        # Negative emotions (higher = more stuck)
        sadness = emotions.get('sadness', 0.0) / 100.0
        frustration = emotions.get('frustration', 0.0) / 100.0
        anxiety = emotions.get('anxiety', 0.0) / 100.0
        
        # Positive emotions (lower = more stuck)
        happiness = emotions.get('happiness', 0.0) / 100.0
        excitement = emotions.get('excitement', 0.0) / 100.0
        
        emotional_score = (
            (sadness + frustration) * 0.4 +
            (1 - (happiness + excitement)) * 0.3 +
            anxiety * 0.3
        )
        
        # Normalize to 0-1 range (since emotions sum can exceed 1)
        emotional_score = min(emotional_score, 1.0)
        
        breakdown['emotional'] = {
            'negative_emotions': (sadness + frustration) / 2.0,
            'lack_of_positive': 1 - (happiness + excitement) / 2.0,
            'anxiety': anxiety
        }
    
    # Combine scores
    stuck_probability = (
        conversational_score * conversational_weight +
        emotional_score * emotional_weight
    )
    
    # Determine status
    if stuck_probability > 0.7:
        status = "stuck"
    elif stuck_probability >= 0.4:
        status = "warning"
    else:
        status = "on_track"
    
    return {
        'stuck_probability': round(stuck_probability, 3),
        'conversational_score': round(conversational_score, 3),
        'emotional_score': round(emotional_score, 3),
        'status': status,
        'breakdown': breakdown
    }


def generate_insight_message(stuck_info: Dict[str, Any]) -> str:
    """Generate human-readable insight message.
    
    Args:
        stuck_info: Stuck pattern information from detect_stuck_pattern
        
    Returns:
        Formatted insight message
    """
    if not stuck_info or not stuck_info.get('is_stuck'):
        return "No stuck pattern detected."
    
    keyword = stuck_info['repeated_keyword']
    count = stuck_info['keyword_count']
    delta = stuck_info['emotion_delta']
    days = stuck_info['days_affected']
    recommendation = stuck_info['recommendation']
    
    message = (
        f"⚠️  Stuck Pattern Detected\n\n"
        f"Engineer has been working on '{keyword}' for {count} consecutive days "
        f"({days} total days tracked).\n"
        f"Emotion declined by {abs(delta):.1f} percentage points.\n\n"
        f"Recommendation: {recommendation}"
    )
    
    return message


def format_hybrid_insight(
    day: int,
    stuck_probability: float,
    conversational_score: float,
    emotional_score: float,
    status: str,
    breakdown: Dict[str, Any]
) -> str:
    """Format hybrid stuck detection insight for display.
    
    Args:
        day: Day number
        stuck_probability: Combined probability (0-1)
        conversational_score: Conversational component (0-1)
        emotional_score: Emotional component (0-1)
        status: Status string ("stuck", "warning", "on_track")
        breakdown: Detailed score breakdown
        
    Returns:
        Formatted insight message
    """
    status_emoji = {
        'stuck': '🚨',
        'warning': '⚠️',
        'on_track': '✅'
    }
    
    emoji = status_emoji.get(status, '•')
    
    message = (
        f"{emoji} Day {day}: {status.upper().replace('_', ' ')}\n"
        f"  Stuck Probability: {stuck_probability:.1%}\n"
        f"  • Conversational: {conversational_score:.1%} (70% weight)\n"
        f"  • Emotional: {emotional_score:.1%} (30% weight)\n"
    )
    
    # Add breakdown if available
    if breakdown.get('conversational'):
        conv = breakdown['conversational']
        message += f"\n  Conversational Signals:\n"
        message += f"    - Vagueness: {conv.get('vagueness', 0):.1%}\n"
        message += f"    - Lack of specificity: {conv.get('lack_of_specificity', 0):.1%}\n"
        message += f"    - Hedging: {conv.get('hedging', 0):.1%}\n"
        message += f"    - Avoiding help: {conv.get('avoiding_help', 0):.1%}\n"
    
    if breakdown.get('emotional'):
        emot = breakdown['emotional']
        message += f"\n  Emotional Signals:\n"
        message += f"    - Negative emotions: {emot.get('negative_emotions', 0):.1%}\n"
        message += f"    - Lack of positive: {emot.get('lack_of_positive', 0):.1%}\n"
        message += f"    - Anxiety: {emot.get('anxiety', 0):.1%}\n"
    
    return message
