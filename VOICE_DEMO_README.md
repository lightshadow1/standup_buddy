# AsyncStandup Voice Demo

**Browser-based interactive demo with TWO modes:**
1. **Demo Mode**: Watch AI-vs-AI standup conversations and hear stuck detection
2. **Live Mode**: Record YOUR OWN standup and get real-time analysis

## What This Is

A live voice demo that:
- **Demo Mode**: Generates realistic AI-vs-AI conversations with different personas
- **Live Mode**: Records your voice via microphone and analyzes in real-time
- Converts conversations to audio (Smallest.ai for interviewer, OpenAI TTS for personas)
- Shows comprehensive analysis: transcript, emotions, speech patterns, conversational signals
- Detects stuck engineers using hybrid approach (70% conversational + 30% emotional)

## Quick Start

### 1. Start the Server

```bash
uv run python voice_demo_server.py
```

The server will start at **http://localhost:8000**

### 2. Open in Browser

Visit http://localhost:8000 in your web browser.

### 3a. Try Demo Mode (AI-vs-AI)

1. Select "Demo Mode" (default)
2. Choose a persona from the dropdown (Steve, Sarah, Marcus, Priya, or Alex)
3. Click "Generate & Play Voice Demo"
4. Wait 2-3 minutes for generation (watch the progress indicator)
5. Click play buttons to hear the conversation
6. Review the stuck detection analysis at the bottom

### 3b. Try Live Mode (Your Voice)

1. Select "Live Mode"
2. Click "🎤 Start My Standup"
3. Grant microphone permissions when prompted
4. **Zero-click conversation flow** 🆕:
   - 🤖 AI asks question (blue indicator)
   - 🎤 Recording auto-starts (pink waveform animation)
   - Speak your answer naturally (5-15 seconds)
   - ⏹ Recording auto-stops after 2 seconds of silence
   - ⏳ Analysis runs automatically (orange spinner)
   - Repeat for next question
5. View instant analysis after each answer:
   - Transcript with confidence score
   - Emotions detected (happiness, sadness, frustration, anxiety)
   - Speech patterns (filler words, speech rate, hesitation)
   - Conversational signals (vagueness, hedging, specificity, help-seeking)
6. Answer all 5 questions
7. Review final stuck probability progression
8. Click "🔄 Start New Standup" to try again

**Live Mode Features**:
- ✅ **Auto-start recording** - Begins automatically after AI finishes speaking 🆕
- ✅ **Voice Activity Detection (VAD)** - Auto-stops after 2 seconds of silence 🆕
- ✅ **Animated phase indicators** - Visual feedback for AI speaking/listening/analyzing 🆕
- ✅ **Manual override** - "✋ Done Speaking" button available as backup 🆕
- ✅ Real-time Pulse API transcription + emotion detection
- ✅ Adaptive follow-up questions based on vagueness
- ✅ Low confidence warning (<70%) with retry option
- ✅ Final stuck probability chart across all exchanges

**User Experience**:
- **Before**: 2 clicks per exchange (Start + Stop)
- **After**: 0 clicks per exchange (fully automated)
- **Time saved**: ~5-10 seconds per exchange

## The 5 Personas

### 🎭 Steve - The Avoider
**Pattern**: Defensive stuck engineer
- Starts confident, becomes vague and defensive
- High hedging, avoids specifics
- Never seeks help
- Expected: 28% → 73% stuck probability

### 🎭 Sarah - The Overwhelmed  
**Pattern**: Self-aware but paralyzed
- Specific about problems but overwhelmed by options
- Shows analysis paralysis
- Eventually asks for help (protective factor)
- Expected: 20% → 50% stuck probability

### 🎭 Marcus - The Overconfident
**Pattern**: Confident but wrong direction
- Very specific and technical
- Sounds great but repeating same approach
- High specificity masks stuck state
- Expected: 18% → 45% stuck probability

### 🎭 Priya - The Healthy Progress
**Pattern**: Baseline/control
- Consistent low vagueness
- Appropriate help-seeking
- Clear progress indicators
- Expected: 15% → 22% stuck probability (stays healthy)

### 🎭 Alex - The Burnt Out
**Pattern**: Disengaged engineer
- Consistently high vagueness
- Flat, minimal responses
- Low energy throughout
- Expected: 35% → 65% stuck probability

## How It Works

### Generation Pipeline

```
1. Generate Conversations (GPT-4)
   ↓
2. Analyze Conversational Signals (GPT-4)
   ↓
3. Generate Audio
   - Questions: Smallest.ai Lightning (emily voice)
   - Answers: OpenAI TTS (persona-specific voices with emotional progression)
   ↓
4. Calculate Stuck Probability (70% conversational, 30% emotional)
   ↓
5. Serve Audio + Analysis via Web UI
```

### Voice Mapping

**Interviewer**: Smallest.ai Lightning - `emily` (professional, consistent)

**Personas** (OpenAI TTS with emotional instructions):
- Steve → `onyx` (defensive tone, declining confidence)
- Sarah → `shimmer` (stressed, anxious)
- Marcus → `echo` (confident, authoritative)
- Priya → `alloy` (calm, collaborative)
- Alex → `fable` (flat, disengaged)

## API Endpoints

The server provides a REST API:

**Demo Mode**:
- `GET /` - Serve HTML frontend
- `GET /api/personas` - List available personas
- `POST /api/generate` - Generate voice demo (background task)
- `GET /api/session/{id}/status` - Check generation status
- `GET /api/session/{id}` - Get session data
- `GET /api/audio/{session_id}/{filename}` - Stream audio file
- `GET /api/sessions` - List all sessions
- `DELETE /api/session/{id}` - Delete session
- `POST /api/cleanup` - Clean up old sessions (>24 hours)

