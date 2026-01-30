# IceScriber

Icelandic audiobook transcription engine and LLM-powered learning assistant built for Apple Silicon.

## Overview

A two-tier system:

1. **IceScriber** - Transcribes Icelandic audio using a fine-tuned [Whisper-Large](https://huggingface.co/language-and-voice-lab/whisper-large-icelandic-62640-steps-967h) model with Apple Silicon optimizations
2. **AudiobookLearner** - Transforms transcripts into an interactive learning database with character extraction, chapter summaries, timeline events, and Q&A via Gemini API

```
Audio Files (.mp3)
    │
    ▼
┌──────────────────┐     ┌──────────────────────┐     ┌───────────────┐
│   IceScriber     │────▶│  AudiobookLearner    │────▶│  Interactive  │
│  (Whisper-Large) │     │  (Gemini LLM)        │     │  Q&A Chat     │
└──────────────────┘     └──────────────────────┘     └───────────────┘
    │                         │
    ▼                         ▼
JSON Transcripts         Learning Database
  + TXT, MD, LLM          Characters, Summaries,
    formats                Timeline, Study Notes
```

## Features

### Transcription Engine
- **SDPA-optimized inference** on Apple Silicon MPS backend (~20% speedup)
- **Anti-hallucination** via `repetition_penalty` and `no_repeat_ngram_size`
- **Sliding window** chunking (30s window, 5s stride) with intelligent overlap deduplication
- **JSON-first output** with derived TXT, Markdown, and LLM-optimized formats
- **Full UTF-8 Icelandic** support (þ, ð, æ, ö, á, í, ú, ó)
- **English fast-track** via Distil-Whisper (6x faster, separate pipeline)

### Learning Assistant
- **Character extraction** - names, ages, occupations, traits, actions per chapter
- **Chapter summaries** - 3-5 sentence LLM-generated summaries
- **Timeline events** - dates, times, locations, participants
- **Study material** - key concepts and generated study questions
- **Interactive Q&A** - ask natural language questions about the book
- **SQLite + FTS5** - full-text search across all extracted data

### Infrastructure
- **GUI file picker** (tkinter) with CLI fallback
- **Separated I/O** - input audio and output transcripts in different directories
- **Multi-language** - Icelandic (Whisper-Large) and English (Distil-Whisper) engines
- **Smart resumption** - skips already-transcribed files

## Quick Start

### 1. Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg
```

### 2. Configure API Key (for AudiobookLearner)

```bash
cp .env.example .env
# Edit .env with your Gemini API key from https://aistudio.google.com/apikey
```

### 3. Transcribe

```bash
# Interactive mode (file picker + language selection)
python scripts/transcribe_interactive.py

# Direct batch transcription (Icelandic)
python scripts/transcription/chapterbatch_v2.py

# English audio (6x faster via Distil-Whisper)
python scripts/transcription/chapterbatch_english.py
```

### 4. Analyze with LLM

```bash
# Process chapters with Gemini for character/summary extraction
python scripts/learner/learner_ingest.py --analyze

# Single chapter test
python scripts/learner/learner_ingest.py --analyze --chapter 1
```

### 5. Query

```bash
# Interactive Q&A (LLM-powered)
python scripts/learner/learner_chat_intelligent.py

# Simple keyword-based Q&A
python scripts/learner/learner_chat_simple.py

# CLI queries
python scripts/learner/learner_query.py --characters <book-id>
python scripts/learner/learner_query.py --chapter-detail <chapter-id>
```

## Project Structure

```
IceScriber/
├── scripts/
│   ├── transcription/
│   │   ├── chapterbatch_v2.py       # Icelandic engine (SDPA + anti-hallucination)
│   │   ├── chapterbatch_english.py  # English engine (Distil-Whisper)
│   │   └── chapterbatch.py          # v1 reference implementation
│   ├── learner/
│   │   ├── learner_ingest.py        # LLM analysis pipeline
│   │   ├── learner_query.py         # CLI query interface
│   │   ├── learner_chat_intelligent.py  # Gemini-powered Q&A
│   │   └── learner_chat_simple.py   # Keyword-based Q&A
│   ├── utils/
│   │   ├── compare_v1_v2.py         # Version comparison tool
│   │   └── test_qa.py               # Q&A test suite
│   └── transcribe_interactive.py    # Interactive tool with file picker
├── src/
│   ├── file_picker.py               # GUI/CLI file selection
│   ├── learner_db.py                # Database CRUD operations
│   ├── learner_llm.py               # Gemini API integration
│   └── learner_schema.sql           # SQLite schema (FTS5 + UUID)
├── config/
│   └── chapter_mapping.json         # Chapter-to-file mapping
├── docs/
│   ├── architecture.md              # System design
│   ├── technical_notes.md           # Whisper/MPS optimization notes
│   └── roadmap.md                   # Development roadmap
├── data/
│   ├── input/{icelandic,english}/   # Audio files (git-ignored)
│   ├── output/{icelandic,english}/  # Transcripts (git-ignored)
│   └── databases/                   # SQLite databases (git-ignored)
└── logs/                            # Runtime logs (git-ignored)
```

## Technical Details

### Transcription Pipeline

| Setting | Value | Rationale |
|---------|-------|-----------|
| Model | `whisper-large-icelandic-62640-steps-967h` | Fine-tuned for Icelandic |
| Precision | `float32` | Required on MPS (float16 causes NaN) |
| Attention | `sdpa` | Apple Neural Engine optimization |
| Window | 30s chunks, 5s stride | Prevents memory overflow |
| Anti-hallucination | `repetition_penalty=1.1`, `no_repeat_ngram_size=3` | Prevents loops in silence |

### Performance (Apple Silicon)

| Engine | Speed | Accuracy | Model Size |
|--------|-------|----------|------------|
| **v2 Icelandic** | ~5s/chunk | Baseline +23% | 1.5 GB |
| **English Distil** | ~0.8s/chunk | 99% WER | 800 MB |

### Database Schema

The learning database uses SQLite with FTS5 full-text search:

- `books` - Book metadata
- `chapters` - Chapter info with timestamps
- `chapter_summaries` - LLM-generated summaries (FTS5 indexed)
- `characters` - Names, ages, traits, occupations
- `character_events` - What happened to whom, per chapter
- `timeline_events` - Dates, times, locations
- `relationships` - Character connections
- `study_notes` - Key concepts (FTS5 indexed)

## Dependencies

- Python 3.12+
- PyTorch 2.1+ (with MPS support)
- transformers 4.36+
- librosa, tqdm, python-dotenv
- google-genai (for AudiobookLearner)
- ffmpeg (system dependency)
- tkinter (built-in, for GUI file picker)

## Roadmap

### Phase 1: Transcription - Complete
- Whisper transcription with sliding window and overlap deduplication
- JSON-first output with derived formats
- SQLite indexing with FTS5 search

### Phase 2: Learning Assistant - In Progress
- LLM-powered content extraction (Gemini)
- Character, summary, and timeline databases
- Interactive Q&A (keyword + LLM-powered)
- v2 engine with SDPA and anti-hallucination
- English fast-track via Distil-Whisper

### Phase 3: Advanced Features - Planned
- Vector embeddings for semantic search
- Character deduplication and relationship graphs
- Flashcard generation and practice tests
- Web interface

See [docs/roadmap.md](docs/roadmap.md) for details.

## License

MIT
