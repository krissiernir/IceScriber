"""
AudiobookLearner Query Tool
Query the learning database for books, chapters, characters, etc.

Usage:
    # List all books
    python learner_query.py --list-books

    # Show book info
    python learner_query.py --info <book-id>

    # List chapters
    python learner_query.py --chapters <book-id>

    # Show chapter details
    python learner_query.py --chapter-detail <chapter-id>

    # List characters
    python learner_query.py --characters <book-id>
"""

import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import learner_db as db


def list_books():
    """List all books in the database."""
    books = db.get_books()

    if not books:
        print("No books found in database")
        return

    print(f"\n{'='*60}")
    print(f"Found {len(books)} book(s):")
    print(f"{'='*60}\n")

    for book in books:
        print(f"Title: {book['title']}")
        print(f"Author: {book.get('author', 'Unknown')}")
        print(f"ID: {book['book_id']}")
        print(f"Created: {book['created_at']}")
        print()


def show_book_info(book_id: str):
    """Show detailed book information."""
    stats = db.get_book_stats(book_id)
    book = stats['book']

    print(f"\n{'='*60}")
    print(f"Book: {book['title']}")
    print(f"{'='*60}\n")

    print(f"Author: {book.get('author', 'Unknown')}")
    print(f"Genre: {book.get('genre', 'Unknown')}")
    print(f"Language: {book.get('language', 'Unknown')}")
    print(f"ID: {book['book_id']}")
    print(f"Created: {book['created_at']}")

    print(f"\nStatistics:")
    print(f"  Chapters: {stats['chapters']}")
    print(f"  Characters: {stats['characters']}")
    print(f"  Timeline Events: {stats['timeline_events']}")

    if book.get('metadata'):
        print(f"\nMetadata:")
        metadata = json.loads(book['metadata']) if isinstance(book['metadata'], str) else book['metadata']
        for key, value in metadata.items():
            print(f"  {key}: {value}")


def list_chapters(book_id: str):
    """List all chapters for a book."""
    chapters = db.get_chapters(book_id)

    if not chapters:
        print(f"No chapters found for book {book_id}")
        return

    print(f"\n{'='*60}")
    print(f"Chapters ({len(chapters)} total):")
    print(f"{'='*60}\n")

    for chapter in chapters:
        duration_min = chapter['duration_s'] / 60
        print(f"{chapter['chapter_number']:3d}. {chapter['title']}")
        print(f"     Duration: {duration_min:.1f} min | Time: {format_timestamp(chapter['start_timestamp_s'])} - {format_timestamp(chapter['end_timestamp_s'])}")


def show_chapter_detail(chapter_id: str):
    """Show detailed chapter information."""
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM chapters WHERE chapter_id = ?", (chapter_id,))
    row = cursor.fetchone()

    if not row:
        print(f"Chapter {chapter_id} not found")
        return

    chapter = dict(row)

    print(f"\n{'='*60}")
    print(f"Chapter {chapter['chapter_number']}: {chapter['title']}")
    print(f"{'='*60}\n")

    print(f"Duration: {chapter['duration_s']/60:.1f} min")
    print(f"Time range: {format_timestamp(chapter['start_timestamp_s'])} - {format_timestamp(chapter['end_timestamp_s'])}")

    if chapter.get('audio_file_paths'):
        files = json.loads(chapter['audio_file_paths']) if isinstance(chapter['audio_file_paths'], str) else chapter['audio_file_paths']
        print(f"\nAudio files:")
        for f in files:
            print(f"  - {f}")

    # Check for summary
    cursor.execute("SELECT * FROM chapter_summaries WHERE chapter_id = ?", (chapter_id,))
    summary_row = cursor.fetchone()

    if summary_row:
        summary = dict(summary_row)
        print(f"\n--- Summary ---")
        print(summary['summary_text'])

        if summary.get('key_events'):
            events = json.loads(summary['key_events']) if isinstance(summary['key_events'], str) else summary['key_events']
            print(f"\nKey Events:")
            for event in events:
                print(f"  • {event}")

    conn.close()


def list_characters(book_id: str):
    """List all characters for a book."""
    characters = db.get_characters(book_id)

    if not characters:
        print(f"No characters found for book {book_id}")
        return

    print(f"\n{'='*60}")
    print(f"Characters ({len(characters)} total):")
    print(f"{'='*60}\n")

    for char in characters:
        print(f"{char['name']}")
        if char.get('occupation'):
            print(f"  Occupation: {char['occupation']}")
        if char.get('age'):
            print(f"  Age: {char['age']}")
        if char.get('traits'):
            traits = json.loads(char['traits']) if isinstance(char['traits'], str) else char['traits']
            print(f"  Traits: {', '.join(traits)}")
        if char.get('first_appearance_chapter'):
            print(f"  First appears: Chapter {char['first_appearance_chapter']}")
        print()


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(description="Query AudiobookLearner database")
    parser.add_argument('--list-books', action='store_true', help='List all books')
    parser.add_argument('--info', metavar='BOOK_ID', help='Show book information')
    parser.add_argument('--chapters', metavar='BOOK_ID', help='List chapters for book')
    parser.add_argument('--chapter-detail', metavar='CHAPTER_ID', help='Show chapter details')
    parser.add_argument('--characters', metavar='BOOK_ID', help='List characters for book')

    args = parser.parse_args()

    if args.list_books:
        list_books()
    elif args.info:
        show_book_info(args.info)
    elif args.chapters:
        list_chapters(args.chapters)
    elif args.chapter_detail:
        show_chapter_detail(args.chapter_detail)
    elif args.characters:
        list_characters(args.characters)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
