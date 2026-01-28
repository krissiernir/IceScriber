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

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askopenfilename(title="Veldu hljóðbók (Select Audiobook)")

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
    
    # 3. Create 30-second chunks
    chunk_len = 30 * sr
    chunks = [speech[i:i + chunk_len] for i in range(0, len(speech), chunk_len)]
    
    print(f"Fjöldi búta (Total Chunks): {len(chunks)}")
    print("Umritun hafin (Transcription started)...")
    
    full_transcript = []
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
        full_transcript.append(chunk_text)

    # 5. Save Results
    final_text = " ".join(full_transcript)
    output_file = os.path.splitext(audio_path)[0] + "_TEXTI.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_text)

    total_time = (time.time() - start_time) / 60
    print(f"\n✅ VERKI LOKIÐ!")
    print(f"Heildartími: {total_time:.2f} mínútur")
    print(f"Skrá vistuð: {output_file}")

if __name__ == "__main__":
    transcribe_audiobook()