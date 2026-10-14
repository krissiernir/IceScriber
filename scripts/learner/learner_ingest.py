"""
AudiobookLearner Ingestion Tool
Processes IceScriber JSON transcripts into learning database

Usage:
    # Ingest all chapters from mapping file
    python learner_ingest.py --mapping chapter_mapping.json

    # Process with LLM analysis (requires API key)
    python learner_ingest.py --mapping chapter_mapping.json --analyze

    # Process specific chapters only
    python learner_ingest.py --chapters 13,14,15 --analyze

    # Multi-book: use --book-dir for self-contained book folders
    python learner_ingest.py --book-dir data/books/the-hate-u-give --analyze

    # Auto-generate chapter mapping from audio files
    python learner_ingest.py --book-dir data/books/the-hate-u-give --auto-mapping --title "The Hate U Give" --author "Angie Thomas"
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import learner_db as db
import learner_llm
from paths import CHAPTER_MAPPING, INPUT_ICELANDIC


def load_chapter_mapping(mapping_path: str) -> Dict:
    """Load chapter mapping configuration."""
    with open(mapping_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_transcript_json(json_path: str) -> Dict:
    """Load a transcript JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_chapter_duration(transcript_data: Dict) -> float:
    """Calculate total duration from transcript segments."""
    if not transcript_data.get('segments'):
        return 0.0

    segments = transcript_data['segments']
    if not segments:
        return 0.0

    first_start = segments[0]['start']
    last_end = segments[-1]['end']

    return last_end - first_start


def get_chapter_text(transcript_data: Dict) -> str:
    """Extract all text from transcript segments."""
    if not transcript_data.get('segments'):
        return ""

    texts = [seg['text'] for seg in transcript_data['segments']]
    return " ".join(texts)


def auto_generate_mapping(audio_folder: str, transcripts_folder: str, title: str,
                          author: str = None, genre: str = None,
                          language: str = "english") -> Dict:
    """Auto-generate a chapter mapping from audio files in a folder."""
    audio_dir = Path(audio_folder)
    audio_files = sorted(
        f.name for f in audio_dir.iterdir()
        if f.suffix.lower() in ('.mp3', '.m4a', '.wav')
    )

    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {audio_folder}")

    chapters = []
    for i, filename in enumerate(audio_files, start=1):
        # Derive chapter title from filename (strip extension, replace underscores)
        stem = Path(filename).stem
        chapter_title = stem.replace('_', ' ').replace('-', ' ').strip()
        # JSON file lives in transcripts/ with lowercase stem
        json_filename = f"{stem.lower()}.json"
        chapters.append({
            "number": i,
            "title": chapter_title,
            "files": [json_filename]
        })

    mapping = {
        "book_title": title,
        "author": author or "Unknown",
        "genre": genre or "Non-fiction",
        "language": language,
        "chapters": chapters
    }

    return mapping


