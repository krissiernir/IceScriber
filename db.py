"""
Database utilities for IceScriber SQLite backend.
Handles connections, schema initialization, and common queries.
"""

import sqlite3
import json
import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

DB_PATH = "transcripts.db"
SCHEMA_PATH = "schema.sql"


def get_db():
    """Get SQLite connection with FTS5 support."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    return conn


def init_db():
    """Initialize database schema if it doesn't exist."""
    if os.path.exists(DB_PATH):
        print(f"✓ Database already exists at {DB_PATH}")
        return

    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    conn = get_db()
    cursor = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()

    cursor.executescript(schema)
    conn.commit()
    conn.close()

    print(f"✓ Database initialized at {DB_PATH}")


def add_book(title: str, author: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
    """Add a book to the database. Returns book_id."""
    book_id = str(uuid.uuid4())
    metadata_str = json.dumps(metadata) if metadata else None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO books (book_id, title, author, metadata)
        VALUES (?, ?, ?, ?)
        """,
        (book_id, title, author, metadata_str),
    )

    conn.commit()
    conn.close()

    print(f"✓ Added book: {title} (ID: {book_id})")
    return book_id


def add_audio_file(
    book_id: str,
    file_path: str,
    json_path: str,
    file_number: Optional[int] = None,
    duration_s: Optional[float] = None,
) -> str:
    """Add an audio file to the database. Returns audio_file_id.
    
    Args:
        book_id: Book this audio file belongs to
        file_path: Path to audio file (.mp3, .m4a, .wav, etc.)
        json_path: Path to canonical JSON transcript
        file_number: Position in book (track 1, 2, 3...), optional
        duration_s: Duration in seconds, optional
    """
    audio_file_id = str(uuid.uuid4())

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audio_files (audio_file_id, book_id, file_number, file_path, json_path, duration_s)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (audio_file_id, book_id, file_number, file_path, json_path, duration_s),
    )

    conn.commit()
    conn.close()

    return audio_file_id


def add_segment(
    audio_file_id: str,
    start_s: float,
    end_s: float,
    text_raw: str,
    text_clean: Optional[str] = None,
    text_final: Optional[str] = None,
    flags: Optional[Dict] = None,
) -> str:
    """Add a segment to the database. Returns segment_id."""
    segment_id = str(uuid.uuid4())
    flags_str = json.dumps(flags) if flags else None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO segments (segment_id, audio_file_id, start_s, end_s, text_raw, text_clean, text_final, flags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (segment_id, audio_file_id, start_s, end_s, text_raw, text_clean, text_final, flags_str),
    )

    conn.commit()
    conn.close()

    return segment_id


def search_keyword(
    query: str, book_id: Optional[str] = None, limit: int = 50
) -> List[Dict]:
    """Search segments by keyword using full-text search (case-insensitive LIKE).

    Returns list of dicts with: segment_id, audio_file_id, file_path, start_s, end_s, text_excerpt
    """
    conn = get_db()
    cursor = conn.cursor()

    # Use LIKE for case-insensitive substring search (simpler than FTS5 with external content)
    search_pattern = f"%{query}%"

    if book_id:
        cursor.execute(
            """
            SELECT
                s.segment_id,
                s.audio_file_id,
                af.file_path,
                s.start_s,
                s.end_s,
                COALESCE(s.text_final, s.text_clean, s.text_raw) as text_excerpt
            FROM segments s
            JOIN audio_files af ON s.audio_file_id = af.audio_file_id
            WHERE (s.text_raw LIKE ? OR s.text_clean LIKE ? OR s.text_final LIKE ?)
              AND af.book_id = ?
            ORDER BY s.start_s
            LIMIT ?
            """,
            (search_pattern, search_pattern, search_pattern, book_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                s.segment_id,
                s.audio_file_id,
                af.file_path,
                s.start_s,
                s.end_s,
                COALESCE(s.text_final, s.text_clean, s.text_raw) as text_excerpt
            FROM segments s
            JOIN audio_files af ON s.audio_file_id = af.audio_file_id
            WHERE s.text_raw LIKE ? OR s.text_clean LIKE ? OR s.text_final LIKE ?
            ORDER BY s.start_s
            LIMIT ?
            """,
            (search_pattern, search_pattern, search_pattern, limit),
        )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_segment(segment_id: str) -> Optional[Dict]:
    """Get a single segment with full details."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            s.segment_id,
            s.audio_file_id,
            af.book_id,
            af.file_path,
            s.start_s,
            s.end_s,
            s.text_raw,
            s.text_clean,
            s.text_final,
            s.flags_json,
            s.created_at
        FROM segments s
        JOIN audio_files af ON s.audio_file_id = af.audio_file_id
        WHERE s.segment_id = ?
        """,
        (segment_id,),
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_context(
    audio_file_id: str, start_s: float, end_s: float, padding_s: float = 30
) -> List[Dict]:
    """Get all segments in a time range (with optional padding).

    Returns segments in chronological order.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            segment_id,
            start_s,
            end_s,
            COALESCE(text_final, text_clean, text_raw) as text
        FROM segments
        WHERE audio_file_id = ?
          AND start_s >= ? AND end_s <= ?
        ORDER BY start_s
        """,
        (audio_file_id, start_s - padding_s, end_s + padding_s),
    )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_books() -> List[Dict]:
    """Get all books in the database."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT book_id, title, author, created_at
        FROM books
        ORDER BY created_at DESC
        """
    )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_audio_files(book_id: str) -> List[Dict]:
    """Get all audio files for a book."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT audio_file_id, file_number, file_path, json_path, duration_s, created_at
        FROM audio_files
        WHERE book_id = ?
        ORDER BY file_number
        """,
        (book_id,),
    )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_book_info(book_id: str) -> Optional[Dict]:
    """Get book details with audio file count and segment count."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            b.book_id,
            b.title,
            b.author,
            COUNT(DISTINCT af.audio_file_id) as audio_file_count,
            COUNT(DISTINCT s.segment_id) as segment_count,
            SUM(af.duration_s) as total_duration_s,
            b.created_at
        FROM books b
        LEFT JOIN audio_files af ON b.book_id = af.book_id
        LEFT JOIN segments s ON af.audio_file_id = s.audio_file_id
        WHERE b.book_id = ?
        GROUP BY b.book_id
        """,
        (book_id,),
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
