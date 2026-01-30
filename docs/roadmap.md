# IceScriber + AudiobookLearner Roadmap

## Current Status (Jan 28, 2026 - Updated)

### ✅ Completed (IceScriber v1.0)
- [x] Whisper-Large Icelandic transcription engine
- [x] Mac GPU (MPS) acceleration
- [x] 30-second chunking with 5-second stride (sliding window)
- [x] JSON-first output format (canonical source)
- [x] SQLite database with FTS5 full-text search
- [x] Batch processing (chapterbatch.py)
- [x] Smart resumption (skip already-transcribed files)
- [x] Query interface (search with timestamps)
- [x] Three output formats: JSON, TXT, MD, LLM
- [x] Smart punctuation and formatting
- [x] 25/29 audiobook files transcribed (86% complete)

### ✅ Completed (AudiobookLearner Foundation)
- [x] Database schema design (learner_schema.sql)
- [x] Database utilities (learner_db.py)
- [x] LLM integration with Gemini API (learner_llm.py)
- [x] Ingestion pipeline (learner_ingest.py)
- [x] Query interface (learner_query.py)
- [x] Chapter mapping configuration
- [x] Full documentation (ARCHITECTURE.md, LEARNER_STATUS.md)
- [x] Tested on 3 chapters (1, 5, 6) - quality verified ✅

---

## Phase 1: Complete Current Transcription
**Goal**: Finish transcribing "Dauði Trúðsins" audiobook

### Tasks
- [ ] Transcribe remaining 4 audio files (026-029)
- [ ] Verify JSON outputs are clean
- [ ] Ingest all 29 files into transcripts.db
- [ ] Test search functionality on complete dataset

**Timeline**: 3 hours (transcription) + 1 hour (testing)

---

## Phase 2: AudiobookLearner Foundation (🚧 80% Complete)
**Goal**: Build learning assistant tool that processes IceScriber transcripts

### 2.1 Schema & Database Setup ✅
- [x] Design learner.db schema (learner_schema.sql)
- [x] Document architecture (ARCHITECTURE.md)
- [x] Create learner_db.py (database utilities - 350 lines)
- [x] Test database creation and migrations

### 2.2 Chapter Detection & Ingestion ✅
- [x] Build learner_ingest.py (260 lines)
  - [x] Parse filename metadata (chapter numbers, titles)
  - [x] Group audio files into logical chapters
  - [x] Calculate cumulative timestamps
  - [x] Store chapter structure in learner.db
- [x] Create chapter mapping config (chapter_mapping.json)
  - 25 chapters mapped from audio files
  - Chapter titles (days of the week)
  - File associations

### 2.3 LLM Content Extraction ✅
- [x] Set up LLM API (Gemini - cost effective, good quality)
- [x] Build prompts for content extraction:
  - [x] Chapter summary (3-5 sentences)
  - [x] Character extraction (name, age, traits, actions)
  - [x] Key events and plot points
  - [x] Timeline/dates
  - [x] Important concepts
  - [x] Study questions
- [x] Process three chapters as proof-of-concept (Ch 1, 5, 6)
- [x] Iterate on prompt quality (Icelandic names handled correctly)
- [ ] Batch process all chapters (ready, pending user confirmation)

**Test Results:**
- Chapter 1: 6 characters, summary quality excellent
- Chapter 5: 15 characters, 6 events
- Chapter 6: 9 characters, 5 events

### 2.4 Knowledge Graph Building ⏭️ Next
- [ ] Extract characters from all chapters
- [ ] Deduplicate characters across chapters
- [ ] Track character development over time
- [ ] Build character relationships
- [ ] Create cumulative timeline
- [ ] Cross-reference events between chapters
- [ ] Generate character profiles

### 2.5 Vector Embeddings ⏭️ Future
- [ ] Choose vector DB (numpy/ChromaDB/FAISS)
- [ ] Generate embeddings for:
  - [ ] Chapter summaries
  - [ ] Character profiles
  - [ ] Key segments
  - [ ] Study notes
- [ ] Store embeddings in learner.db
- [ ] Build similarity search function

**Timeline**: Foundation complete, 2-3 days for full analysis + Q&A

---

## Phase 3: Q&A Interface
**Goal**: Interactive chat with audiobook content

### 3.1 Query Engine
- [ ] Build learner_chat.py
- [ ] Implement hybrid retrieval:
  - [ ] Vector search (semantic similarity)
  - [ ] FTS5 keyword search (exact matches)
  - [ ] JSON structured queries
- [ ] Context assembly from multiple sources
- [ ] Test retrieval quality

### 3.2 LLM Response Generation
- [ ] Build prompt for answer generation
- [ ] Include context with citations
- [ ] Format timestamps [HH:MM:SS]
- [ ] Reference characters and events
- [ ] Suggest related content
- [ ] Save Q&A history

### 3.3 CLI Interface
- [ ] Interactive mode (chat loop)
- [ ] Single question mode
- [ ] List mode (show characters, timeline, etc.)
- [ ] Export mode (save conversation)

**Timeline**: 1-2 weeks

---

## Phase 4: Study Notes Generation
**Goal**: Export formatted study material

### 4.1 Markdown Export
- [ ] Build learner_notes.py
- [ ] Chapter summaries (one MD per chapter)
- [ ] Master character list with profiles
- [ ] Timeline of events
- [ ] Key concepts and themes
- [ ] Study questions
- [ ] Full book summary

