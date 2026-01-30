"""
AudiobookLearner Database Utilities
Handles all database operations for the learning assistant
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from paths import LEARNER_DB, SRC_DIR

DB_PATH = str(LEARNER_DB)
SCHEMA_PATH = str(SRC_DIR / "learner_schema.sql")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get database connection with proper settings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def initialize_database(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH):
    """Initialize database with schema."""
    if Path(db_path).exists():
        print(f"Database already exists: {db_path}")
        return

    print(f"Creating database: {db_path}")

    # Read schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Create database
    conn = get_connection(db_path)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    print(f"✓ Database initialized: {db_path}")


def add_book(
    title: str,
    author: str = None,
    genre: str = None,
    language: str = "icelandic",
    transcript_source: str = None,
    metadata: Dict = None,
    db_path: str = DB_PATH
) -> str:
    """Add a book to the database. Returns book_id."""
    book_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO books (book_id, title, author, genre, language, transcript_source, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        book_id,
        title,
        author,
        genre,
        language,
        transcript_source,
        json.dumps(metadata) if metadata else None
    ))

    conn.commit()
    conn.close()

    print(f"✓ Added book: {title} (ID: {book_id})")
    return book_id


def add_chapter(
    book_id: str,
    chapter_number: int,
    title: str = None,
    audio_file_paths: List[str] = None,
    start_timestamp_s: float = 0.0,
    end_timestamp_s: float = 0.0,
    duration_s: float = 0.0,
    db_path: str = DB_PATH
) -> str:
    """Add a chapter to the database. Returns chapter_id."""
    chapter_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chapters (
            chapter_id, book_id, chapter_number, title,
            audio_file_paths, start_timestamp_s, end_timestamp_s, duration_s
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chapter_id,
        book_id,
        chapter_number,
        title,
        json.dumps(audio_file_paths) if audio_file_paths else None,
        start_timestamp_s,
        end_timestamp_s,
        duration_s
    ))

    conn.commit()
    conn.close()

    print(f"✓ Added chapter {chapter_number}: {title or '(untitled)'} (ID: {chapter_id})")
    return chapter_id


def add_chapter_summary(
    chapter_id: str,
    summary_text: str,
    key_events: List[str] = None,
    key_concepts: List[str] = None,
    plot_points: List[str] = None,
    study_questions: List[str] = None,
    db_path: str = DB_PATH
) -> str:
    """Add a chapter summary. Returns summary_id."""
    summary_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chapter_summaries (
            summary_id, chapter_id, summary_text,
            key_events, key_concepts, plot_points, study_questions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        summary_id,
        chapter_id,
        summary_text,
        json.dumps(key_events) if key_events else None,
        json.dumps(key_concepts) if key_concepts else None,
        json.dumps(plot_points) if plot_points else None,
        json.dumps(study_questions) if study_questions else None
    ))

    conn.commit()

    # Add to FTS index
    cursor.execute("""
        INSERT INTO chapter_summaries_fts (summary_text, summary_id, chapter_id)
        VALUES (?, ?, ?)
    """, (summary_text, summary_id, chapter_id))

    conn.commit()
    conn.close()

    return summary_id


def add_character(
    book_id: str,
    name: str,
    aliases: List[str] = None,
    age: int = None,
    occupation: str = None,
    traits: List[str] = None,
    first_appearance_chapter: int = None,
    description: str = None,
    metadata: Dict = None,
    db_path: str = DB_PATH
) -> str:
    """Add a character. Returns character_id."""
    character_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO characters (
            character_id, book_id, name, aliases, age, occupation,
            traits, first_appearance_chapter, description, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        character_id,
        book_id,
        name,
        json.dumps(aliases) if aliases else None,
        age,
        occupation,
        json.dumps(traits) if traits else None,
        first_appearance_chapter,
        description,
        json.dumps(metadata) if metadata else None
    ))

    conn.commit()
    conn.close()

    print(f"✓ Added character: {name}")
    return character_id


def add_character_event(
    character_id: str,
    chapter_id: str,
    event_description: str,
    event_type: str = None,
    timestamp_s: float = None,
    importance: int = 5,
    db_path: str = DB_PATH
) -> str:
    """Add a character event. Returns event_id."""
    event_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO character_events (
            event_id, character_id, chapter_id, event_type,
            event_description, timestamp_s, importance
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        character_id,
        chapter_id,
        event_type,
        event_description,
        timestamp_s,
        importance
    ))

    conn.commit()
    conn.close()

    return event_id


def add_timeline_event(
    book_id: str,
    event_description: str,
    chapter_id: str = None,
    event_date: str = None,
    event_time: str = None,
    participants: List[str] = None,
    location: str = None,
    timestamp_s: float = None,
    importance: int = 5,
    db_path: str = DB_PATH
) -> str:
    """Add a timeline event. Returns timeline_event_id."""
    timeline_event_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO timeline_events (
            timeline_event_id, book_id, chapter_id, event_date, event_time,
            event_description, participants, location, timestamp_s, importance
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timeline_event_id,
        book_id,
        chapter_id,
        event_date,
        event_time,
        event_description,
        json.dumps(participants) if participants else None,
        location,
        timestamp_s,
        importance
    ))

    conn.commit()
    conn.close()

    return timeline_event_id


def add_study_note(
    chapter_id: str,
    note_type: str,
    content_markdown: str,
    db_path: str = DB_PATH
) -> str:
    """Add a study note. Returns note_id."""
    note_id = str(uuid.uuid4())

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_notes (note_id, chapter_id, note_type, content_markdown)
        VALUES (?, ?, ?, ?)
    """, (note_id, chapter_id, note_type, content_markdown))

    conn.commit()

    # Add to FTS index
    cursor.execute("""
        INSERT INTO study_notes_fts (content_markdown, note_id, chapter_id)
        VALUES (?, ?, ?)
    """, (content_markdown, note_id, chapter_id))

    conn.commit()
    conn.close()

    return note_id