def ingest_basic_structure(mapping_path: str, transcripts_folder: str):
    """
    Ingest basic book and chapter structure without LLM analysis.
    This is the fast first pass - just loads the structure.
    """
    print("=== AudiobookLearner Ingestion ===\n")

    # Load mapping
    print(f"Loading chapter mapping: {mapping_path}")
    mapping = load_chapter_mapping(mapping_path)

    # Create book (returns existing ID if already present)
    print(f"\nCreating book: {mapping['book_title']}")
    book_id = db.add_book(
        title=mapping['book_title'],
        author=mapping.get('author'),
        genre=mapping.get('genre'),
        language=mapping.get('language', 'icelandic'),
        transcript_source=transcripts_folder,
        metadata={"mapping_file": mapping_path}
    )

    # Process chapters
    print(f"\nProcessing {len(mapping['chapters'])} chapters...")
    cumulative_time = 0.0

    for chapter_config in mapping['chapters']:
        chapter_num = chapter_config['number']
        chapter_title = chapter_config['title']
        files = chapter_config['files']

        print(f"\n--- Chapter {chapter_num}: {chapter_title} ---")

        # Load transcript(s) for this chapter
        chapter_duration = 0.0
        all_segments = []

        for json_filename in files:
            json_path = Path(transcripts_folder) / json_filename

            if not json_path.exists():
                print(f"⚠️  Warning: {json_filename} not found in {transcripts_folder}, skipping")
                continue

            print(f"  Loading: {json_filename}")
            transcript_data = load_transcript_json(str(json_path))

            duration = calculate_chapter_duration(transcript_data)
            chapter_duration += duration

            if transcript_data.get('segments'):
                all_segments.extend(transcript_data['segments'])

        if chapter_duration == 0:
            print(f"  ⚠️  No valid transcript data found for chapter {chapter_num}")
            continue

        chapter_start = cumulative_time
        chapter_end = cumulative_time + chapter_duration

        db.add_chapter(
            book_id=book_id,
            chapter_number=chapter_num,
            title=chapter_title,
            audio_file_paths=files,
            start_timestamp_s=chapter_start,
            end_timestamp_s=chapter_end,
            duration_s=chapter_duration
        )

        print(f"  Duration: {chapter_duration:.1f}s ({chapter_duration/60:.1f} min)")
        print(f"  Segments: {len(all_segments)}")
        print(f"  Time range: [{format_timestamp(chapter_start)} - {format_timestamp(chapter_end)}]")

        cumulative_time = chapter_end

    print("\n" + "="*60)
    print("✓ Basic structure ingestion complete!")
    print(f"  Book ID: {book_id}")
    print(f"  Total duration: {cumulative_time:.1f}s ({cumulative_time/3600:.2f} hours)")
    print("\nNext step: Run with --analyze to extract characters and generate summaries")

    return book_id


def write_flashcard_markdown(
    book_dir: Optional[Path],
    chapter_number: int,
    chapter_title: str,
    extracted: Dict
):
    """Write Gemini-generated flashcard markdown to markdown/ subfolder."""
    if not book_dir:
        return

    markdown_dir = book_dir / "markdown"
    markdown_dir.mkdir(exist_ok=True)

    # Build filename from chapter number + title
    slug = chapter_title.lower().replace(' ', '_').replace('/', '_')[:50]
    filename = f"{chapter_number:02d}_{slug}.md"
    filepath = markdown_dir / filename

    lines = [f"# Chapter {chapter_number}: {chapter_title}", ""]

    summary = extracted.get('summary', '')
    if summary:
        lines += ["## Summary", summary, ""]

    key_events = extracted.get('key_events', [])
    if key_events:
        lines.append("## Key Events")
        for event in key_events:
            lines.append(f"- {event}")
        lines.append("")

    characters = extracted.get('characters', [])
    if characters:
        lines.append("## Characters in This Chapter")
        for char in characters:
            name = char.get('name', '')
            desc = char.get('actions') or char.get('occupation') or ''
            if desc:
                lines.append(f"- **{name}**: {desc}")
            else:
                lines.append(f"- **{name}**")
        lines.append("")

    key_concepts = extracted.get('key_concepts', [])
    if key_concepts:
        lines.append("## Key Concepts / Vocabulary")
        for concept in key_concepts:
            if isinstance(concept, dict):
                lines.append(f"- **{concept.get('term', concept)}**: {concept.get('definition', '')}")
            else:
                lines.append(f"- {concept}")
        lines.append("")

    study_questions = extracted.get('study_questions', [])
    if study_questions:
        lines.append("## Study Questions")
        for i, q in enumerate(study_questions, 1):
            lines.append(f"{i}. {q}")
        lines.append("")

    timeline_events = extracted.get('timeline_events', [])
    if timeline_events:
        lines.append("## Key Quotes / Moments")
        for event in timeline_events[:5]:
            desc = event.get('event', '') if isinstance(event, dict) else str(event)
            if desc:
                lines.append(f"> {desc}")
        lines.append("")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"    ✓ Wrote flashcard: markdown/{filename}")


