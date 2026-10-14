#!/usr/bin/env python3
"""
IceScriber English Edition - Optimized Transcription Engine
Uses Distil-Whisper for 6x faster English transcription

Features:
- Distil-Whisper Large v3 (6x faster than standard Whisper)
- SDPA attention for Apple Silicon
- float16 precision on MPS (faster, Distil-Whisper handles it better)
- Anti-hallucination parameters
- Same JSON-first output format as IceScriber

Usage:
    python chapterbatch_english.py
    python chapterbatch_english.py --book-dir data/books/the-hate-u-give
"""

import sys
import argparse
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import librosa
import os
import json
from pathlib import Path
from tqdm import tqdm

# Add src/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from paths import INPUT_ENGLISH

# --- SETTINGS ---
DEFAULT_INPUT_FOLDER = str(INPUT_ENGLISH)
MODEL_ID = "distil-whisper/distil-large-v3"  # 6x faster, 50% smaller

# Sliding Window Settings (using pipeline's built-in chunking)
CHUNK_LENGTH_S = 30  # 30 second chunks
STRIDE_LENGTH_S = 5   # 5 second stride (overlap)

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def build_json_transcript(audio_path, segments, language="english"):
    """Build JSON structure as source of truth for transcript."""
    json_data = {
        "metadata": {
            "audio_file": os.path.basename(audio_path),
            "language": language,
            "model": MODEL_ID,
            "chunk_length_s": CHUNK_LENGTH_S,
            "stride_length_s": STRIDE_LENGTH_S,
            "version": "english-distil-v1",
            "optimizations": [
                "Distil-Whisper (6x faster than standard)",
                "SDPA attention (Apple Neural Engine)",
                "float16 precision on MPS",
                "Anti-hallucination parameters"
            ]
        },
        "segments": segments
    }
    return json_data

