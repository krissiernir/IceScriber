import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import librosa
import os
import time
from tqdm import tqdm
import tkinter as tk
from tkinter import filedialog

# Stop the internet timeout errors
os.environ["TRANSFORMERS_OFFLINE"] = "1"

MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"

# Sliding Window Settings
WINDOW_SIZE_SECONDS = 30  # Size of each chunk
STRIDE_SECONDS = 5        # How much to shift for next window (smaller = more overlap)
OVERLAP_SECONDS = WINDOW_SIZE_SECONDS - STRIDE_SECONDS  # 25 seconds of context

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askopenfilename(title="Veldu hljóðbók (Select Audiobook)")

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

def transcribe_audiobook():
    audio_path = select_file()
    if not audio_path:
        print("Engin skrá valin.")
        return

    print(f"\n--- BYRJA (STARTING) ---")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Tæki (Device): {device}")

    # 1. Load AI
    print("Hleð líkaninu (Loading AI)...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID, 
        torch_dtype=torch.float32, 
        low_cpu_mem_usage=True
    ).to(device)

    # 2. Load Audio
    print(f"Hleð hljóðskrá (Loading Audio): {os.path.basename(audio_path)}...")
    # This part might take a minute for a very long book
    speech, sr = librosa.load(audio_path, sr=16000)
    
    # 3. Create sliding window chunks with timestamps
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
    
    print(f"Fjöldi búta (Total Chunks): {len(chunks)} (Sliding window with {OVERLAP_SECONDS}s overlap)")
    print("Umritun hafin (Transcription started)...")
    
    chunk_texts = []
    start_time = time.time()

    # 4. Transcription Loop
    for chunk in tqdm(chunks, desc="Framvinda (Progress)", unit="bútur"):
        inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
        input_features = inputs.input_features.to(device)

        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                language="icelandic",
                task="transcribe"
            )

        chunk_text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        chunk_texts.append(chunk_text)

    # 5. Intelligent Deduplication: Remove overlapping text and add timestamps
    full_transcript = []
    
    for idx, text in enumerate(chunk_texts):
        timestamp = format_timestamp(chunk_times[idx])
        
        if idx == 0:
            # First chunk: keep everything
            full_transcript.append(f"[{timestamp}] {text}")
        else:
            # Find where the overlap ends in this chunk
            prev_text = chunk_texts[idx - 1]
            skip_words = find_overlap_end(prev_text, text)
            
            # Keep only the non-overlapped portion
            words = text.split()
            if skip_words < len(words):
                new_text = " ".join(words[skip_words:])
                if new_text.strip():  # Only add if there's content
                    full_transcript.append(f"\n[{timestamp}] {new_text}")

    # 6. Save Results in three formats
    raw_transcript = "".join(full_transcript)
    formatted_timestamps = format_timestamps(raw_transcript)
    formatted_timestamps_punct = format_text_with_punctuation(formatted_timestamps)
    formatted_markdown = format_markdown(formatted_timestamps)
    formatted_llm = format_llm_optimized(formatted_timestamps)
    
    base_path = os.path.splitext(audio_path)[0]
    
    # Save timestamps version
    output_file_ts = base_path + "_TEXTI.txt"
    with open(output_file_ts, "w", encoding="utf-8") as f:
        f.write(formatted_timestamps_punct)
    
    # Save markdown version
    output_file_md = base_path + "_MARKDOWN.md"
    with open(output_file_md, "w", encoding="utf-8") as f:
        f.write(formatted_markdown)
    
    # Save LLM-optimized version
    output_file_llm = base_path + "_LLM.txt"
    with open(output_file_llm, "w", encoding="utf-8") as f:
        f.write(formatted_llm)

    total_time = (time.time() - start_time) / 60
    print(f"\n✅ VERKI LOKIÐ!")
    print(f"Heildartími: {total_time:.2f} mínútur")
    print(f"Skrá vistuð: {output_file_ts}")
    print(f"Skrá vistuð: {output_file_md}")
    print(f"Skrá vistuð: {output_file_llm}")

if __name__ == "__main__":
    transcribe_audiobook()
