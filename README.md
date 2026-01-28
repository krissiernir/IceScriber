# IceScriber - Icelandic Audiobook Transcriber

A specialized tool for transcribing long-form Icelandic audiobooks using a fine-tuned Whisper-Large model. Features audio-to-text transcription with optional database indexing for full-text search.

## 🛠 Features

### Transcription Core
- **Audio Chunking:** 30-second segments prevent memory overflow on Mac M-series
- **Mac GPU Acceleration:** Metal Performance Shaders (MPS) for fast inference
- **Smart Resumption:** Skip already-transcribed files
- **UTF-8 Icelandic:** Full support for Icelandic characters (þ, ð, æ, ö)
- **Three Output Formats:**
  - `_TRANSCRIPT.txt` - Plain text with timestamps
  - `_LLM.txt` - Optimized for LLM input
  - `_MARKDOWN.md` - Formatted markdown

### Database & Search
- **SQLite Backend:** Portable database for transcript indexing
- **Full-Text Search:** Search across all segments with timestamps
- **Citation Format:** Results with exact timestamps [HH:MM:SS–HH:MM:SS]
- **Clean Schema:** UUID-based design for future Postgres migration

## 🚀 Quick Start

### 1. Setup Environment

```bash
python3.12 -m venv venv_stable
source venv_stable/bin/activate
pip install -r requirements.txt
brew install ffmpeg  # Required for librosa
```

### 2. Transcribe Audiobook

Place audio files in `audio_chapters/`:

```bash
# Single file (GUI file picker)
python transcribe.py

# Batch process all files
python chapterbatch.py
```

**Output:** JSON transcripts with metadata + segments (one JSON per audio file)

### 3. Index into SQLite Database

```bash
# Initialize and ingest all JSON files
python ingest.py --all --book-title "Book Title" --author "Author Name"
```

### 4. Search Transcripts

```bash
# Keyword search
python query.py "keyword"

# Search in specific book
python query.py "keyword" --book-id <book-id>

# List books
python query.py --list-books

# List audio files in book
python query.py --list-audio-files <book-id>

# Show book statistics
python query.py --info <book-id>
```

## 📊 Data Model

### Core Unit: AudioFile
- One audio file = one JSON transcript (canonical source)
- Naming flexible: track_001.mp3, chapter_1.m4a, disk2_side1.wav, etc.
- File number auto-extracted for ordering

### Segments
- Time windows within audio file (typically 5–30 seconds)
- Timestamped: start_s, end_s
- Three text variants: raw, clean, final (with punctuation)
- Searchable by keyword

### Books
- Collection of audio files
- Metadata stored as JSON in database
- Query returns book statistics

## 📁 Project Structure

```
├── transcribe.py              # Single-file transcription GUI
├── chapterbatch.py            # Batch process all audio files
├── ingest.py                  # Import JSON transcripts to SQLite
├── query.py                   # Search database CLI
├── db.py                      # Database utilities
├── schema.sql                 # SQLite schema definition
├── audio_chapters/            # Place audio files here
│   ├── 001_Chapter.mp3
│   ├── 001_Chapter.mp3.json   # Canonical transcript
│   ├── 002_Chapter.mp3
│   ├── 002_Chapter.mp3.json
│   └── ...
├── transcripts.db             # SQLite database (auto-created)
└── requirements.txt           # Python dependencies
```

## 🗄 SQLite Database

### Initialize & Ingest
```bash
python ingest.py --all --book-title "Title" --author "Author"
```

### Rebuild From Scratch
```bash
python ingest.py --rescan --book-title "Title"
```

### Add Single Audio File to Existing Book
```bash
python ingest.py path/to/file.json --book-id <existing-book-id>
```

## 🔍 Search Examples

### Simple keyword search
```bash
python query.py "dýrðlegi"
```

Output:
```
🔍 Found 3 result(s) for: 'dýrðlegi'
────────────────────────────────────────────────────
1. 001_Intro.mp3 [00:02:15–00:02:20]: ...dýrðlegi konungi...
2. 005_Chapter4.mp3 [00:15:30–00:15:35]: ...dýrðlegir menn...
────────────────────────────────────────────────────
```

### Search specific book
```bash
python query.py "keyword" --book-id 5ef8b42f-0baf-4b68-b573-214b370b9761
```

### List all books
```bash
python query.py --list-books
```

### Show book statistics
```bash
python query.py --info <book-id>
```

## ⚙️ Configuration

### Model (in transcribe.py/chapterbatch.py)
- Model: `language-and-voice-lab/whisper-large-icelandic-62640-steps-967h`
- Language: Icelandic
- Task: Transcribe (not translate)
- Sample rate: 16kHz
- Chunk duration: 30 seconds

### Database (in db.py)
- Engine: SQLite (single file)
- Search: Case-insensitive substring matching
- Default limit: 50 results per search

## 📈 Performance

### Transcription (Mac M1/M2/M3)
- First run: ~5GB loaded to VRAM (~30 seconds)
- Per 30s chunk: 2–5 seconds
- 10-hour book: ~2–3 hours total

### Database
- Size: ~100KB per 54 segments (~1.8KB average)
- Search: <100ms for keyword across 10k+ segments

## 🚀 Planned Enhancements

See [improvements.md](improvements.md):
- **Sliding Window:** Overlapping chunks to prevent word splitting
- **Postgres Migration:** Scale search to distributed deployment
- **Semantic Search:** Vector similarity with pgvector
- **Confidence Metrics:** Low-confidence segment flagging
- **Post-processing:** Smart punctuation + paragraph formatting

## 🧪 Testing

### Run Overnight Integration Test
```bash
bash test_overnight.sh
```

This:
1. Removes old database
2. Ingests all JSON files
3. Tests keyword searches
4. Displays final statistics

### Manual Testing
```bash
# Ingest
python ingest.py --all --book-title "Test" --author "Test Author"

# List books
python query.py --list-books

# Search
python query.py "test keyword"
```

## 📦 Dependencies

- **Python:** 3.12.x
- **torch:** 2.10.0 (with MPS support)
- **transformers:** 5.0.0
- **librosa:** 0.11.0
- **SQLite:** Built-in
- **ffmpeg:** System dependency (install via Homebrew)

## 📝 Notes

- **Offline Mode:** Model cached locally; internet not required after first setup
- **UTF-8 Support:** All Icelandic characters handled correctly
- **UUID IDs:** Database uses stable UUIDs for clean Postgres migration
- **JSON Source:** Each JSON is the canonical artifact; regenerate outputs as needed

## 🤝 Contributing

See [debugging_log.md](debugging_log.md) for known issues and [improvements.md](improvements.md) for technical roadmap.