def save_json_transcript(json_data, output_path):
    """Save JSON transcript to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

def json_to_formatted_text(json_data, include_timestamps=True):
    """Convert JSON segments to formatted text."""
    lines = []
    for segment in json_data["segments"]:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"]

        if include_timestamps:
            lines.append(f"[{timestamp}] {text}")
        else:
            lines.append(text)

    return "\n".join(lines)

def format_markdown(text):
    """Format as markdown-friendly text."""
    lines = text.split('\n')
    paragraphs = []
    current_paragraph = []
    line_count = 0

    for line in lines:
        # Remove timestamp, keep content
        if line.strip().startswith('['):
            bracket_end = line.find(']')
            if bracket_end != -1:
                content = line[bracket_end + 1:].strip()
            else:
                content = line.strip()
        else:
            content = line.strip()

        if content:
            current_paragraph.append(content)
            line_count += 1

            # Create paragraph break every 5 chunks
            if line_count >= 5:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                line_count = 0

    # Add remaining content
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))

    return '\n\n'.join(paragraphs)

def format_llm_optimized(text):
    """Format for LLM ingestion."""
    lines = text.split('\n')
    content_lines = []

    for line in lines:
        # Remove timestamp
        if line.strip().startswith('['):
            bracket_end = line.find(']')
            if bracket_end != -1:
                content = line[bracket_end + 1:].strip()
            else:
                content = line.strip()
        else:
            content = line.strip()

        if content:
            content_lines.append(content)

    # Join with single spaces
    text_output = ' '.join(content_lines)

    # Clean up multiple spaces
    while '  ' in text_output:
        text_output = text_output.replace('  ', ' ')

    return text_output

def transcribe_all_chapters(input_folder: str = DEFAULT_INPUT_FOLDER, book_dir: Path = None):
    # 1. Setup Device
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using Device: {device}")
    print(f"🚀 IceScriber English Edition - Distil-Whisper Optimized")
    INPUT_FOLDER = input_folder

    # 2. Load AI with optimizations
    print("Loading Distil-Whisper model...")

    # Distil-Whisper can handle float16 on MPS (unlike full Whisper)
    torch_dtype = torch.float16 if device == "mps" else torch.float32

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        dtype=torch_dtype,  # float16 for speed on MPS
        low_cpu_mem_usage=True,
        use_safetensors=True,
        attn_implementation="sdpa"  # Apple Neural Engine optimization
    ).to(device)

    processor = AutoProcessor.from_pretrained(MODEL_ID)

    # 3. Create pipeline (Distil-Whisper works great with pipeline)
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=CHUNK_LENGTH_S,
        stride_length_s=(STRIDE_LENGTH_S, STRIDE_LENGTH_S),  # (left, right) stride
        batch_size=1,  # Process one at a time for stability
        torch_dtype=torch_dtype,
        device=device,
        return_timestamps=True,  # Get word-level timestamps
        generate_kwargs={
            "language": "english",
            "task": "transcribe",
            "repetition_penalty": 1.1,  # Anti-hallucination
            "no_repeat_ngram_size": 3   # Block 3-word loops
        }
    )

    print("✓ Distil-Whisper pipeline initialized")
    print(f"  Using: {torch_dtype}")
    print(f"  Chunk size: {CHUNK_LENGTH_S}s with {STRIDE_LENGTH_S}s stride")

    # 4. Determine output folders
    INPUT_FOLDER = Path(INPUT_FOLDER)
    if book_dir:
        transcripts_folder = book_dir / "transcripts"
        backup_folder = book_dir / "backup"
    else:
        transcripts_folder = INPUT_FOLDER
        backup_folder = INPUT_FOLDER / "backup"
    transcripts_folder.mkdir(parents=True, exist_ok=True)
    backup_folder.mkdir(parents=True, exist_ok=True)

    # 5. Find all audio files
    if not INPUT_FOLDER.exists():
        INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Created folder: {INPUT_FOLDER}")
        print(f"   Place your English audio files there and run again.")
        return

    audio_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp3', '.m4a', '.wav'))]
    audio_files.sort()

    if not audio_files:
        print(f"\n❌ No audio files found in {INPUT_FOLDER}")
        print("   Supported formats: .mp3, .m4a, .wav")
        return

    print(f"\nFound {len(audio_files)} files to transcribe.")

    # 6. Process each file
    for filename in audio_files:
        audio_path = str(INPUT_FOLDER / filename)
        stem = Path(filename).stem.lower()
        json_path = str(transcripts_folder / f"{stem}.json")

        # Skip if already transcribed
        if os.path.exists(json_path):
            print(f"✓ Skipping {filename} (already transcribed)")
            continue

        print(f"\n--- Processing: {filename} ---")

        # Transcribe using pipeline (handles chunking automatically with Gaussian blending)
        result = pipe(audio_path)

        # Extract segments from pipeline output
        segments = []
        if 'chunks' in result:
            # Word-level timestamps
            for chunk in result['chunks']:
                segments.append({
                    "start": chunk['timestamp'][0] if chunk['timestamp'][0] is not None else 0,
                    "end": chunk['timestamp'][1] if chunk['timestamp'][1] is not None else 0,
                    "text": chunk['text'].strip()
                })
        else:
            # Fallback: single segment
            segments.append({
                "start": 0,
                "end": 0,
                "text": result['text'].strip()
            })

        # Build JSON
        json_data = build_json_transcript(audio_path, segments, language="english")

        # Save JSON to transcripts/
        save_json_transcript(json_data, json_path)

        # Derive text formats and save to backup/
        formatted_timestamps = json_to_formatted_text(json_data, include_timestamps=True)
        formatted_llm = format_llm_optimized(formatted_timestamps)

        output_file_ts = str(backup_folder / f"{stem}_transcript.txt")
        with open(output_file_ts, "w", encoding="utf-8") as f:
            f.write(formatted_timestamps)

        output_file_llm_txt = str(backup_folder / f"{stem}_llm.txt")
        with open(output_file_llm_txt, "w", encoding="utf-8") as f:
            f.write(formatted_llm)

        print(f"Done! Saved JSON: {json_path}")
        print(f"       TRANSCRIPT: {output_file_ts}")
        print(f"       LLM:        {output_file_llm_txt}")

    print("\n✅ ALL FILES FINISHED!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IceScriber English Edition - Distil-Whisper Transcription")
    parser.add_argument("--book-dir", type=str, default=None,
                        help="Book directory (e.g., data/books/the-hate-u-give). Reads audio from <book-dir>/audio/")
    parser.add_argument("--input-dir", type=str, default=None,
                        help="Direct path to folder containing audio files")
    args = parser.parse_args()

    if args.book_dir:
        book_dir = Path(args.book_dir)
        input_folder = str(book_dir / "audio")
        if not book_dir.exists():
            book_dir.mkdir(parents=True, exist_ok=True)
            (book_dir / "audio").mkdir(exist_ok=True)
            print(f"Created book directory: {book_dir}")
            print(f"Place your audio files in: {book_dir / 'audio'}/")
        transcribe_all_chapters(input_folder=input_folder, book_dir=book_dir)
    elif args.input_dir:
        transcribe_all_chapters(input_folder=args.input_dir)
    else:
        transcribe_all_chapters(input_folder=DEFAULT_INPUT_FOLDER)
