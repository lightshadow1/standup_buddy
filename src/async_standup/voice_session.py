"""Session management for voice demo.

Handles:
- Session creation and storage
- Audio file management
- Metadata storage
"""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class AudioExchange:
    """Represents a single Q&A audio exchange."""
    question_text: str
    answer_text: str
    question_audio_file: str
    answer_audio_file: str
    day: int
    exchange_index: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VoiceSession:
    """Represents a complete voice demo session."""
    session_id: str
    persona_name: str
    persona_archetype: str
    exchanges: List[AudioExchange]
    analysis: Dict[str, Any]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'persona_name': self.persona_name,
            'persona_archetype': self.persona_archetype,
            'exchanges': [e.to_dict() for e in self.exchanges],
            'analysis': self.analysis,
            'created_at': self.created_at
        }


class SessionManager:
    """Manages voice demo sessions, audio files, and metadata."""
    
    def __init__(
        self,
        audio_dir: Path = Path("data/voice_sessions"),
        metadata_dir: Path = Path("data/voice_metadata")
    ):
        """Initialize session manager.
        
        Args:
            audio_dir: Directory to store audio files
            metadata_dir: Directory to store session metadata
        """
        self.audio_dir = Path(audio_dir)
        self.metadata_dir = Path(metadata_dir)
        
        # Create directories if they don't exist
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(self, persona_name: str, persona_archetype: str = "") -> str:
        """Create a new session.
        
        Args:
            persona_name: Name of the persona
            persona_archetype: Archetype description
            
        Returns:
            Session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        session_dir = self.audio_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        return session_id
    
    def save_audio(
        self,
        session_id: str,
        filename: str,
        audio_data: bytes
    ) -> str:
        """Save audio data to session directory.
        
        Args:
            session_id: Session ID
            filename: Audio filename (e.g., 'q_1_1.mp3')
            audio_data: Audio bytes
            
        Returns:
            Relative path to saved audio file
        """
        filepath = self.audio_dir / session_id / filename
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        # Return relative path for API serving
        return f"{session_id}/{filename}"
    
    def save_session(self, session: VoiceSession) -> None:
        """Save session metadata to JSON file.
        
        Args:
            session: VoiceSession object
        """
        filepath = self.metadata_dir / f"{session.session_id}.json"
        with open(filepath, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Load session from metadata.
        
        Args:
            session_id: Session ID
            
        Returns:
            VoiceSession object or None if not found
        """
        filepath = self.metadata_dir / f"{session_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath) as f:
            data = json.load(f)
        
        # Reconstruct AudioExchange objects
        exchanges = [AudioExchange(**e) for e in data['exchanges']]
        
        return VoiceSession(
            session_id=data['session_id'],
            persona_name=data['persona_name'],
            persona_archetype=data['persona_archetype'],
            exchanges=exchanges,
            analysis=data['analysis'],
            created_at=data['created_at']
        )
    
    def list_sessions(self) -> List[Dict[str, str]]:
        """List all available sessions.
        
        Returns:
            List of session summaries
        """
        sessions = []
        
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                sessions.append({
                    'session_id': data['session_id'],
                    'persona_name': data['persona_name'],
                    'persona_archetype': data['persona_archetype'],
                    'created_at': data['created_at'],
                    'exchange_count': len(data['exchanges'])
                })
            except Exception:
                continue
        
        # Sort by creation time (most recent first)
        sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its audio files.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted, False if not found
        """
        # Delete audio directory
        audio_dir = self.audio_dir / session_id
        if audio_dir.exists():
            import shutil
            shutil.rmtree(audio_dir)
        
        # Delete metadata file
        metadata_file = self.metadata_dir / f"{session_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            return True
        
        return False
    
    def get_audio_path(self, session_id: str, filename: str) -> Optional[Path]:
        """Get full path to an audio file.
        
        Args:
            session_id: Session ID
            filename: Audio filename
            
        Returns:
            Path object or None if not found
        """
        filepath = self.audio_dir / session_id / filename
        return filepath if filepath.exists() else None
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Delete sessions older than specified hours.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of sessions deleted
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        for session_summary in self.list_sessions():
            try:
                created_at = datetime.fromisoformat(session_summary['created_at'])
                if created_at < cutoff_time:
                    if self.delete_session(session_summary['session_id']):
                        deleted_count += 1
            except Exception:
                continue
        
        return deleted_count


def create_session_from_conversations(
    persona_name: str,
    persona_archetype: str,
    conversations: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    session_manager: SessionManager
) -> VoiceSession:
    """Create a VoiceSession object from conversation data.
    
    Args:
        persona_name: Persona name
        persona_archetype: Persona archetype
        conversations: List of conversation data with 'day' and 'conversation' keys
        analysis: Analysis results
        session_manager: SessionManager instance
        
    Returns:
        VoiceSession object (not yet saved)
    """
    session_id = str(uuid.uuid4())
    exchanges = []
    
    exchange_index = 0
    for conv_data in conversations:
        day = conv_data['day']
        conversation = conv_data['conversation']
        
        for exchange in conversation:
            # Generate filenames (audio not yet generated)
            q_filename = f"q_{day}_{exchange_index}.mp3"
            a_filename = f"a_{day}_{exchange_index}.mp3"
            
            exchanges.append(AudioExchange(
                question_text=exchange['q'],
                answer_text=exchange['a'],
                question_audio_file=f"{session_id}/{q_filename}",
                answer_audio_file=f"{session_id}/{a_filename}",
                day=day,
                exchange_index=exchange_index
            ))
            
            exchange_index += 1
    
    return VoiceSession(
        session_id=session_id,
        persona_name=persona_name,
        persona_archetype=persona_archetype,
        exchanges=exchanges,
        analysis=analysis,
        created_at=datetime.now().isoformat()
    )


if __name__ == "__main__":
    # Test session management
    print("Testing session management...")
    print()
    
    # Create manager
    manager = SessionManager(
        audio_dir=Path("data/test_voice_sessions"),
        metadata_dir=Path("data/test_voice_metadata")
    )
    print("✅ SessionManager created")
    print(f"   Audio dir: {manager.audio_dir}")
    print(f"   Metadata dir: {manager.metadata_dir}")
    print()
    
    # Create test session
    session_id = manager.create_session("steve", "The Avoider")
    print(f"✅ Created session: {session_id}")
    print()
    
    # Save test audio
    test_audio = b"fake audio data"
    audio_path = manager.save_audio(session_id, "test.mp3", test_audio)
    print(f"✅ Saved test audio: {audio_path}")
    print()
    
    # Create and save session metadata
    test_session = VoiceSession(
        session_id=session_id,
        persona_name="steve",
        persona_archetype="The Avoider",
        exchanges=[
            AudioExchange(
                question_text="Test question?",
                answer_text="Test answer.",
                question_audio_file=f"{session_id}/q_1.mp3",
                answer_audio_file=f"{session_id}/a_1.mp3",
                day=1,
                exchange_index=0
            )
        ],
        analysis={'stuck_probability': 0.5},
        created_at=datetime.now().isoformat()
    )
    
    manager.save_session(test_session)
    print("✅ Saved session metadata")
    print()
    
    # List sessions
    sessions = manager.list_sessions()
    print(f"✅ Listed sessions: {len(sessions)} found")
    for s in sessions:
        print(f"   - {s['persona_name']}: {s['exchange_count']} exchanges")
    print()
    
    # Load session
    loaded = manager.get_session(session_id)
    if loaded:
        print(f"✅ Loaded session: {loaded.persona_name}")
        print(f"   Exchanges: {len(loaded.exchanges)}")
    print()
    
    # Clean up test data
    import shutil
    if Path("data/test_voice_sessions").exists():
        shutil.rmtree("data/test_voice_sessions")
    if Path("data/test_voice_metadata").exists():
        shutil.rmtree("data/test_voice_metadata")
    print("✅ Cleaned up test data")
    print()
    
    print("Session management tests complete!")
