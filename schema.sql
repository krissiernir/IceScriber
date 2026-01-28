-- IceScriber SQLite Schema v1
-- Stable IDs (UUIDs/hashes) enable clean migration to Postgres later

CREATE TABLE books (
  book_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  metadata TEXT,  -- JSON string for extensibility
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audio_files (
  audio_file_id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL,
  file_number INTEGER,  -- position in book (e.g., track 1, 2, 3...), not required
  file_path TEXT NOT NULL UNIQUE,  -- path to .mp3, .m4a, .wav, etc.
  json_path TEXT NOT NULL UNIQUE,  -- path to canonical JSON (source of truth)
  duration_s REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(book_id) REFERENCES books(book_id)
);

CREATE TABLE segments (
  segment_id TEXT PRIMARY KEY,
  audio_file_id TEXT NOT NULL,  -- segments belong to an audio file
  start_s REAL NOT NULL,
  end_s REAL NOT NULL,
  text_raw TEXT NOT NULL,
  text_clean TEXT,  -- deterministic cleanup (optional)
  text_final TEXT,  -- after LLM punctuation pass (optional)
  flags_json TEXT,  -- JSON: {"low_confidence": true, "needs_review": false}
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(audio_file_id) REFERENCES audio_files(audio_file_id)
);

-- FTS5 Virtual Table for full-text search
-- Indexes both text_clean (normalized) and text_final (punctuated)
CREATE VIRTUAL TABLE segments_fts USING fts5(
  text_search,           -- combined searchable text
  segment_id UNINDEXED,  -- pointer back to segments table
  audio_file_id UNINDEXED,
  start_s UNINDEXED,
  end_s UNINDEXED,
  content = 'segments',  -- external content table
  content_rowid = 'segment_id'
);

-- Triggers to keep FTS index in sync with segments table
CREATE TRIGGER segments_ai AFTER INSERT ON segments BEGIN
  INSERT INTO segments_fts(rowid, text_search, segment_id, audio_file_id, start_s, end_s)
  VALUES (NEW.rowid, COALESCE(NEW.text_final, NEW.text_clean, NEW.text_raw), NEW.segment_id, NEW.audio_file_id, NEW.start_s, NEW.end_s);
END;

CREATE TRIGGER segments_ad AFTER DELETE ON segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text_search, segment_id, audio_file_id, start_s, end_s)
  VALUES('delete', OLD.rowid, COALESCE(OLD.text_final, OLD.text_clean, OLD.text_raw), OLD.segment_id, OLD.audio_file_id, OLD.start_s, OLD.end_s);
END;

CREATE TRIGGER segments_au AFTER UPDATE ON segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text_search, segment_id, audio_file_id, start_s, end_s)
  VALUES('delete', OLD.rowid, COALESCE(OLD.text_final, OLD.text_clean, OLD.text_raw), OLD.segment_id, OLD.audio_file_id, OLD.start_s, OLD.end_s);
  INSERT INTO segments_fts(rowid, text_search, segment_id, audio_file_id, start_s, end_s)
  VALUES (NEW.rowid, COALESCE(NEW.text_final, NEW.text_clean, NEW.text_raw), NEW.segment_id, NEW.audio_file_id, NEW.start_s, NEW.end_s);
END;

-- Indexes for common queries
CREATE INDEX idx_audio_files_book_id ON audio_files(book_id);
CREATE INDEX idx_segments_audio_file_id ON segments(audio_file_id);
CREATE INDEX idx_segments_start_end ON segments(start_s, end_s);
