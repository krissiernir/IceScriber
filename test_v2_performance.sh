#!/bin/bash
# Test script for comparing v1 vs v2 transcription performance
# Usage: ./test_v2_performance.sh <audio_file.mp3>

if [ -z "$1" ]; then
    echo "Usage: ./test_v2_performance.sh <audio_file_in_audio_chapters>"
    echo "Example: ./test_v2_performance.sh 001_Intro.mp3"
    exit 1
fi

AUDIO_FILE="$1"
AUDIO_PATH="audio_chapters/${AUDIO_FILE}"
JSON_PATH="audio_chapters/${AUDIO_FILE}.json"
V2_JSON_PATH="audio_chapters/${AUDIO_FILE}.v2.json"

echo "=== Transcription Performance Test: v1 vs v2 ==="
echo "Testing file: ${AUDIO_FILE}"
echo ""

# Check if file exists
if [ ! -f "$AUDIO_PATH" ]; then
    echo "❌ Error: ${AUDIO_PATH} not found"
    exit 1
fi

# Backup v1 if it exists
if [ -f "$JSON_PATH" ]; then
    echo "📦 Backing up v1 transcription..."
    mkdir -p audio_chapters/v1_backup
    cp "${JSON_PATH}" "audio_chapters/v1_backup/"
    cp "audio_chapters/${AUDIO_FILE}_TRANSCRIPT.txt" "audio_chapters/v1_backup/" 2>/dev/null
    cp "audio_chapters/${AUDIO_FILE}_MARKDOWN.md" "audio_chapters/v1_backup/" 2>/dev/null
    cp "audio_chapters/${AUDIO_FILE}_LLM.txt" "audio_chapters/v1_backup/" 2>/dev/null
    echo "✓ v1 files backed up to audio_chapters/v1_backup/"

    # Delete JSON to allow re-transcription
    rm "${JSON_PATH}"
fi

# Test v2
echo ""
echo "🚀 Running v2 transcription..."
echo "Start time: $(date '+%H:%M:%S')"
START_TIME=$(date +%s)

python chapterbatch_v2.py

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "End time: $(date '+%H:%M:%S')"
echo "Duration: ${DURATION} seconds"

# Analysis
echo ""
echo "=== Results ==="

if [ -f "$V2_JSON_PATH" ]; then
    echo "✓ v2 transcription completed successfully"

    # Count segments
    SEGMENT_COUNT=$(python3 -c "import json; print(len(json.load(open('${V2_JSON_PATH}'))['segments']))")
    echo "  Segments: ${SEGMENT_COUNT}"

    # Check for repetitions (simple heuristic: look for repeated 3-word sequences)
    echo ""
    echo "🔍 Checking for repetition artifacts..."
    TRANSCRIPT_V2="audio_chapters/${AUDIO_FILE}_TRANSCRIPT.v2.txt"

    if [ -f "$TRANSCRIPT_V2" ]; then
        # Count lines with potential repetitions
        REPETITIONS=$(grep -o -E '(\w+)\s+\1\s+\1' "$TRANSCRIPT_V2" | wc -l | xargs)
        echo "  3-word repetition loops: ${REPETITIONS}"

        if [ "$REPETITIONS" -gt 0 ]; then
            echo "  Examples:"
            grep -o -E '(\w+)\s+\1\s+\1' "$TRANSCRIPT_V2" | head -3
        fi
    fi

    # Show metadata
    echo ""
    echo "📊 Metadata:"
    python3 -c "
import json
data = json.load(open('${V2_JSON_PATH}'))
meta = data['metadata']
print(f\"  Model: {meta['model'].split('/')[-1]}\")
print(f\"  Version: {meta.get('version', 'v1')}\")
if 'optimizations' in meta:
    print(f\"  Optimizations:\")
    for opt in meta['optimizations']:
        print(f\"    - {opt}\")
"
else
    echo "❌ v2 transcription failed - no output file found"
fi

echo ""
echo "=== Comparison Files ==="
echo "v1 backup: audio_chapters/v1_backup/${AUDIO_FILE}.json"
echo "v2 output: ${V2_JSON_PATH}"
echo ""
echo "To compare manually:"
echo "  diff audio_chapters/v1_backup/${AUDIO_FILE}_TRANSCRIPT.txt audio_chapters/${AUDIO_FILE}_TRANSCRIPT.v2.txt"
echo ""
echo "✅ Test complete!"
