# IceScriber + AudiobookLearner Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        IceScriber                               │
│                  (General Transcription Engine)                 │
│                                                                 │
│  Input: Audio/Video files (.mp3, .m4a, .wav)                  │
│  Output: Timestamped JSON transcripts                          │
│  Database: transcripts.db                                      │
│  Use Cases: Audiobooks, YouTube videos, podcasts, lectures     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    JSON Transcripts
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AudiobookLearner                             │
│                  (Learning Assistant Tool)                      │
│                                                                 │
│  Input: IceScriber JSON transcripts                            │
│  Output: Study notes, knowledge graph, Q&A interface           │
│  Database: learner.db                                          │
│  Use Cases: Exam prep, book analysis, interactive learning     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Phase 1: Transcription (IceScriber)
```
Audio Files
    ↓
[transcribe.py / chapterbatch.py]
    ↓
JSON Transcripts (canonical source)
    ├── segments with timestamps
    ├── metadata (model, language, duration)
    └── text variants (raw, clean, final)
    ↓
[ingest.py]
    ↓
transcripts.db
    ├── books
    ├── audio_files
    └── segments (FTS5 indexed)
```

### Phase 2: Learning Enhancement (AudiobookLearner)
```
IceScriber JSON Transcripts
    ↓
[learner_ingest.py] - NEW TOOL
    ↓
Step 1: Chapter Detection
    ├── Parse metadata from filenames
    ├── Group audio files into chapters
    └── Calculate cumulative timestamps
    ↓
Step 2: LLM Processing (per chapter)
    ├── Generate summary
    ├── Extract characters (name, age, traits)
    ├── Identify key events
    ├── Find dates/timeline
    ├── List important concepts
    └── Create study questions
    ↓
Step 3: Knowledge Graph Building
    ├── Track character development across chapters
    ├── Build relationships between characters
    ├── Maintain cumulative timeline
    └── Cross-reference events
    ↓
Step 4: Vector Embedding Generation
    ├── Embed chapter summaries
    ├── Embed character profiles
    ├── Embed key segments
    └── Store for semantic search
    ↓
learner.db
    ├── books
    ├── chapters
    ├── chapter_summaries (FTS5)
    ├── characters
    ├── character_events
    ├── relationships
    ├── timeline_events
    ├── locations
    ├── concepts
    ├── study_notes (FTS5)
    ├── embeddings (vector search)
    └── qa_history
```

### Phase 3: Q&A Interface (AudiobookLearner)
```
User Question
    ↓
[learner_chat.py] - NEW TOOL
    ↓
Hybrid Retrieval:
    ├── Vector Search: Semantic similarity
    │   └── Find relevant chapters, summaries, characters
    ├── Keyword Search: Exact matches (FTS5)
    │   └── Find specific quotes, names, dates
    └── JSON Lookup: Structured queries
        └── "Who is character X?", "What happened in chapter Y?"
    ↓
Context Assembly:
    ├── Retrieved segments with timestamps
    ├── Character profiles
    ├── Timeline events
    └── Related study notes
    ↓
LLM Response Generation:
    ├── Answer question using context
    ├── Cite sources with timestamps [HH:MM:SS]
    ├── Reference characters and events
    └── Suggest related content
    ↓
User Answer + Citations
    ↓
[Save to qa_history for learning]
```

## File Structure

### IceScriber (Existing)
```
IceScriber/
├── transcribe.py              # Single file transcription
├── chapterbatch.py            # Batch transcription
├── ingest.py                  # JSON → transcripts.db
├── query.py                   # Search transcripts
├── db.py                      # Database utilities
├── schema.sql                 # Transcription database schema
├── transcripts.db             # SQLite database
└── audio_chapters/            # Audio files + JSON outputs
```

### AudiobookLearner (New)
```
IceScriber/
├── learner_schema.sql         # Learning database schema (DONE)
├── learner_ingest.py          # JSON → learner.db (TODO)
├── learner_chat.py            # Q&A interface (TODO)
├── learner_db.py              # Database utilities (TODO)
├── learner_notes.py           # Generate study notes (TODO)
├── learner.db                 # Learning database (auto-created)
└── study_notes/               # Exported markdown notes
    ├── chapter_01.md
    ├── chapter_02.md
    ├── characters.md
    ├── timeline.md
    └── key_concepts.md
```