**Live Mode** (NEW):
- `POST /api/interactive/start` - Start live standup session, returns first question audio
- `POST /api/interactive/record` - Upload audio recording, analyze with Pulse API + GPT-4, return analysis + next question

API docs available at: http://localhost:8000/docs

## File Structure

```
voice_demo_server.py              # FastAPI backend
static/
  └── voice_demo.html             # Browser UI
src/async_standup/
  ├── voice_generator.py          # Audio generation
  └── voice_session.py            # Session management
data/
  ├── voice_sessions/             # Generated audio files
  │   └── {session_id}/
  │       ├── q_1_0.wav          # Question audio
  │       └── a_1_0.mp3          # Answer audio
  └── voice_metadata/             # Session metadata
      └── {session_id}.json
```

## Generation Time

- **5 days × ~4 exchanges/day × 2 audio files** = ~40 TTS API calls
- **Estimated time**: 2-3 minutes per persona
- **Progress**: Shown in browser with status updates

## Tips for Demo

### For Judges

1. **Start with Steve** - Clear stuck pattern that's easy to hear
2. **Contrast with Priya** - Show healthy engineer for comparison
3. **Highlight audio cues**:
   - Day 1 Steve: Confident, specific
   - Day 3 Steve: Vague, hesitant ("um", "kind of")
   - Day 5 Steve: Defeated, exhausted
4. **Point out analysis** - System correctly flags WARNING by Day 2

### For Recording (Backup)

If you need a pre-recorded version:
1. Run demo in browser
2. Use macOS Screen Recording (Cmd+Shift+5) with audio
3. Or use OBS Studio for higher quality
4. Export as MP4 with audio

## Cleanup

Sessions auto-expire after 24 hours. Manual cleanup:

```bash
curl -X POST http://localhost:8000/api/cleanup
```

Or delete specific session via browser dev tools:
```javascript
fetch('/api/session/{session_id}', {method: 'DELETE'})
```

## Troubleshooting

### Demo Mode Issues

**"Failed to generate interviewer audio"**
- Check `SMALLEST_API_KEY` in `.env`
- Test: `uv run python -m src.async_standup.voice_generator`

**"Failed to generate persona audio"**
- Check `OPENAI_API_KEY` in `.env`
- Ensure sufficient API credits

**Audio won't play in browser**
- Check browser console for errors
- Try different browser (Chrome/Firefox recommended)
- Verify audio files exist in `data/voice_sessions/{session_id}/`

**Generation stuck/timeout**
- Check server logs for errors
- Restart server: Ctrl+C then `uv run python voice_demo_server.py`
- Delete incomplete session: `rm -rf data/voice_sessions/{session_id}`

### Live Mode Issues

**"Microphone access required"**
- Grant microphone permission in browser settings
- Chrome: chrome://settings/content/microphone
- Firefox: about:preferences#privacy → Permissions → Microphone
- Safari: Preferences → Websites → Microphone
- Try refreshing the page after granting permission

**"Recording too short"**
- Speak for at least 3 seconds
- Check microphone is working (test in System Settings)
- Try speaking louder/closer to mic

**"Low confidence" warning**
- Transcript confidence < 70%
- Options:
  - Click "🔄 Re-record Answer" to retry with clearer audio
  - Click "➡️ Continue Anyway" to proceed with current transcript
- Tips for better confidence:
  - Reduce background noise
  - Speak clearly at normal pace
  - Check microphone positioning

**"Analysis failed"**
- Check `SMALLEST_API_KEY` in `.env` (Pulse API)
- Check `OPENAI_API_KEY` in `.env` (GPT-4 analysis)
- Verify API credits are sufficient
- Check server logs for error details

**Recording not starting**
- Microphone may be in use by another app
- Close other apps using microphone (Zoom, Discord, etc.)
- Restart browser

**Browser Compatibility**
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ⚠️ Safari (may need fallback audio format)
- ❌ Internet Explorer (not supported)

## Cost Estimate

**Demo Mode** - Per 5-day session (~20 exchanges):
- **GPT-4o** (conversations + analysis): ~$0.04-0.08
- **OpenAI TTS** (persona audio): ~$0.02-0.04
- **Smallest.ai Lightning** (interviewer audio): Contact Smallest.ai for pricing

**Total per demo**: ~$0.06-0.12

**Live Mode** - Per standup (5 questions):
- **Smallest.ai Pulse** (transcription + emotions): 5 recordings × pricing per call
- **Smallest.ai Lightning** (question audio): 5 questions × pricing per call
- **GPT-4o** (conversational analysis + adaptive questions): ~$0.02-0.04

**Total per live standup**: Varies by Smallest.ai plan + ~$0.02-0.04 for GPT-4o

## Next Steps

### Future Enhancements
- [ ] Auto-play mode (conversation plays automatically)
- [ ] Playback speed control
- [ ] Download audio as MP3/MP4
- [ ] Compare two personas side-by-side
- [ ] Add emotional visualization (waveform analysis)
- [ ] Slack bot integration for real standups

### Production Deployment
- [ ] Add authentication (JWT tokens)
- [ ] Rate limiting per user
- [ ] Session storage in Redis/database
- [ ] CDN for audio file serving
- [ ] Docker containerization

## Credits

**Built with**:
- FastAPI (backend)
- Vanilla JavaScript (frontend)
- OpenAI GPT-4o + TTS (conversations + persona audio)
- Smallest.ai Lightning (interviewer audio)
- Python 3.13 + uv (package management)

**Personas designed to test**:
- ✅ Easy detection (Steve, Alex)
- ⚠️ Moderate detection (Sarah)
- 🚨 Hard detection (Marcus - false negative risk)
- ✅ False positive prevention (Priya)

---

**Demo ready!** Start the server and open http://localhost:8000 to begin. 🎤
