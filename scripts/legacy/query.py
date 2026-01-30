#!/usr/bin/env python3
"""
Query IceScriber SQLite database for audiobook transcripts.

Provides CLI interface for:
- Keyword search across all segments (using FTS5)
- List books and audio files
- Show book statistics
- Retrieve segment details with timestamps

Citation Format: filename [HH:MM:SS–HH:MM:SS]: ...excerpt...

Usage:
    python query.py "keyword"                       # Search all books for keyword
    python query.py "keyword" --book-id <id>       # Search specific book
    python query.py "keyword" --limit 20            # Limit results
    python query.py --list-books                    # Show all books
    python query.py --list-audio-files <book_id>   # Show audio files in book
    python query.py --info <book_id>                # Book statistics
    python query.py --segment <segment_id>         # Show full segment details
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from db import (
    get_db,
    search_keyword,
    get_books,
    get_book_info,
    get_audio_files,
    format_timestamp,
)


def format_citation(result: Dict[str, Any]) -> str:
    """Format a search result as a citation."""
    filename = Path(result["file_path"]).name
    start_ts = format_timestamp(result["start_s"])
    end_ts = format_timestamp(result["end_s"])
    excerpt = result["text_excerpt"]

    return f"{filename} [{start_ts}–{end_ts}]: {excerpt}"


def search_and_display(query: str, book_id: Optional[str] = None, limit: int = 50) -> None:
    """Search for keyword and display results with citations."""
    results = search_keyword(query, book_id=book_id, limit=limit)

    if not results:
        print(f"\n❌ No results found for: '{query}'\n")
        return

    print(f"\n🔍 Found {len(results)} result(s) for: '{query}'\n")
    print(f"{'─' * 80}\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {format_citation(result)}")
        print()

    print(f"{'─' * 80}\n")


def list_books() -> None:
    """Display all books in database."""
    books = get_books()

    if not books:
        print("\n📚 No books in database.\n")
        return

    print(f"\n📚 Books in Database:\n")
    print(f"{'─' * 80}\n")

    for book in books:
        book_id = book["book_id"]
        title = book["title"]
        author = book["author"] or "(unknown author)"

        # Get detailed stats
        info = get_book_info(book_id)
        if info:
            audio_file_count = info["audio_file_count"]
            segment_count = info["segment_count"]
            duration = info["total_duration_s"]

            duration_str = ""
            if duration:
                hours = duration / 3600
                duration_str = f" • {hours:.1f}h"

            print(f"  {title}")
            print(f"    Author: {author}")
            print(f"    Audio Files: {audio_file_count} • Segments: {segment_count}{duration_str}")
            print(f"    ID: {book_id}")
            print()

    print(f"{'─' * 80}\n")


def list_audio_files(book_id: str) -> None:
    """Display audio files (tracks, chapters, parts, etc.) in a book."""
    audio_files = get_audio_files(book_id)

    if not audio_files:
        print(f"\n❌ Book not found or has no audio files: {book_id}\n")
        return

    # Get book title for context
    db = get_db()
    book = db.execute(
        "SELECT title FROM books WHERE book_id = ?", (book_id,)
    ).fetchone()
    book_title = book["title"] if book else "Unknown Book"

    print(f"\n📚 Audio Files in '{book_title}':\n")
    print(f"{'─' * 80}\n")

    for audio_file in audio_files:
        filename = Path(audio_file["file_path"]).name
        file_number = audio_file["file_number"] or "—"
        duration = audio_file["duration_s"]

        duration_str = ""
        if duration:
            minutes = duration / 60
            duration_str = f" • {minutes:.1f}m"

        print(f"  {filename}")
        print(f"    Track/File #: {file_number} • Duration: {duration}{duration_str}")
        print(f"    ID: {audio_file['audio_file_id']}")
        print()

    print(f"{'─' * 80}\n")


def show_book_info(book_id: str) -> None:
    """Display detailed statistics for a book."""
    db = get_db()
    book = db.execute(
        "SELECT * FROM books WHERE book_id = ?", (book_id,)
    ).fetchone()

    if not book:
        print(f"\n❌ Book not found: {book_id}\n")
        return

    info = get_book_info(book_id)

    print(f"\n{'═' * 80}")
    print(f"📚 Book Information")
    print(f"{'═' * 80}\n")

    print(f"Title: {book['title']}")
    if book['author']:
        print(f"Author: {book['author']}")

    if info:
        print(f"\nStatistics:")
        print(f"  • Audio Files: {info['audio_file_count']}")
        print(f"  • Segments (time windows): {info['segment_count']}")

        if info["total_duration_s"]:
            hours = info["total_duration_s"] / 3600
            print(f"  • Total Duration: {hours:.1f} hours")

    print(f"\nID: {book_id}")
    print(f"\n{'═' * 80}\n")


def show_segment(segment_id: str) -> None:
    """Display full details of a segment."""
    db = get_db()
    segment = db.execute(
        """
        SELECT 
            s.segment_id,
            s.audio_file_id,
            s.start_s,
            s.end_s,
            s.text_raw,
            s.text_final,
            af.file_path
        FROM segments s
        JOIN audio_files af ON s.audio_file_id = af.audio_file_id
        WHERE s.segment_id = ?
        """,
        (segment_id,),
    ).fetchone()

    if not segment:
        print(f"\n❌ Segment not found: {segment_id}\n")
        return

    filename = Path(segment["file_path"]).name
    start_ts = format_timestamp(segment["start_s"])
    end_ts = format_timestamp(segment["end_s"])

    print(f"\n{'═' * 80}")
    print(f"📄 Segment Details")
    print(f"{'═' * 80}\n")

    print(f"File: {filename}")
    print(f"Time Range: {start_ts} – {end_ts}")
    print(f"Duration: {segment['end_s'] - segment['start_s']:.1f}s")
    print(f"\nSegment ID: {segment_id}")
    print(f"Audio File ID: {segment['audio_file_id']}")

    print(f"\nText (final):")
    print(f"{segment['text_final']}")

    if segment["text_raw"] and segment["text_raw"] != segment["text_final"]:
        print(f"\nText (raw):")
        print(f"{segment['text_raw']}")

    print(f"\n{'═' * 80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Query IceScriber audiobook transcripts from SQLite database",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Keyword to search for (FTS5 full-text search)",
    )
    parser.add_argument(
        "--book-id",
        help="Search within specific book (book_id)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum results to return (default: 50)",
    )
    parser.add_argument(
        "--list-books",
        action="store_true",
        help="List all books in database",
    )
    parser.add_argument(
        "--list-audio-files",
        help="List audio files in a book (requires book_id)",
    )
    parser.add_argument(
        "--info",
        help="Show detailed statistics for a book (requires book_id)",
    )
    parser.add_argument(
        "--segment",
        help="Show full details of a segment (requires segment_id)",
    )

    args = parser.parse_args()

    # Check if database exists
    if not Path("transcripts.db").exists():
        print("\n❌ Database not found: transcripts.db")
        print("   Run: python ingest.py --all\n")
        sys.exit(1)

    if args.list_books:
        list_books()
    elif args.list_audio_files:
        list_audio_files(args.list_audio_files)
    elif args.info:
        show_book_info(args.info)
    elif args.segment:
        show_segment(args.segment)
    elif args.query:
        search_and_display(args.query, book_id=args.book_id, limit=args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
