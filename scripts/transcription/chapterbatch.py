import sys
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import librosa
import os
import time
import json
from pathlib import Path
from tqdm import tqdm

# Add src/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from paths import INPUT_ICELANDIC

# Force Offline
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# --- SETTINGS ---
INPUT_FOLDER = str(INPUT_ICELANDIC)
MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"

# Sliding Window Settings
WINDOW_SIZE_SECONDS = 30  # Size of each chunk
STRIDE_SECONDS = 5        # How much to shift for next window (smaller = more overlap)
OVERLAP_SECONDS = WINDOW_SIZE_SECONDS - STRIDE_SECONDS  # 25 seconds of context

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

def format_timestamps(text):
    """
    Output format: timestamps with raw text for reference.
    [HH:MM:SS] text...
    """
    return text

def format_markdown(text):
    """
    Output format: markdown-friendly readable format.
    - Removes timestamps
    - Adds clean paragraph breaks every ~5 lines (roughly every 25 seconds)
    - UTF-8 Icelandic characters preserved
    """
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
            
            # Create paragraph break every 5 chunks (~25 seconds)
            if line_count >= 5:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                line_count = 0
    
    # Add remaining content
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    return '\n\n'.join(paragraphs)

def format_llm_optimized(text):
    """
    Output format: maximum LLM readiness.
    - No timestamps or special formatting
    - Clean continuous text
    - Single spaces, proper paragraph breaks
    - UTF-8 Icelandic characters preserved
    - Optimized for LLM ingestion (minimal preprocessing needed)
    """
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
    
    # Join with single spaces for continuous text
    text_output = ' '.join(content_lines)
    
    # Clean up multiple spaces
    while '  ' in text_output:
        text_output = text_output.replace('  ', ' ')
    
    return text_output

def find_overlap_end(prev_text, curr_text, min_overlap_words=5):
    """
    Find where prev_text's end overlaps with curr_text's beginning by looking for
    the longest common substring. More robust than word-level matching.
    """
    # Normalize text for comparison
    prev_norm = prev_text.lower().split()
    curr_norm = curr_text.lower().split()
    
    max_overlap_idx = 0
    
    # Look for the longest sequence of matching words at the boundary
    # Search backwards from the end of prev_text
    for overlap_len in range(min(len(prev_norm), len(curr_norm), 30), min_overlap_words - 1, -1):
        prev_end = prev_norm[-overlap_len:]
        
        # Check all possible positions in current text
        for start_idx in range(len(curr_norm) - overlap_len + 1):
            curr_start = curr_norm[start_idx:start_idx + overlap_len]
            
            # Calculate match percentage (allow for minor variations)
            matches = sum(1 for p, c in zip(prev_end, curr_start) if p == c)
            match_pct = matches / overlap_len
            
            if match_pct >= 0.85:  # 85% match threshold for robustness
                return start_idx + overlap_len
    
    return 0

def build_json_transcript(audio_path, segments, language="icelandic"):
    """
    Build JSON structure as source of truth for transcript.
    
    segments: list of {"start": time, "end": time, "text": content}
    """
    json_data = {
        "metadata": {
            "audio_file": os.path.basename(audio_path),
            "language": language,
            "model": MODEL_ID,
            "window_size_seconds": WINDOW_SIZE_SECONDS,
            "stride_seconds": STRIDE_SECONDS,
            "overlap_seconds": OVERLAP_SECONDS
        },
        "segments": segments
    }
    return json_data

