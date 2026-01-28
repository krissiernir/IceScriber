# Icelandic Audiobook Transcriber

A specialized Python tool for transcribing long-form Icelandic audiobooks using the fine-tuned Whisper-Large-Icelandic model. Optimized for Mac (M-series) performance.

## 🛠 Features
- **Manual Chunking:** Processes audio in 30s segments to prevent memory crashes.
- **Mac GPU Acceleration:** Uses Apple's Metal Performance Shaders (MPS).
- **Smart Resumption:** Skips files that have already been transcribed.
- **Timestamps:** Outputs text with [MM:SS] markers for easy navigation.
- **Batch Processing:** Scans a folder and transcribes all chapters automatically.

## 🚀 Setup
1. **Python Version:** 3.12.x (Recommended)
2. **Environment:**
   ```bash
   python3.12 -m venv venv_stable
   source venv_stable/bin/activate
   pip install -r requirements.txt

  ## External Dependencies

- **ffmpeg** (install via Homebrew):
  ```bash
  brew install ffmpeg
  

## 📖 How to use

1. Place your audio chapters in the `audio_chapters/` folder.
2. Run the script:

```bash
python transcribe.py# IceScriber
