"""
IceScriber shared transcription core.

The full "fix and chunk" pipeline, ported from
`scripts/transcription/chapterbatch_v2.py` so it can be reused for a single
file (e.g. meeting mode) instead of only folder batches.

Stages (identical to chapterbatch_v2):
  1. Chunking          - sliding window, 30s window / 5s stride (25s overlap)
  2. Anti-hallucination - repetition_penalty=1.1, no_repeat_ngram_size=3
  3. Overlap dedup     - find_overlap_end(), longest-common-substring @ 85%
  4. Text fixing       - format_text_with_punctuation()
  5. Format derivation - JSON source-of-truth -> timestamped / markdown / LLM

NOTE: These functions are duplicated from chapterbatch_v2.py for now so the
proven batch script stays untouched. A later cleanup should make
chapterbatch_v2 import from here (see meeting-mode design spec).

Unlike chapterbatch_v2, this module does NOT force TRANSFORMERS_OFFLINE, so the
model can be downloaded on first use if the cache is empty.
"""

import os
import json

import torch
import librosa
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from tqdm import tqdm

# --- SETTINGS (match chapterbatch_v2.py) ---
MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"
WINDOW_SIZE_SECONDS = 30      # Size of each chunk
STRIDE_SECONDS = 5            # How much to shift for next window
OVERLAP_SECONDS = WINDOW_SIZE_SECONDS - STRIDE_SECONDS  # 25 seconds of context


# ---------------------------------------------------------------------------
# Text formatting helpers (ported verbatim from chapterbatch_v2.py)
# ---------------------------------------------------------------------------

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_text_with_punctuation(text):
    """
    Add smart punctuation and formatting to raw transcription.
    - Add periods at sentence boundaries
    - Capitalize sentence starts
    """
    lines = text.split('\n')
    formatted_lines = []

    for line in lines:
        # Preserve timestamp if present
        if line.strip().startswith('['):
            bracket_end = line.find(']')
            if bracket_end != -1:
                timestamp = line[:bracket_end + 1]
                content = line[bracket_end + 1:].strip()
            else:
                timestamp = ''
                content = line.strip()
        else:
            timestamp = ''
            content = line.strip()

        if not content:
            continue

        # Split into sentences using capitalization heuristic
        words = content.split()
        sentences = []
        current_sentence = []

        for i, word in enumerate(words):
            current_sentence.append(word)
            is_last_word = (i == len(words) - 1)
            next_word_capitalized = (i + 1 < len(words) and len(words[i+1]) > 0 and words[i+1][0].isupper()) if i + 1 < len(words) else False

            # Heuristic: sentence boundary when next word is capitalized or at end
            if (is_last_word or next_word_capitalized) and len(current_sentence) > 2:
                sentences.append(' '.join(current_sentence))
                current_sentence = []

        if current_sentence:
            sentences.append(' '.join(current_sentence))

        # Format each sentence with proper punctuation
        formatted_sentences = []
        for sent in sentences:
            if sent.strip():
                sent = sent.strip()
                # Add period if missing
                if not sent.endswith(('.', '?', '!', ',', ':', ';')):
                    sent += '.'
                # Capitalize first letter
                if sent and sent[0].islower():
                    sent = sent[0].upper() + sent[1:]
                formatted_sentences.append(sent)

        formatted_text = ' '.join(formatted_sentences)
        if timestamp:
            formatted_lines.append(f"{timestamp} {formatted_text}")
        else:
            formatted_lines.append(formatted_text)

    return '\n'.join(formatted_lines)


def format_markdown(text):
    """
    Output format: markdown-friendly readable format.
    - Removes timestamps
    - Adds clean paragraph breaks every ~5 lines (roughly every 25 seconds)
    """
    lines = text.split('\n')
    paragraphs = []
    current_paragraph = []
    line_count = 0

    for line in lines:
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
            if line_count >= 5:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                line_count = 0

    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))

    return '\n\n'.join(paragraphs)


def format_llm_optimized(text):
    """
    Output format: maximum LLM readiness.
    - No timestamps or special formatting
    - Clean continuous text, single spaces
    """
    lines = text.split('\n')
    content_lines = []

    for line in lines:
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

    text_output = ' '.join(content_lines)
    while '  ' in text_output:
        text_output = text_output.replace('  ', ' ')

    return text_output


def find_overlap_end(prev_text, curr_text, min_overlap_words=5):
    """
    Find where prev_text's end overlaps with curr_text's beginning by looking
    for the longest common substring (word-level, 85% match threshold).
    """
    prev_norm = prev_text.lower().split()
    curr_norm = curr_text.lower().split()

    for overlap_len in range(min(len(prev_norm), len(curr_norm), 30), min_overlap_words - 1, -1):
        prev_end = prev_norm[-overlap_len:]
        for start_idx in range(len(curr_norm) - overlap_len + 1):
            curr_start = curr_norm[start_idx:start_idx + overlap_len]
            matches = sum(1 for p, c in zip(prev_end, curr_start) if p == c)
            match_pct = matches / overlap_len
            if match_pct >= 0.85:
                return start_idx + overlap_len

    return 0