def analyze_chapter_with_llm(
    book_id: str,
    chapter_id: str,
    chapter_number: int,
    chapter_title: str,
    transcript_text: str,
    llm_processor: learner_llm.LLMProcessor,
    book_dir: Optional[Path] = None
):
    """
    Analyze a chapter using LLM to extract:
    - Summary
    - Characters
    - Key events
    - Timeline events
    - Study questions
    Also writes a flashcard markdown file to book_dir/markdown/.
    """
    print(f"  [LLM Analysis] Processing chapter {chapter_number}...")

    extracted = llm_processor.extract_chapter_content(
        chapter_text=transcript_text,
        chapter_number=chapter_number,
        chapter_title=chapter_title
    )

    # Add chapter summary to DB
    if extracted.get('summary'):
        db.add_chapter_summary(
            chapter_id=chapter_id,
            summary_text=extracted['summary'],
            key_events=extracted.get('key_events', []),
            key_concepts=extracted.get('key_concepts', []),
            plot_points=[],
            study_questions=extracted.get('study_questions', [])
        )
        print(f"    ✓ Added summary")

    # Add characters to DB
    for char_data in extracted.get('characters', []):
        try:
            char_id = db.add_character(
                book_id=book_id,
                name=char_data['name'],
                aliases=char_data.get('aliases', []),
                age=char_data.get('age'),
                occupation=char_data.get('occupation'),
                traits=char_data.get('traits', []),
                first_appearance_chapter=chapter_number,
                description=char_data.get('actions', '')
            )

            if char_data.get('actions'):
                db.add_character_event(
                    character_id=char_id,
                    chapter_id=chapter_id,
                    event_description=char_data['actions'],
                    event_type="action"
                )

            print(f"    ✓ Added character: {char_data['name']}")
        except Exception as e:
            print(f"    ⚠️  Error adding character {char_data.get('name')}: {e}")

    # Add timeline events to DB
    for event_data in extracted.get('timeline_events', []):
        try:
            db.add_timeline_event(
                book_id=book_id,
                chapter_id=chapter_id,
                event_description=event_data.get('event', ''),
                event_date=event_data.get('date'),
                event_time=event_data.get('time'),
                location=event_data.get('location')
            )
        except Exception as e:
            print(f"    ⚠️  Error adding timeline event: {e}")

    # Write flashcard markdown
    write_flashcard_markdown(book_dir, chapter_number, chapter_title, extracted)

    print(f"    ✓ Analysis complete!")


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(description="Ingest IceScriber transcripts into learning database")
    parser.add_argument('--mapping', default=None, help='Path to chapter mapping file')
    parser.add_argument('--audio-folder', default=None, help='Folder containing transcript JSONs')
    parser.add_argument('--analyze', action='store_true', help='Run LLM analysis (requires API key)')
    parser.add_argument('--chapter', type=int, help='Process only this single chapter number')
    parser.add_argument('--chapters', type=str, default=None,
                        help='Comma-separated chapter numbers to analyze (e.g. 13,14,15)')
    parser.add_argument('--reset', action='store_true', help='Delete existing database and start fresh')
    parser.add_argument('--book-dir', type=str, default=None,
                        help='Book directory (e.g., data/books/the-hate-u-give). Uses <dir>/transcripts/, <dir>/chapter_mapping.json, <dir>/learner.db')
    parser.add_argument('--auto-mapping', action='store_true',
                        help='Auto-generate chapter_mapping.json from audio files in --book-dir')
    parser.add_argument('--title', type=str, default=None, help='Book title (used with --auto-mapping)')
    parser.add_argument('--author', type=str, default=None, help='Book author (used with --auto-mapping)')
    parser.add_argument('--genre', type=str, default=None, help='Book genre (used with --auto-mapping)')
    parser.add_argument('--language', type=str, default=None, help='Book language (used with --auto-mapping)')

    args = parser.parse_args()

    # Build chapter filter set
    chapter_filter: Optional[set] = None
    if args.chapters:
        chapter_filter = {int(c.strip()) for c in args.chapters.split(",")}
    elif args.chapter is not None:
        chapter_filter = {args.chapter}

    # Resolve paths from --book-dir or defaults
    book_dir_path: Optional[Path] = None
    if args.book_dir:
        book_dir_path = Path(args.book_dir)
        transcripts_folder = str(book_dir_path / "transcripts")
        audio_folder = str(book_dir_path / "audio")
        mapping_path = str(book_dir_path / "chapter_mapping.json")
        db_path = str(book_dir_path / "learner.db")

        db.DB_PATH = db_path

        book_dir_path.mkdir(parents=True, exist_ok=True)
        (book_dir_path / "audio").mkdir(exist_ok=True)
        (book_dir_path / "transcripts").mkdir(exist_ok=True)
    else:
        audio_folder = args.audio_folder or str(INPUT_ICELANDIC)
        transcripts_folder = audio_folder
        mapping_path = args.mapping or str(CHAPTER_MAPPING)
        db_path = db.DB_PATH

    # Auto-generate chapter mapping if requested
    if args.auto_mapping:
        if not args.book_dir:
            print("❌ --auto-mapping requires --book-dir")
            return
        if not args.title:
            print("❌ --auto-mapping requires --title")
            return

        print(f"Auto-generating chapter mapping from: {audio_folder}")
        mapping = auto_generate_mapping(
            audio_folder=audio_folder,
            transcripts_folder=transcripts_folder,
            title=args.title,
            author=args.author,
            genre=args.genre,
            language=args.language or "english"
        )

        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved chapter mapping: {mapping_path}")
        print(f"  {len(mapping['chapters'])} chapters mapped")

        if not args.analyze:
            print("\nNext: Run with --analyze to ingest and extract content")
            return

    # Reset database if requested
    if args.reset:
        if Path(db_path).exists():
            print(f"Removing existing database: {db_path}")
            Path(db_path).unlink()
        db.initialize_database(db_path)

    # Make sure database exists
    if not Path(db_path).exists():
        db.initialize_database(db_path)

    # Ingest basic structure
    book_id = ingest_basic_structure(mapping_path, transcripts_folder)

    # LLM analysis (if requested)
    if args.analyze:
        print("\n=== LLM Analysis Phase ===")
        if chapter_filter:
            print(f"  Chapters: {sorted(chapter_filter)}")

        try:
            llm_processor = learner_llm.LLMProcessor(provider="gemini")
        except Exception as e:
            print(f"❌ Error initializing LLM: {e}")
            print("Skipping analysis. Make sure GEMINI_API_KEY is set in .env file")
            return

        chapters = db.get_chapters(book_id)

        for chapter in chapters:
            chapter_num = chapter['chapter_number']
            chapter_title = chapter['title']
            chapter_id = chapter['chapter_id']

            if chapter_filter is not None and chapter_num not in chapter_filter:
                continue

            print(f"\n--- Analyzing Chapter {chapter_num}: {chapter_title} ---")

            audio_files = json.loads(chapter['audio_file_paths']) if isinstance(chapter['audio_file_paths'], str) else chapter['audio_file_paths']
            chapter_text = ""

            for json_filename in audio_files:
                json_path = Path(transcripts_folder) / json_filename
                if json_path.exists():
                    transcript_data = load_transcript_json(str(json_path))
                    chapter_text += get_chapter_text(transcript_data) + " "

            if not chapter_text.strip():
                print(f"  ⚠️  No transcript text found, skipping")
                continue

            try:
                analyze_chapter_with_llm(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    chapter_number=chapter_num,
                    chapter_title=chapter_title,
                    transcript_text=chapter_text[:20000],
                    llm_processor=llm_processor,
                    book_dir=book_dir_path
                )

                llm_processor.rate_limit_pause()

            except Exception as e:
                print(f"  ❌ Error analyzing chapter: {e}")

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
