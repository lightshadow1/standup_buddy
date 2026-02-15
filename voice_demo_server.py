"""FastAPI server for AsyncStandup voice demo.

Provides:
- API endpoints for generating voice demos
- Audio file serving
- Session management
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import uuid

from src.async_standup.conversation_agent import (
    generate_5_day_conversations,
    analyze_5_day_conversations
)
from src.async_standup.personas import get_persona, list_personas
from src.async_standup.voice_generator import (
    generate_interviewer_audio,
    generate_persona_audio,
    PERSONA_DESCRIPTIONS
)
from src.async_standup.voice_session import (
    SessionManager,
    VoiceSession,
    AudioExchange
)
from src.async_standup.insight_engine import calculate_stuck_probability
from src.async_standup.analyze_audio import process_audio_file


# Initialize FastAPI app
app = FastAPI(
    title="AsyncStandup Voice Demo",
    description="Interactive voice demo showing AI-powered stuck detection",
    version="1.0.0"
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
session_manager = SessionManager()

# Mount static files directory (for serving HTML/CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Request/Response models
class GenerateRequest(BaseModel):
    persona: str


class GenerateResponse(BaseModel):
    session_id: str
    persona_name: str
    persona_archetype: str
    status: str
    message: str


class SessionResponse(BaseModel):
    session: Dict[str, Any]


# Root endpoint - serve the HTML frontend
@app.get("/")
async def root():
    """Serve the voice demo HTML page."""
    html_file = Path("static/voice_demo.html")
    if html_file.exists():
        return FileResponse(html_file)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Frontend not found. Please create static/voice_demo.html"}
        )


# API Endpoints

@app.get("/api/personas")
async def get_personas():
    """List available personas."""
    personas = []
    for name, archetype in list_personas().items():
        description = PERSONA_DESCRIPTIONS.get(name, "")
        personas.append({
            "name": name,
            "archetype": archetype,
            "description": description
        })
    return {"personas": personas}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_voice_demo(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """Generate a voice demo for a specific persona.
    
    This endpoint initiates the generation process and returns immediately.
    The actual generation happens in the background.
    """
    persona_name = request.persona.lower()
    
    # Validate persona
    try:
        persona = get_persona(persona_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {persona_name}")
    
    # Create session
    session_id = session_manager.create_session(
        persona_name=persona_name,
        persona_archetype=persona["archetype"]
    )
    
    # Start background generation
    background_tasks.add_task(
        generate_voice_demo_background,
        session_id,
        persona_name,
        persona["archetype"]
    )
    
    return GenerateResponse(
        session_id=session_id,
        persona_name=persona_name,
        persona_archetype=persona["archetype"],
        status="generating",
        message="Voice demo generation started. This will take 2-3 minutes."
    )


async def generate_voice_demo_background(
    session_id: str,
    persona_name: str,
    persona_archetype: str
):
    """Background task to generate voice demo.
    
    Steps:
    1. Generate conversations (GPT-4)
    2. Analyze conversations (GPT-4)
    3. Generate audio for each exchange (Smallest.ai + OpenAI TTS)
    4. Save session metadata
    """
    try:
        # Step 1: Generate conversations
        print(f"[{session_id}] Generating conversations for {persona_name}...")
        conversations = generate_5_day_conversations(persona_name=persona_name)
        
        # Step 2: Analyze conversations
        print(f"[{session_id}] Analyzing conversations...")
        analyzed = analyze_5_day_conversations(conversations)
        
        # Step 3: Calculate stuck probabilities for each day
        analysis_by_day = {}
        for conv_data in analyzed:
            day = conv_data['day']
            signals = conv_data.get('conversational_signals', {})
            
            # Calculate stuck probability (simplified - no emotions for now)
            result = calculate_stuck_probability(
                conversational_signals=signals,
                emotions=None
            )
            
            analysis_by_day[day] = {
                'stuck_probability': result['stuck_probability'],
                'status': result['status'],
                'conversational_score': result['conversational_score'],
                'signals': signals
            }
        
        # Step 4: Generate audio for each exchange
        print(f"[{session_id}] Generating audio...")
        exchanges = []
        exchange_index = 0
        
        for conv_data in analyzed:
            day = conv_data['day']
            conversation = conv_data['conversation']
            
            for exchange in conversation:
                question_text = exchange['q']
                answer_text = exchange['a']
                
                # Generate filenames
                q_filename = f"q_{day}_{exchange_index}.wav"
                a_filename = f"a_{day}_{exchange_index}.mp3"
                
                # Generate interviewer question audio
                print(f"[{session_id}] Generating Q{exchange_index+1} audio...")
                q_audio = generate_interviewer_audio(question_text)
                session_manager.save_audio(session_id, q_filename, q_audio)
                
                # Generate persona answer audio
                print(f"[{session_id}] Generating A{exchange_index+1} audio...")
                a_audio = generate_persona_audio(answer_text, persona_name, day)
                session_manager.save_audio(session_id, a_filename, a_audio)
                
                # Create exchange record
                exchanges.append(AudioExchange(
                    question_text=question_text,
                    answer_text=answer_text,
                    question_audio_file=f"{session_id}/{q_filename}",
                    answer_audio_file=f"{session_id}/{a_filename}",
                    day=day,
                    exchange_index=exchange_index
                ))
                
                exchange_index += 1
        
        # Step 5: Create and save session
        from datetime import datetime
        session = VoiceSession(
            session_id=session_id,
            persona_name=persona_name,
            persona_archetype=persona_archetype,
            exchanges=exchanges,
            analysis=analysis_by_day,
            created_at=datetime.now().isoformat()
        )
        
        session_manager.save_session(session)
        print(f"[{session_id}] Voice demo generation complete!")
        
    except Exception as e:
        print(f"[{session_id}] Error generating voice demo: {e}")
        import traceback
        traceback.print_exc()


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session metadata and status."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"session": session.to_dict()}


@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Check if session generation is complete."""
    session = session_manager.get_session(session_id)
    
    if session:
        return {
            "status": "complete",
            "session_id": session_id,
            "exchange_count": len(session.exchanges)
        }
    else:
        # Check if session directory exists (generation in progress)
        session_dir = session_manager.audio_dir / session_id
        if session_dir.exists():
            return {
                "status": "generating",
                "session_id": session_id
            }
        else:
            return {
                "status": "not_found",
                "session_id": session_id
            }


