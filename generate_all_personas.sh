#!/bin/bash

# Generate all personas for AsyncStandup demo

BASE_URL="http://localhost:8000/api"
PERSONAS=("sarah" "marcus" "alex")

for persona in "${PERSONAS[@]}"; do
    echo "=========================================="
    echo "Generating $persona..."
    echo "=========================================="
    
    # Start generation
    session_id=$(curl -s -X POST "$BASE_URL/generate" \
        -H "Content-Type: application/json" \
        -d "{\"persona\":\"$persona\"}" | \
        python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
    
    echo "$persona session ID: $session_id"
    
    # Poll for completion (max 3 minutes = 60 checks × 3 seconds)
    echo "Waiting for generation to complete..."
    for i in {1..60}; do
        gen_status=$(curl -s "$BASE_URL/session/$session_id/status" | \
            python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
        
        if [ "$gen_status" = "complete" ]; then
            echo "✓ $persona complete!"
            
            # Copy audio files to organized folder
            cp data/voice_sessions/$session_id/* persona_audio_files/$persona/
            echo "✓ Audio files copied to persona_audio_files/$persona/"
            break
        elif [ "$gen_status" = "generating" ]; then
            echo "  Progress: $i/60 (still generating...)"
        else
            echo "  Unexpected status: $gen_status"
        fi
        
        sleep 3
    done
    
    echo ""
done

echo "=========================================="
echo "✓ All personas generated!"
echo "=========================================="
echo ""
echo "Audio files are in:"
echo "  persona_audio_files/steve/"
echo "  persona_audio_files/priya/"
echo "  persona_audio_files/sarah/"
echo "  persona_audio_files/marcus/"
echo "  persona_audio_files/alex/"
