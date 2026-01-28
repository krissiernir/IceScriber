import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import librosa
import os
import time
from tqdm import tqdm

# Force Offline
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# --- SETTINGS ---
INPUT_FOLDER = "audio_chapters" # Put your mp3 files in this folder
MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"

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
        print(f"\n--- Processing: {filename} ---")
        
        # Load audio
        speech, sr = librosa.load(audio_path, sr=16000)
        chunk_len = 30 * sr
        chunks = [speech[i:i + chunk_len] for i in range(0, len(speech), chunk_len)]
        
        full_chapter_transcript = []
        
        # Transcribe chunks
        for chunk in tqdm(chunks, desc=f"Transcribing {filename}"):
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            input_features = inputs.input_features.to(device)

            with torch.no_grad():
                predicted_ids = model.generate(input_features, language="icelandic", task="transcribe")

            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            full_chapter_transcript.append(text)

        # Save this specific chapter
        output_file = audio_path + "_TRANSCRIPT.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(" ".join(full_chapter_transcript))
        
        print(f"Done! Saved to {output_file}")

    print("\n✅ ALL CHAPTERS FINISHED!")

if __name__ == "__main__":
    # Create the input folder if it doesn't exist
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"Please put your audio files in the '{INPUT_FOLDER}' folder and run again.")
    else:
        transcribe_all_chapters()