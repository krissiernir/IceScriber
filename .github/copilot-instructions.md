# IceScriber - AI Coding Agent Instructions

## Project Overview
IceScriber is a specialized speech-to-text transcription tool for Icelandic audiobooks using a fine-tuned Whisper Large model. It processes audio in 30-second chunks to prevent memory overflow and leverages Mac M-series GPUs via Metal Performance Shaders (MPS).

## Architecture & Data Flow

### Core Components
1. **Audio Chunking:** Audio files (MP3, M4A, WAV) are split into 30-second chunks using librosa at 16kHz sample rate
2. **Model Loading:** Single instance of `whisper-large-icelandic-62640-steps-967h` loaded once for all files (memory optimization)
3. **Inference Loop:** Each chunk processed through Transformer-based Whisper model with language="icelandic" parameter
4. **Text Aggregation:** Chunks decoded and joined into complete transcript saved as `.txt` or `.txt_TEXTI.txt`

### Key Entry Points
- [transcribe.py](transcribe.py) - Single file transcription with GUI file picker (Tkinter)
- [chapterbatch.py](chapterbatch.py) - Batch processing for multi-chapter audiobooks with auto-ordering

### Device Handling
```python
device = "mps" if torch.backends.mps.is_available() else "cpu"
```
Automatically selects Apple Metal (MPS) if available, falls back to CPU. Always use this pattern when adding hardware-dependent code.

## Critical Patterns & Conventions

### Chunk Processing Strategy
- **Size:** 30 seconds of audio at 16kHz sample rate (`chunk_len = 30 * sr`)
- **Rationale:** Prevents OOM crashes on M-series Macs; documents mention "sliding window" improvement (overlapping chunks) as future enhancement
- **Modification Risk:** Changes to chunk size require testing on full audiobooks (can take hours)

### Offline Mode (Important)
```python
os.environ["TRANSFORMERS_OFFLINE"] = "1"
```
Model caching is disabled to prevent internet timeouts. Keep this in all scripts. Do NOT remove or change without explicit requirement.

### Model Specifications
- **Model ID:** `language-and-voice-lab/whisper-large-icelandic-62640-steps-967h`
- **Language Parameter:** Always use `language="icelandic"` in generate() calls
- **Task Parameter:** Always use `task="transcribe"` (not "translate")
- **Data Type:** `torch.float32` for compatibility with Whisper architecture

### File Output Naming
- `transcribe.py`: Saves as `{original_path}_TEXTI.txt` (Icelandic naming)
- `chapterbatch.py`: Saves as `{audio_path}_TRANSCRIPT.txt`
- **Note:** Inconsistent naming convention - preserve current behavior unless refactoring both scripts together

## Developer Workflows

### Setup
```bash
python3.12 -m venv venv_stable
source venv_stable/bin/activate
pip install -r requirements.txt
brew install ffmpeg  # Required for librosa audio loading
```

### Running Transcriptions
- **Single file:** `python transcribe.py` (opens file picker)
- **Batch processing:** `python chapterbatch.py` (scans `audio_chapters/` folder)

### Testing
- Place test audio files in `audio_chapters/` folder
- Small test files recommended (< 5 minutes) due to processing time
- Existing files: [test.py](test.py), [working_test.py](working_test.py)

### Performance Considerations
- **First run:** Model loads ~5GB to VRAM, plan for ~30 seconds
- **Per 30s chunk:** ~2-5 seconds depending on Mac model
- **10-hour book estimate:** 2-3 hours on M-series Mac (see [improvements.md](improvements.md) for faster-whisper optimization)

## Known Limitations & Planned Improvements

See [improvements.md](improvements.md) for priority enhancements:

1. **Sliding Window (High Priority):** Overlapping chunks to prevent word splitting mid-sentence
2. **Post-Processing:** Smart punctuation & paragraph formatting via small LLM
3. **Smart Resumption:** Skip already-transcribed chapters in batch mode
4. **Subtitle Generation:** Export SRT/VTT files for synced video players
5. **CTranslate2 Migration:** Use `faster-whisper` (~4x speedup)

## Dependencies & Version Constraints
- **Python:** 3.12.x required (specified in setup instructions)
- **torch:** 2.10.0 (requires macOS 11+)
- **transformers:** 5.0.0 (tied to model loading)
- **librosa:** 0.11.0 (audio resampling to 16kHz)
- **ffmpeg:** System dependency (via Homebrew)

Do NOT upgrade major versions without testing full transcription workflow - model compatibility varies.

## When Adding Features

- **GPU-related changes:** Test with both MPS and CPU fallback
- **Audio processing:** Validate against 16kHz requirement (hard constraint for model)
- **Text output:** Check encoding UTF-8 explicit (Icelandic characters: þ, ð, æ, ö)
- **Batch processing:** Consider memory implications when loading multiple models
- **File I/O:** Use absolute paths via `os.path.join()` for cross-platform compatibility

## References
- [Model Card](model_card.md) - Model details and training info
- [Improvements Roadmap](improvements.md) - Planned enhancements with technical rationale
- [Debugging Log](debugging_log.md) - Known issues and solutions