### 4.2 Study Tools
- [ ] Flashcard generation (Anki format)
- [ ] Practice test questions
- [ ] Key quotes with timestamps
- [ ] Character relationship diagram (Mermaid/Graphviz)

**Timeline**: 1 week

---

## Phase 5: IceScriber Enhancements
**Goal**: Improve transcription quality and speed

### 5.1 Quality Improvements
- [ ] **Auto-detect chapters** (LLM-based)
  - Analyze content for chapter boundaries
  - Detect chapter titles from audio
  - Generate table of contents
- [ ] **Confidence scoring**
  - Flag low-confidence transcriptions
  - Highlight words that need review
  - Generate proofreading checklist

### 5.2 Performance Improvements
- [ ] **faster-whisper integration**
  - Convert Icelandic model to CTranslate2 format
  - 4x speed increase (10-hour book in 30 minutes)
  - Reduced RAM usage
- [ ] **Parallel processing**
  - Process multiple files simultaneously
  - Utilize all CPU/GPU cores

### 5.3 Output Formats
- [ ] **Subtitle generation**
  - .srt format (SubRip)
  - .vtt format (WebVTT)
  - Sync with audio in VLC
- [ ] **Timestamp precision**
  - Word-level timestamps
  - Sentence-level timestamps
  - Better overlap handling

**Timeline**: 2-3 weeks

---

## Phase 6: Video Transcription
**Goal**: Extend IceScriber to handle video files

### 6.1 Video Support
- [ ] Extract audio from video files (.mp4, .mkv, .avi)
- [ ] Preserve video metadata
- [ ] Generate video-synced subtitles
- [ ] Scene detection and chapter markers

### 6.2 YouTube Integration
- [ ] Download YouTube audio (yt-dlp)
- [ ] Extract video metadata (title, description)
- [ ] Generate timestamped transcripts
- [ ] Create clickable chapter markers

**Timeline**: 1-2 weeks

---

## Phase 7: Web Interface (Long-term)
**Goal**: Deploy as web application

### 7.1 Backend API
- [ ] Migrate to Postgres (multi-user support)
- [ ] REST API (FastAPI or Flask)
- [ ] User authentication
- [ ] File upload and processing queue
- [ ] WebSocket for real-time chat

### 7.2 Frontend
- [ ] React/Vue web interface
- [ ] Audio player with synchronized transcript
- [ ] Interactive Q&A chat
- [ ] Study notes viewer
- [ ] Knowledge graph visualization

### 7.3 Deployment
- [ ] Docker containers
- [ ] Cloud hosting (AWS/GCP/Azure)
- [ ] CDN for audio files
- [ ] Background job processing (Celery)

**Timeline**: 2-3 months

---

## Immediate Next Steps (This Week)

1. **Finish transcription** (3 hours)
   - Run: `python chapterbatch.py`
   - Transcribe files 026-029
   - Verify outputs

2. **Set up learner database** (2 hours)
   - Create learner_db.py
   - Initialize learner.db
   - Test schema

3. **Build chapter detection** (4 hours)
   - Create learner_ingest.py
   - Parse filename metadata
   - Group files into chapters

4. **LLM integration proof-of-concept** (4 hours)
   - Set up Claude/OpenAI API
   - Process one chapter
   - Extract characters and summary
   - Verify output quality

5. **Test Q&A basics** (4 hours)
   - Simple keyword search
   - Basic vector similarity
   - Format answers with citations

**Total**: ~17 hours of focused work

---

## Key Design Decisions

### Two-Tier Architecture
- **IceScriber**: General-purpose Icelandic transcription (reusable)
- **AudiobookLearner**: Specialized learning tool (consumes IceScriber output)

### Hybrid Search Strategy
- **Vector embeddings**: Semantic search ("chapters about love")
- **FTS5 keywords**: Exact matches ("Reykjavík")
- **JSON queries**: Structured data ("list all characters")

### Database Strategy
- **Now**: SQLite (simple, portable, fast)
- **Later**: Postgres (multi-user, web deployment)

### LLM Strategy
- **Content extraction**: Claude/GPT-4 (accuracy matters)
- **Embeddings**: OpenAI text-embedding-3-small (cost-effective)
- **Future**: Local Llama models (privacy, cost)

---

## Questions to Answer

1. **LLM Provider**:
   - Claude API (better at Icelandic)?
   - OpenAI GPT-4 (cheaper)?
   - Local Llama (free, slower)?

2. **Vector Database**:
   - numpy (simplest, good enough)?
   - ChromaDB (more features, easy)?
   - FAISS (fastest, more complex)?

3. **Chapter Detection**:
   - Manual mapping file for now?
   - Auto-detect as Phase 5 feature?

4. **Cost Estimation**:
   - ~29 chapters × ~10 minutes each = ~4 hours of audio
   - GPT-4 API cost for processing?
   - Embedding cost for ~1000 segments?

---

## Success Metrics

### IceScriber
- ✅ Transcribe 10-hour audiobook in 2-3 hours
- ✅ 95%+ accuracy on Icelandic text
- ✅ Search results in <100ms

### AudiobookLearner
- [ ] Extract 95%+ of character mentions
- [ ] Generate useful chapter summaries
- [ ] Answer 90%+ of factual questions correctly
- [ ] Provide citations with timestamps
- [ ] Process full book in <1 hour (after transcription)

---

## Resources Needed

- API keys (Claude or OpenAI)
- Embedding model access
- Test audiobook (current: "Dauði Trúðsins")
- ~50GB disk space for models and databases
- Mac M-series for GPU acceleration
