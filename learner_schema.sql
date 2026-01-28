-- AudiobookLearner Schema v1
-- Separate database from IceScriber for learning-specific features
-- Consumes IceScriber JSON transcripts as input

-- Books table (learning context)
CREATE TABLE books (
  book_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  genre TEXT,
  language TEXT DEFAULT 'icelandic',
  transcript_source TEXT,  -- path to IceScriber transcripts.db or folder
  metadata TEXT,  -- JSON: exam date, course name, etc.
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chapters (logical grouping of audio files)
CREATE TABLE chapters (
  chapter_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  chapter_number INTEGER,
  title TEXT,
  audio_file_paths TEXT,  -- JSON array: ["001.mp3", "002.mp3"]
  start_timestamp_s REAL,  -- Start time in book (cumulative)
  end_timestamp_s REAL,    -- End time in book (cumulative)
  duration_s REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

-- Chapter Summaries (what happened)
CREATE TABLE chapter_summaries (
  summary_id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL,
  summary_text TEXT NOT NULL,  -- LLM-generated summary
  key_events TEXT,  -- JSON array: ["Event 1", "Event 2"]
  key_concepts TEXT,  -- JSON array: ["Concept 1", "Concept 2"]
  plot_points TEXT,  -- JSON array: plot developments
  study_questions TEXT,  -- JSON array: potential test questions
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(chapter_id) REFERENCES chapters(chapter_id)
);

-- Characters (knowledge graph nodes)
CREATE TABLE characters (
  character_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  name TEXT NOT NULL,
  aliases TEXT,  -- JSON array: ["Jon", "Jói", "Inspector"]
  age INTEGER,
  occupation TEXT,
  traits TEXT,  -- JSON array: ["intelligent", "determined"]
  first_appearance_chapter INTEGER,
  description TEXT,  -- LLM-generated character profile
  metadata TEXT,  -- JSON: extensible character data
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

-- Character Events (what happened to whom)
CREATE TABLE character_events (
  event_id TEXT PRIMARY KEY,
  character_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL,
  event_type TEXT,  -- "introduced", "action", "dialogue", "development"
  event_description TEXT,
  timestamp_s REAL,  -- Exact time in audiobook
  importance INTEGER DEFAULT 5,  -- 1-10 scale
  FOREIGN KEY(character_id) REFERENCES characters(character_id),
  FOREIGN KEY(chapter_id) REFERENCES chapters(chapter_id)
);

-- Relationships (character connections)
CREATE TABLE relationships (
  relationship_id TEXT PRIMARY KEY,
  character_id_1 TEXT NOT NULL,
  character_id_2 TEXT NOT NULL,
  relationship_type TEXT,  -- "friend", "enemy", "family", "colleague"
  description TEXT,
  first_chapter_id TEXT,
  FOREIGN KEY(character_id_1) REFERENCES characters(character_id),
  FOREIGN KEY(character_id_2) REFERENCES characters(character_id),
  FOREIGN KEY(first_chapter_id) REFERENCES chapters(chapter_id)
);

-- Timeline (dates and events)
CREATE TABLE timeline_events (
  timeline_event_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  chapter_id TEXT,
  event_date TEXT,  -- "1995-03-15" or "March 15, 1995" (flexible)
  event_time TEXT,  -- "14:30" if specified
  event_description TEXT NOT NULL,
  participants TEXT,  -- JSON array: [character_id1, character_id2]
  location TEXT,
  timestamp_s REAL,  -- Where in audiobook this is mentioned
  importance INTEGER DEFAULT 5,
  FOREIGN KEY(book_id) REFERENCES books(book_id),
  FOREIGN KEY(chapter_id) REFERENCES chapters(chapter_id)
);

-- Locations
CREATE TABLE locations (
  location_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  first_mention_chapter INTEGER,
  significance TEXT,  -- Why this location matters
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

-- Key Concepts (themes, ideas, test-worthy content)
CREATE TABLE concepts (
  concept_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  concept_name TEXT NOT NULL,
  definition TEXT,
  explanation TEXT,
  related_chapters TEXT,  -- JSON array: [chapter_id1, chapter_id2]
  importance INTEGER DEFAULT 5,
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

-- Study Notes (markdown formatted per chapter)
CREATE TABLE study_notes (
  note_id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL,
  note_type TEXT,  -- "summary", "analysis", "key_points", "test_prep"
  content_markdown TEXT NOT NULL,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(chapter_id) REFERENCES chapters(chapter_id)
);

-- Vector Embeddings (for semantic search)
CREATE TABLE embeddings (
  embedding_id TEXT PRIMARY KEY,
  content_type TEXT NOT NULL,  -- "chapter", "segment", "summary", "character"
  content_id TEXT NOT NULL,  -- chapter_id, character_id, etc.
  text_content TEXT NOT NULL,  -- Original text that was embedded
  embedding_vector BLOB NOT NULL,  -- Serialized numpy array or bytes
  model_name TEXT,  -- "text-embedding-3-small" or similar
  timestamp_s REAL,  -- If from a specific audiobook moment
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Q&A History (track conversations)
CREATE TABLE qa_history (
  qa_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  context_used TEXT,  -- JSON: which chapters/characters were referenced
  retrieval_method TEXT,  -- "vector", "keyword", "hybrid"
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

-- Indexes for performance
CREATE INDEX idx_chapters_book_id ON chapters(book_id);
CREATE INDEX idx_chapter_summaries_chapter_id ON chapter_summaries(chapter_id);
CREATE INDEX idx_characters_book_id ON characters(book_id);
CREATE INDEX idx_character_events_character_id ON character_events(character_id);
CREATE INDEX idx_character_events_chapter_id ON character_events(chapter_id);
CREATE INDEX idx_timeline_book_id ON timeline_events(book_id);
CREATE INDEX idx_timeline_chapter_id ON timeline_events(chapter_id);
CREATE INDEX idx_embeddings_content ON embeddings(content_type, content_id);

-- FTS5 for keyword search (complement to vector embeddings)
CREATE VIRTUAL TABLE study_notes_fts USING fts5(
  content_markdown,
  note_id UNINDEXED,
  chapter_id UNINDEXED
);

CREATE VIRTUAL TABLE chapter_summaries_fts USING fts5(
  summary_text,
  summary_id UNINDEXED,
  chapter_id UNINDEXED
);