@app.get("/api/audio/{session_id}/{filename}")
async def get_audio(session_id: str, filename: str):
    """Serve audio file for a session."""
    audio_path = session_manager.get_audio_path(session_id, filename)
    
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type based on extension
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    
    return FileResponse(audio_path, media_type=media_type)


@app.get("/api/sessions")
async def list_sessions():
    """List all available sessions."""
    sessions = session_manager.list_sessions()
    return {"sessions": sessions}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its audio files."""
    success = session_manager.delete_session(session_id)
    
    if success:
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/cleanup")
async def cleanup_old_sessions():
    """Clean up sessions older than 24 hours."""
    deleted_count = session_manager.cleanup_old_sessions(max_age_hours=24)
    return {
        "status": "complete",
        "deleted_count": deleted_count
    }


# Interactive standup endpoints

@app.post("/api/interactive/save")
async def save_interactive_session(
    session_id: str = Form(...),
    exchanges: str = Form(...)  # JSON string of exchanges
):
    """Save a completed interactive standup session.
    
    Saves the session data so it can be viewed later.
    """
    try:
        import json
        from datetime import datetime
        
        exchanges_data = json.loads(exchanges)
        
        # Calculate final analysis
        progress_data = []
        for idx, exchange in enumerate(exchanges_data):
            vagueness = exchange['analysis']['conversational_signals']['vagueness']
            hedging = exchange['analysis']['conversational_signals']['hedging_count'] / 20
            sadness = exchange['analysis']['pulse_analysis']['emotions'].get('sadness', 0)
            frustration = exchange['analysis']['pulse_analysis']['emotions'].get('frustration', 0)
            
            conversational_score = (vagueness * 0.6 + hedging * 0.4)
            emotional_score = (sadness + frustration) / 2
            stuck_probability = conversational_score * 0.7 + emotional_score * 0.3
            
            status = 'on_track'
            if stuck_probability > 0.7:
                status = 'stuck'
            elif stuck_probability > 0.4:
                status = 'warning'
            
            progress_data.append({
                'exchange': idx + 1,
                'stuck_probability': stuck_probability,
                'status': status
            })
        
        # Create session metadata
        session_data = {
            'session_id': session_id,
            'session_type': 'interactive',
            'persona_name': 'live_user',
            'persona_archetype': 'Interactive User',
            'created_at': datetime.now().isoformat(),
            'exchanges': exchanges_data,
            'final_analysis': {
                'progress': progress_data,
                'final_status': progress_data[-1]['status'] if progress_data else 'unknown'
            }
        }
        
        # Save to metadata directory
        metadata_file = session_manager.metadata_dir / f"{session_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"[{session_id}] Interactive session saved")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session saved successfully"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save session: {str(e)}")


@app.get("/api/interactive/sessions")
async def list_interactive_sessions():
    """List all interactive standup sessions."""
    try:
        import json
        sessions = []
        
        for metadata_file in session_manager.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                
                # Only include interactive sessions
                if data.get('session_type') == 'interactive':
                    sessions.append({
                        'session_id': data['session_id'],
                        'created_at': data['created_at'],
                        'exchange_count': len(data.get('exchanges', [])),
                        'final_status': data.get('final_analysis', {}).get('final_status', 'unknown')
                    })
            except Exception:
                continue
        
        # Sort by creation time (most recent first)
        sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {"sessions": sessions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.get("/api/interactive/session/{session_id}")
async def get_interactive_session(session_id: str):
    """Get a specific interactive session."""
    try:
        import json
        metadata_file = session_manager.metadata_dir / f"{session_id}.json"
        
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Session not found")
        
        with open(metadata_file) as f:
            data = json.load(f)
        
        if data.get('session_type') != 'interactive':
            raise HTTPException(status_code=400, detail="Not an interactive session")
        
        return {"session": data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@app.post("/api/interactive/start")
async def start_interactive_standup():
    """Start an interactive standup session.
    
    Returns the first question audio.
    """
    # Generate first question
    first_question = "What did you work on yesterday?"
    
    # Generate audio for first question
    try:
        # Create session directory for interactive mode
        session_id = session_manager.create_session(
            persona_name="interactive",
            persona_archetype="live_user"
        )
        print(f"[Interactive] Starting session {session_id}")
        print(f"[Interactive] Generating audio for: {first_question}")
        question_audio = generate_interviewer_audio(first_question)
        print(f"[Interactive] Audio generated: {len(question_audio)} bytes")
        
        # Save to session directory
        audio_filename = f"interactive_q_{session_id}_0.wav"
        session_manager.save_audio(session_id, audio_filename, question_audio)
        print(f"[Interactive] Audio saved: {audio_filename}")
        
        return {
            "session_id": session_id,
            "question_text": first_question,
            "question_audio_url": f"/api/audio/{session_id}/{audio_filename}",
            "question_number": 0
        }
    except Exception as e:
        import traceback
        print(f"[Interactive] ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate question: {str(e)}")


@app.post("/api/interactive/record")
async def process_recording(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    question_number: int = Form(...)
):
    """Process user's recorded answer.
    
    Steps:
    1. Save uploaded audio
    2. Send to Smallest.ai Pulse (transcribe + emotion + word_timestamps)
    3. Analyze vagueness with GPT-4
    4. Generate next question based on response
    5. Convert question to audio
    6. Return analysis and next question
    """
    try:
        # Save uploaded audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Process with Smallest.ai Pulse API
        try:
            pulse_result = process_audio_file(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pulse API error: {str(e)}")
        finally:
            # Clean up temp file
            import os
            os.unlink(tmp_path)
        
        transcript = pulse_result.get('transcript', '')
        emotions = pulse_result.get('emotions', {})
        confidence = pulse_result.get('confidence', 1.0) if 'confidence' in pulse_result else 0.95
        
        # Check confidence
        if confidence < 0.7:
            return {
                "status": "low_confidence",
                "message": "Didn't catch that clearly. Could you please repeat?",
                "confidence": confidence
            }
        
        # Analyze with GPT-4 for conversational signals
        from openai import OpenAI
        import os as env_os
        
        openai_client = OpenAI(api_key=env_os.getenv("OPENAI_API_KEY"))
        
        analysis_prompt = f"""Analyze this standup response for stuck signals:

