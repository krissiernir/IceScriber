#!/usr/bin/env python3
"""
Ingest IceScriber JSON transcripts into SQLite database.

Model: JSON is the canonical artifact (source of truth) per audio file.
- One JSON per audio file (.mp3, .m4a, .wav, etc.)
- Segments inside JSON = time windows (typically 5-30 seconds)
- Book = collection of audio files
- AudioFile = fundamental unit (can be named track, chapter, disk, part, etc.)

Usage:
    python ingest.py --all                                      # Ingest all .json files as audio files
    python ingest.py --all --book-title "My Book" --author "..." # Specify book metadata
    python ingest.py --rescan                                   # Rebuild database from all JSON files
    python ingest.py <json_file> --book-id <id>               # Add single audio file to existing book
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional
import argparse

from db import (
    init_db,
    add_book,
    add_audio_file,
    add_segment,
    get_book_info,
)


def ingest_json_file(json_path: str, book_id: str) -> str:
    """
    Ingest a single JSON transcript file (representing one audio file) into the database.

    Args:
        json_path: Path to JSON transcript file (canonical source of truth)
        book_id: book_id to associate this audio file with (required)

    Returns:
        audio_file_id of the ingested audio file
    """
    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract metadata
    metadata = data.get("metadata", {})
    audio_file_name = metadata.get("audio_file", "Unknown")
    duration_s = metadata.get("duration_s")

    # Extract file number from filename (e.g., "001_Daudi_trudsins.mp3" → 1)
    file_number = extract_file_number(audio_file_name)

    # Construct audio file path (assume it's in same dir as JSON)
    audio_file_path = str(json_path).replace(".json", "")

    # Add audio file to the book
    audio_file_id = add_audio_file(
        book_id=book_id,
        file_path=audio_file_path,
        json_path=str(json_path),
        file_number=file_number,
        duration_s=duration_s,
    )

    # Ingest segments (time windows within this audio file, typically 5-30 seconds each)
    segments = data.get("segments", [])
    segment_count = 0

    for segment in segments:
        start_s = segment.get("start", 0)
        end_s = segment.get("end", 0)
        text = segment.get("text", "")

        if not text.strip():
            continue

        add_segment(
            audio_file_id=audio_file_id,
            start_s=start_s,
            end_s=end_s,
            text_raw=text,
            text_final=text,  # JSON already has punctuation applied
        )
        segment_count += 1

    print(
        f"✓ Ingested {json_path.name}: {segment_count} segments → audio_file_id={audio_file_id}"
    )

    return audio_file_id


def extract_file_number(filename: str) -> Optional[int]:
    """Extract file number from filename if present."""
    parts = filename.split("_")
    if parts and parts[0].isdigit():
        return int(parts[0])
    return None


def ingest_all_json_files(directory: str = "audio_chapters", book_title: str = None, author: str = None) -> None:
    """
    Ingest all .json files from a directory into a single book.

    Each JSON file = one audio file of the book.
    Segments within = time windows (5-30s clips), not audio files.

    Args:
        directory: Folder containing JSON transcript files
        book_title: Title for the book (required for clarity)
        author: Author name (optional)
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Directory not found: {directory}")
        return

    json_files = sorted(dir_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {directory}")
        return

    # If no book title provided, ask user
    if not book_title:
        print(f"\n📚 Found {len(json_files)} JSON files in {directory}/")
        print("   Note: Each .json file = 1 audio file. Segments within = time windows (not audio files).\n")
        book_title = input("Enter book title: ").strip()
        if not book_title:
            book_title = f"Audiobook ({len(json_files)} files)"

    if not author:
        author_input = input("Enter author (optional): ").strip()
        author = author_input if author_input else None

    # Create book
    book_id = add_book(
        title=book_title,
        author=author,
        metadata={"source": directory, "audio_file_count": len(json_files)},
    )

    print(f"\n📚 Book: {book_title}")
    if author:
        print(f"   Author: {author}")
    print(f"📂 Ingesting {len(json_files)} audio files...\n")

    ingested_count = 0
    for json_file in json_files:
        try:
            ingest_json_file(str(json_file), book_id=book_id)
            ingested_count += 1
        except Exception as e:
            print(f"✗ Error ingesting {json_file.name}: {e}")

    # Print summary
    book_info = get_book_info(book_id)
    if book_info:
        print(f"\n{'='*60}")
        print(f"✅ Ingestion complete!")
        print(f"   Book: {book_info['title']}")
        print(f"   Audio Files: {book_info['audio_file_count']}")
        print(f"   Total Segments (time windows): {book_info['segment_count']}")
        if book_info["total_duration_s"]:
            hours = book_info["total_duration_s"] / 3600
            print(f"   Total Duration: {hours:.1f} hours")
        print(f"   Book ID: {book_id}")
        print(f"{'='*60}\n")


def rescan_all_json_files(directory: str = "audio_chapters", book_title: str = None, author: str = None) -> None:
    """
    Rebuild database from all JSON files.

    Useful if you've modified JSON files or want a fresh start.
    """
    db_path = "transcripts.db"

    if os.path.exists(db_path):
        print(f"⚠️  Removing existing database: {db_path}")
        os.remove(db_path)

    print("🔄 Reinitializing database...")
    init_db()

    print()
    ingest_all_json_files(directory, book_title=book_title, author=author)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest IceScriber JSON transcripts into SQLite database",
        epilog="Note: Each JSON file = one audio file. Segments within = time windows (5-30s), not audio files."
    )
    parser.add_argument("file", nargs="?", help="Path to JSON file to ingest (requires --book-id)")
    parser.add_argument("--all", action="store_true", help="Ingest all .json files as audio files of one book")
    parser.add_argument(
        "--rescan",
        action="store_true",
        help="Rebuild database from all JSON files (destructive)",
    )
    parser.add_argument(
        "--dir",
        default="audio_chapters",
        help="Directory to scan for JSON files (default: audio_chapters)",
    )
    parser.add_argument(
        "--book-id",
        help="Existing book_id to add audio file to (for single file ingestion)"
    )
    parser.add_argument(
        "--book-title",
        help="Book title (used with --all or --rescan)"
    )
    parser.add_argument(
        "--author",
        help="Author name (used with --all or --rescan)"
    )

    args = parser.parse_args()

    # Initialize database if it doesn't exist
    if not os.path.exists("transcripts.db"):
        print("🗄️  Initializing database...\n")
        init_db()

    if args.rescan:
        rescan_all_json_files(args.dir, book_title=args.book_title, author=args.author)
    elif args.all:
        ingest_all_json_files(args.dir, book_title=args.book_title, author=args.author)
    elif args.file:
        if not args.book_id:
            print("❌ Single file ingestion requires --book-id\n")
            parser.print_help()
            sys.exit(1)
        ingest_json_file(args.file, book_id=args.book_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