def get_books(db_path: str = DB_PATH) -> List[Dict]:
    """Get all books."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books ORDER BY created_at DESC")
    rows = cursor.fetchall()

    conn.close()

    books = []
    for row in rows:
        book = dict(row)
        if book.get('metadata'):
            book['metadata'] = json.loads(book['metadata'])
        books.append(book)

    return books


def get_chapters(book_id: str, db_path: str = DB_PATH) -> List[Dict]:
    """Get all chapters for a book."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM chapters
        WHERE book_id = ?
        ORDER BY chapter_number
    """, (book_id,))

    rows = cursor.fetchall()
    conn.close()

    chapters = []
    for row in rows:
        chapter = dict(row)
        if chapter.get('audio_file_paths'):
            chapter['audio_file_paths'] = json.loads(chapter['audio_file_paths'])
        chapters.append(chapter)

    return chapters


def get_characters(book_id: str, db_path: str = DB_PATH) -> List[Dict]:
    """Get all characters for a book."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM characters
        WHERE book_id = ?
        ORDER BY first_appearance_chapter, name
    """, (book_id,))

    rows = cursor.fetchall()
    conn.close()

    characters = []
    for row in rows:
        char = dict(row)
        for json_field in ['aliases', 'traits', 'metadata']:
            if char.get(json_field):
                char[json_field] = json.loads(char[json_field])
        characters.append(char)

    return characters


def search_study_notes(query: str, chapter_id: str = None, db_path: str = DB_PATH) -> List[Dict]:
    """Search study notes using FTS5."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if chapter_id:
        cursor.execute("""
            SELECT sn.*, fts.rank
            FROM study_notes_fts fts
            JOIN study_notes sn ON fts.note_id = sn.note_id
            WHERE fts.content_markdown MATCH ? AND sn.chapter_id = ?
            ORDER BY fts.rank
        """, (query, chapter_id))
    else:
        cursor.execute("""
            SELECT sn.*, fts.rank
            FROM study_notes_fts fts
            JOIN study_notes sn ON fts.note_id = sn.note_id
            WHERE fts.content_markdown MATCH ?
            ORDER BY fts.rank
        """, (query,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_book_stats(book_id: str, db_path: str = DB_PATH) -> Dict:
    """Get statistics for a book."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Get book info
    cursor.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))
    book = dict(cursor.fetchone())

    # Count chapters
    cursor.execute("SELECT COUNT(*) as count FROM chapters WHERE book_id = ?", (book_id,))
    chapter_count = cursor.fetchone()['count']

    # Count characters
    cursor.execute("SELECT COUNT(*) as count FROM characters WHERE book_id = ?", (book_id,))
    character_count = cursor.fetchone()['count']

    # Count timeline events
    cursor.execute("SELECT COUNT(*) as count FROM timeline_events WHERE book_id = ?", (book_id,))
    timeline_count = cursor.fetchone()['count']

    conn.close()

    return {
        'book': book,
        'chapters': chapter_count,
        'characters': character_count,
        'timeline_events': timeline_count
    }


if __name__ == "__main__":
    # Test database initialization
    initialize_database()
    print("\n✓ Database utilities loaded successfully")