def build_json_transcript(audio_path, segments, language="icelandic"):
    """Build JSON structure as source of truth for transcript."""
    return {
        "metadata": {
            "audio_file": os.path.basename(audio_path),
            "language": language,
            "model": MODEL_ID,
            "window_size_seconds": WINDOW_SIZE_SECONDS,
            "stride_seconds": STRIDE_SECONDS,
            "overlap_seconds": OVERLAP_SECONDS,
            "version": "v2",
            "optimizations": [
                "SDPA attention (Apple Neural Engine)",
                "Anti-hallucination parameters (repetition_penalty=1.1, no_repeat_ngram_size=3)"
            ]
        },
        "segments": segments
    }


def json_to_formatted_text(json_data, include_timestamps=True, apply_punctuation=False):
    """Convert JSON segments to formatted text."""
    lines = []
    for segment in json_data["segments"]:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"]

        if apply_punctuation:
            text = format_text_with_punctuation(f"[{timestamp}] {text}")
            if "] " in text:
                text = text.split("] ", 1)[1]

        if include_timestamps:
            lines.append(f"[{timestamp}] {text}")
        else:
            lines.append(text)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model loading + single-file transcription
# ---------------------------------------------------------------------------

def load_model():
    """Load the Icelandic Whisper model + processor once. Returns (processor, model, device)."""
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using Device: {device}")
    print("Loading AI model (first run may download ~1.5 GB)...")

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        dtype=torch.float32,        # Required for MPS stability (avoid NaN)
        low_cpu_mem_usage=True,
        attn_implementation="sdpa"  # Apple Silicon optimization
    ).to(device)

    print("✓ Model loaded with SDPA attention optimization")
    return processor, model, device


def transcribe(audio_path, processor=None, model=None, device=None, language="icelandic"):
    """
    Transcribe a single audio file through the full IceScriber pipeline.

    Returns a dict:
        {
          "json": <source-of-truth JSON dict>,
          "text_timestamped": <str>,   # [HH:MM:SS] punctuated text
          "text_markdown": <str>,
          "text_llm": <str>,           # clean continuous text, best for LLM input
        }
    """
    if processor is None or model is None:
        processor, model, device = load_model()

    filename = os.path.basename(audio_path)

    # Load audio at 16kHz
    speech, sr = librosa.load(audio_path, sr=16000)
    chunk_len = int(WINDOW_SIZE_SECONDS * sr)
    stride_len = int(STRIDE_SECONDS * sr)

    chunks = []
    chunk_times = []
    for i in range(0, len(speech), stride_len):
        chunk_start_time = i / sr
        if i + chunk_len <= len(speech):
            chunks.append(speech[i:i + chunk_len])
            chunk_times.append(chunk_start_time)
        elif i < len(speech):  # Last (shorter) chunk
            chunks.append(speech[i:])
            chunk_times.append(chunk_start_time)

    # Transcribe chunks (anti-hallucination params)
    chunk_texts = []
    for chunk in tqdm(chunks, desc=f"Transcribing {filename}"):
        inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
        input_features = inputs.input_features.to(device)
        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                language="icelandic",
                task="transcribe",
                repetition_penalty=1.1,
                no_repeat_ngram_size=3,
            )
        text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        chunk_texts.append(text)

    # Intelligent overlap deduplication -> JSON segments
    segments = []
    current_segment_start = chunk_times[0] if chunk_times else 0
    current_segment_text = ""

    for idx, text in enumerate(chunk_texts):
        start_time = chunk_times[idx]
        if idx == 0:
            current_segment_text = text
            current_segment_start = start_time
        else:
            prev_text = chunk_texts[idx - 1]
            skip_words = find_overlap_end(prev_text, text)
            words = text.split()
            if skip_words < len(words):
                new_text = " ".join(words[skip_words:])
                if new_text.strip():
                    if current_segment_text.strip():
                        segments.append({
                            "start": current_segment_start,
                            "end": start_time,
                            "text": current_segment_text.strip()
                        })
                    current_segment_text = new_text.strip()
                    current_segment_start = start_time

    if current_segment_text.strip():
        segments.append({
            "start": current_segment_start,
            "end": current_segment_start + WINDOW_SIZE_SECONDS,
            "text": current_segment_text.strip()
        })

    # Build JSON source of truth, apply punctuation fixing to each segment
    json_data = build_json_transcript(audio_path, segments, language=language)
    for segment in json_data["segments"]:
        segment["text"] = format_text_with_punctuation(segment["text"])

    # Derive all formats from JSON
    text_timestamped = json_to_formatted_text(json_data, include_timestamps=True, apply_punctuation=False)
    text_markdown = format_markdown(text_timestamped)
    text_llm = format_llm_optimized(text_timestamped)

    return {
        "json": json_data,
        "text_timestamped": text_timestamped,
        "text_markdown": text_markdown,
        "text_llm": text_llm,
    }
