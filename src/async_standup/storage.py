"""Storage module for standup data using JSON file."""

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional


class StandupStorage:
    """Manages standup data in JSON file format."""

    def __init__(self, data_file: str = "data/standups.json") -> None:
        """Initialize storage with data file path.
        
        Args:
            data_file: Path to JSON file for storing standups
        """
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty file if it doesn't exist
        if not self.data_file.exists():
            self._save([])

    def _save(self, standups: List[Dict[str, Any]]) -> None:
        """Save standups list to JSON file.
        
        Args:
            standups: List of standup dictionaries
        """
        with open(self.data_file, 'w') as f:
            json.dump(standups, f, indent=2)

    def load_standups(self) -> List[Dict[str, Any]]:
        """Load all standups from JSON file.
        
        Returns:
            List of standup dictionaries
        """
        if not self.data_file.exists():
            return []
        
        with open(self.data_file, 'r') as f:
            return json.load(f)

    def save_standup(self, standup: Dict[str, Any]) -> Dict[str, Any]:
        """Save a new standup entry.
        
        Expected schema for hybrid approach:
        {
            "id": int (auto-generated),
            "date": str (YYYY-MM-DD),
            "day_number": int,
            "conversation": List[Dict[str, str]] (optional, Q&A exchanges),
            "transcript": str (full conversation text),
            "emotion_score": float (0-100, from Pulse API),
            "dominant_emotion": str,
            "emotions": Dict[str, float] (from Pulse API),
            "conversational_signals": Dict[str, Any] (optional, from GPT-4),
            "stuck_probability": float (0.0-1.0, combined score),
            "created_at": str (ISO timestamp)
        }
        
        Args:
            standup: Standup data dictionary
            
        Returns:
            Saved standup with generated ID and timestamp
        """
        standups = self.load_standups()
        
        # Generate ID
        next_id = max([s.get('id', 0) for s in standups], default=0) + 1
        standup['id'] = next_id
        
        # Add timestamp if not present
        if 'created_at' not in standup:
            standup['created_at'] = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        
        standups.append(standup)
        self._save(standups)
        
        return standup

    def get_standups_by_range(
        self, 
        start_day: Optional[int] = None, 
        end_day: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get standups filtered by day_number range.
        
        Args:
            start_day: Start day number (inclusive), None for no lower bound
            end_day: End day number (inclusive), None for no upper bound
            
        Returns:
            Filtered list of standups sorted by day_number
        """
        standups = self.load_standups()
        
        filtered = standups
        if start_day is not None:
            filtered = [s for s in filtered if s.get('day_number', 0) >= start_day]
        if end_day is not None:
            filtered = [s for s in filtered if s.get('day_number', 0) <= end_day]
        
        # Sort by day_number
        filtered.sort(key=lambda s: s.get('day_number', 0))
        
        return filtered

    def clear(self) -> None:
        """Clear all standups from storage."""
        self._save([])

    def get_by_id(self, standup_id: int) -> Optional[Dict[str, Any]]:
        """Get a standup by its ID.
        
        Args:
            standup_id: ID of the standup
            
        Returns:
            Standup dictionary or None if not found
        """
        standups = self.load_standups()
        for standup in standups:
            if standup.get('id') == standup_id:
                return standup
        return None