## Technology Stack

### Transcription (IceScriber)
- **Model**: Whisper-Large Icelandic (fine-tuned)
- **GPU**: Mac MPS (Metal Performance Shaders)
- **Audio**: librosa + ffmpeg
- **Database**: SQLite + FTS5

### Learning (AudiobookLearner)
- **LLM**: Claude/GPT API for analysis
- **Embeddings**: OpenAI text-embedding-3-small or similar
- **Vector Search**:
  - Option A: numpy + cosine similarity (simple, local)
  - Option B: ChromaDB (more features)
  - Option C: FAISS (fastest)
- **Database**: SQLite + FTS5 + vector storage
- **Output**: Markdown study notes

## Implementation Phases

### ✅ Phase 1: Transcription Foundation (COMPLETE)
- [x] Whisper transcription engine
- [x] JSON-first output format
- [x] SQLite database with FTS5
- [x] Query interface
- [x] Batch processing

### 🚧 Phase 2: Learning Assistant (IN DESIGN)
- [ ] Design learner.db schema
- [ ] Build chapter detection logic
- [ ] Integrate LLM for content extraction
- [ ] Generate knowledge graph
- [ ] Create vector embeddings
- [ ] Build Q&A interface

### 📋 Phase 3: Study Tools (PLANNED)
- [ ] Export study notes (markdown)
- [ ] Flashcard generation
- [ ] Practice test questions
- [ ] Progress tracking
- [ ] Spaced repetition system

### 🔮 Phase 4: Advanced Features (FUTURE)
- [ ] Auto-detect chapters (LLM-based)
- [ ] Multi-language support
- [ ] Video transcription with timestamps
- [ ] Web interface
- [ ] Mobile app

## Design Decisions

### Why Two Separate Databases?
1. **Separation of Concerns**: IceScriber = transcription, AudiobookLearner = learning
2. **Reusability**: Use IceScriber for videos, podcasts, etc.
3. **Performance**: Smaller, focused databases
4. **Migration**: Easier to upgrade/change learning features

### Why Hybrid Search (Vector + Keyword + JSON)?
1. **Vector**: "Find chapters about relationships" (semantic)
2. **Keyword**: "Find where 'Reykjavik' is mentioned" (exact)
3. **JSON**: "List all characters" (structured queries)

### Why SQLite (not Postgres)?
- **Now**: Zero setup, portable, fast for single user
- **Later**: Clean migration path to Postgres for web deployment

## Example Workflows

### Workflow 1: Study for Exam
```bash
# 1. Transcribe audiobook
python chapterbatch.py

# 2. Process into study material
python learner_ingest.py --book-id <id> --course "Icelandic Literature"

# 3. Generate study notes
python learner_notes.py --book-id <id> --export study_notes/

# 4. Study with Q&A
python learner_chat.py --book-id <id>
> "Who is the main character and what happens to them?"
> "What are the key dates in the story?"
> "Explain the relationship between X and Y"
```

### Workflow 2: Transcribe YouTube Video
```bash
# 1. Download audio
yt-dlp -x --audio-format mp3 <video-url> -o "audio_chapters/lecture.mp3"

# 2. Transcribe
python transcribe.py

# 3. Search specific topics
python query.py "jökulhlaup"
```

## Next Steps

1. ✅ Create learner_schema.sql
2. ⏭️ Build learner_ingest.py (chapter detection + LLM processing)
3. ⏭️ Set up vector embedding pipeline
4. ⏭️ Build learner_chat.py (Q&A interface)
5. ⏭️ Test with one chapter first
6. ⏭️ Process full audiobook
7. ⏭️ Refine and iterate

## Questions to Resolve

1. **LLM Provider**: Claude API, OpenAI GPT-4, or local Llama?
2. **Vector DB**: numpy (simple), ChromaDB (features), or FAISS (speed)?
3. **Cost**: API costs for processing ~29 chapters?
4. **Markdown Format**: What structure for study notes?
5. **Chapter Mapping**: Manual config file or auto-parse filenames?