def save_json_transcript(json_data, output_path):
    """Save JSON transcript to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

def json_to_formatted_text(json_data, include_timestamps=True, apply_punctuation=False):
    """Convert JSON segments to formatted text."""
    lines = []
    for segment in json_data["segments"]:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"]
        
        if apply_punctuation:
            text = format_text_with_punctuation(f"[{timestamp}] {text}")
            # Remove timestamp prefix from punctuation result
            if "] " in text:
                text = text.split("] ", 1)[1]
        
        if include_timestamps:
            lines.append(f"[{timestamp}] {text}")
        else:
            lines.append(text)
    
    return "\n".join(lines)

def transcribe_all_chapters():
    # 1. Setup Device
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using Device: {device}")

    # 2. Load AI (only do this once for all files)
    print("Loading AI model...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID, torch_dtype=torch.float32, low_cpu_mem_usage=True
    ).to(device)

    # 3. Find all audio files in the folder
    audio_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp3', '.m4a', '.wav'))]
    audio_files.sort() # Ensure they are in order: Chapter 1, Chapter 2...
    
    print(f"Found {len(audio_files)} chapters to transcribe.")

    # 4. Loop through each file
    for filename in audio_files:
        audio_path = os.path.join(INPUT_FOLDER, filename)
        json_path = os.path.join(INPUT_FOLDER, f"{filename}.json")
        
        # Skip if already transcribed (JSON exists)
        if os.path.exists(json_path):
            print(f"✓ Skipping {filename} (already transcribed)")
            continue
        
        print(f"\n--- Processing: {filename} ---")
        
        # Load audio
        speech, sr = librosa.load(audio_path, sr=16000)
        chunk_len = int(WINDOW_SIZE_SECONDS * sr)
        stride_len = int(STRIDE_SECONDS * sr)
        chunks = []
        chunk_times = []  # Track start time of each chunk
        
        for i in range(0, len(speech), stride_len):
            chunk_start_time = i / sr  # Convert sample index to seconds
            if i + chunk_len <= len(speech):
                chunks.append(speech[i:i + chunk_len])
                chunk_times.append(chunk_start_time)
            elif i < len(speech):  # Last chunk (may be shorter than window size)
                chunks.append(speech[i:])
                chunk_times.append(chunk_start_time)
        
        chunk_texts = []
        
        # Transcribe chunks
        for chunk in tqdm(chunks, desc=f"Transcribing {filename}"):
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            input_features = inputs.input_features.to(device)

            with torch.no_grad():
                predicted_ids = model.generate(input_features, language="icelandic", task="transcribe")

            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            chunk_texts.append(text)

        # Intelligent Deduplication: Remove overlapping text and add timestamps
        full_chapter_transcript = []
        segments = []  # Build segments for JSON
        current_segment_start = chunk_times[0] if chunk_times else 0
        current_segment_text = ""
        
        for idx, text in enumerate(chunk_texts):
            start_time = chunk_times[idx]
            end_time = chunk_times[idx] + WINDOW_SIZE_SECONDS if idx < len(chunk_times) - 1 else start_time + WINDOW_SIZE_SECONDS
            
            if idx == 0:
                # First chunk: keep everything
                full_chapter_transcript.append(f"[{format_timestamp(start_time)}] {text}")
                current_segment_text = text
                current_segment_start = start_time
            else:
                # Find where the overlap ends in this chunk
                prev_text = chunk_texts[idx - 1]
                skip_words = find_overlap_end(prev_text, text)
                
                # Keep only the non-overlapped portion
                words = text.split()
                if skip_words < len(words):
                    new_text = " ".join(words[skip_words:])
                    if new_text.strip():  # Only add if there's content
                        full_chapter_transcript.append(f"\n[{format_timestamp(start_time)}] {new_text}")
                        
                        # Add completed segment to JSON
                        if current_segment_text.strip():
                            segments.append({
                                "start": current_segment_start,
                                "end": start_time,
                                "text": current_segment_text.strip()
                            })
                        current_segment_text = new_text.strip()
                        current_segment_start = start_time
        
        # Add final segment
        if current_segment_text.strip():
            segments.append({
                "start": current_segment_start,
                "end": current_segment_start + WINDOW_SIZE_SECONDS,
                "text": current_segment_text.strip()
            })
        
        # Build JSON as source of truth
        json_data = build_json_transcript(audio_path, segments)
        
        # Apply punctuation to segments in JSON
        for segment in json_data["segments"]:
            segment["text"] = format_text_with_punctuation(segment["text"])
        
        # Save JSON (source of truth)
        output_file_json = audio_path + ".json"
        save_json_transcript(json_data, output_file_json)
        
        # Derive all output formats from JSON
        formatted_timestamps_punct = json_to_formatted_text(json_data, include_timestamps=True, apply_punctuation=False)
        formatted_markdown = format_markdown(formatted_timestamps_punct)
        formatted_llm = format_llm_optimized(formatted_timestamps_punct)

        # Save derived formats
        output_file_ts = audio_path + "_TRANSCRIPT.txt"
        with open(output_file_ts, "w", encoding="utf-8") as f:
            f.write(formatted_timestamps_punct)
        
        output_file_md = audio_path + "_MARKDOWN.md"
        with open(output_file_md, "w", encoding="utf-8") as f:
            f.write(formatted_markdown)
        
        output_file_llm = audio_path + "_LLM.txt"
        with open(output_file_llm, "w", encoding="utf-8") as f:
            f.write(formatted_llm)
        
        print(f"Done! Saved JSON (source of truth): {output_file_json}")
        print(f"       Derived TRANSCRIPT: {output_file_ts}")
        print(f"       Derived MARKDOWN:   {output_file_md}")
        print(f"       Derived LLM:        {output_file_llm}")

    print("\n✅ ALL CHAPTERS FINISHED!")

if __name__ == "__main__":
    # Create the input folder if it doesn't exist
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"Please put your audio files in the '{INPUT_FOLDER}' folder and run again.")
    else:
        transcribe_all_chapters()
