import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import librosa
import os
import time
from tqdm import tqdm

# Force Offline
os.environ["TRANSFORMERS_OFFLINE"] = "1"

AUDIO_FILE = "001_Daudi_trudsins.mp3"
MODEL_ID = "language-and-voice-lab/whisper-large-icelandic-62640-steps-967h"

def transcribe_direct():
    print(f"--- Icelandic Direct Transcriber ---")
    
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    # Using float32 for maximum stability on Mac
    torch_dtype = torch.float32 

    # 1. Load Processor and Model directly
    print("Loading Processor and Model...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID, 
        torch_dtype=torch_dtype, 
        low_cpu_mem_usage=True
    ).to(device)

    # 2. Load the Audio
    print(f"Loading Audio: {AUDIO_FILE}...")
    speech, sr = librosa.load(AUDIO_FILE, sr=16000)
    
    # 3. Setup Chunking
    chunk_len = 30 * sr  # 30 second chunks
    chunks = [speech[i:i + chunk_len] for i in range(0, len(speech), chunk_len)]
    
    print(f"Total Chunks: {len(chunks)}")
    print("--- Starting Transcription ---")
    
    full_transcript = []
    start_time = time.time()

    # 4. Manual Loop with Progress Bar
    for i, chunk in enumerate(tqdm(chunks)):
        # Convert audio to the format the AI needs
        inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
        input_features = inputs.input_features.to(device).to(torch_dtype)

        # Tell the AI to generate Icelandic text
        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                language="icelandic",
                task="transcribe"
            )

        # Turn the IDs into actual Icelandic words
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        full_transcript.append(transcription)

    # 5. Save Results
    final_text = " ".join(full_transcript)
    duration = (time.time() - start_time) / 60
    
    output_file = "direct_transcription.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"\n✅ SUCCESS!")
    print(f"Total time: {duration:.2f} minutes")
    print(f"First 200 chars: {final_text[:200]}...")

if __name__ == "__main__":
    transcribe_direct()