"{transcript}"

Return JSON with:
- vagueness_score (0-1, higher = more vague)
- hedging_words (list of hedging words found like "um", "like", "I think")
- specificity_score (0-1, higher = more specific)
- help_seeking (boolean, true if asking for help or open to assistance)
- summary (brief 1-line analysis)
"""
        
        analysis_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You analyze standup conversations for stuck signals. Return only valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        import json
        conversational_analysis = json.loads(analysis_response.choices[0].message.content)
        
        # Generate next question based on analysis
        next_question = generate_followup_question(
            transcript,
            conversational_analysis,
            question_number
        )
        
        # Generate audio for next question
        if next_question:
            question_audio = generate_interviewer_audio(next_question)
            audio_filename = f"interactive_q_{session_id}_{question_number + 1}.wav"
            session_manager.save_audio(session_id, audio_filename, question_audio)
            next_question_audio_url = f"/api/audio/{session_id}/{audio_filename}"
        else:
            next_question_audio_url = None
        
        # Calculate hesitation metrics
        hesitation_score = len(conversational_analysis.get('hedging_words', [])) / 20.0
        hesitation_score = min(hesitation_score, 1.0)
        
        # Estimate speech rate (rough approximation)
        word_count = len(transcript.split())
        estimated_duration = 10  # Assuming 10 second recording
        speech_rate = (word_count / estimated_duration) * 60 if estimated_duration > 0 else 0
        
        # Structure response to match frontend expectations
        return {
            "status": "success",
            "analysis": {
                "pulse_analysis": {
                    "transcript": transcript,
                    "confidence": confidence,
                    "emotions": emotions
                },
                "speech_patterns": {
                    "filler_word_count": len(conversational_analysis.get('hedging_words', [])),
                    "speech_rate_wpm": round(speech_rate),
                    "hesitation_score": round(hesitation_score, 2)
                },
                "conversational_signals": {
                    "vagueness": conversational_analysis.get('vagueness_score', 0),
                    "hedging_count": len(conversational_analysis.get('hedging_words', [])),
                    "specificity": conversational_analysis.get('specificity_score', 0),
                    "help_seeking": conversational_analysis.get('help_seeking', False)
                }
            },
            "next_question": next_question,
            "next_question_audio_url": next_question_audio_url,
            "is_complete": next_question is None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


def generate_followup_question(transcript: str, analysis: dict, question_number: int) -> str:
    """Generate adaptive follow-up question based on user's response."""
    
    # Define question flow
    if question_number >= 4:
        return None  # End after 5 questions
    
    vagueness = analysis.get('vagueness_score', 0)
    
    # Adaptive questioning based on vagueness
    if question_number == 0:
        # After "What did you work on yesterday?"
        if vagueness > 0.5:
            return "Can you be more specific about what you accomplished?"
        else:
            return "What are you working on today?"
    
    elif question_number == 1:
        if vagueness > 0.5:
            return "What exactly have you tried so far?"
        else:
            return "Are there any blockers or challenges?"
    
    elif question_number == 2:
        if vagueness > 0.5:
            return "Do you need any help or input from the team?"
        else:
            return "What's your plan for the rest of the day?"
    
    elif question_number == 3:
        return "Anything else you'd like to share?"
    
    return None


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voice-demo-server"}


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("AsyncStandup Voice Demo Server")
    print("=" * 70)
    print()
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
