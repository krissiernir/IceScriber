import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import librosa
import os
import time
from tqdm import tqdm

# --- SETTINGS ---
INPUT_FOLDER = "audio_chapters" 
MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"

def transcribe_with_resumption():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using Device: {device}")

    print("Loading AI model...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID, torch_dtype=torch.float32, low_cpu_mem_usage=True
    ).to(device)

    # Find and sort files
    audio_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp3', '.m4a', '.wav'))]
    audio_files.sort()
    
    print(f"Found {len(audio_files)} files in '{INPUT_FOLDER}'.")

    for filename in audio_files:
        audio_path = os.path.join(INPUT_FOLDER, filename)
        output_file = audio_path + "_TRANSCRIPT.txt"

        # --- THE SMART RESUMPTION FIX ---
        if os.path.exists(output_file):
            print(f"⏩ Skipping {filename} (Transcript already exists).")
            continue 
        # --------------------------------

        print(f"\n--- Processing: {filename} ---")
        speech, sr = librosa.load(audio_path, sr=16000)
        chunk_len = 30 * sr
        chunks = [speech[i:i + chunk_len] for i in range(0, len(speech), chunk_len)]
        
        full_chapter_transcript = []
        
        for chunk in tqdm(chunks, desc=f"Transcribing {filename}"):
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            input_features = inputs.input_features.to(device)

            with torch.no_grad():
                predicted_ids = model.generate(input_features, language="icelandic", task="transcribe")

            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            full_chapter_transcript.append(text)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(" ".join(full_chapter_transcript))
        
        print(f"✅ Saved: {filename}")

    print("\n🎉 ALL PENDING CHAPTERS FINISHED!")

if __name__ == "__main__":
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"Please put files in '{INPUT_FOLDER}'")
    else:
        transcribe_with_resumption()