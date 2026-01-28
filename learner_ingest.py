"""
AudiobookLearner Ingestion Tool
Processes IceScriber JSON transcripts into learning database

Usage:
    # Ingest all chapters from mapping file
    python learner_ingest.py --mapping chapter_mapping.json

    # Process with LLM analysis (requires API key)
    python learner_ingest.py --mapping chapter_mapping.json --analyze

    # Process single chapter
    python learner_ingest.py --chapter 1 --analyze
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import learner_db as db
import learner_llm


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

    # Duration is from first segment start to last segment end
    first_start = segments[0]['start']
    last_end = segments[-1]['end']

    return last_end - first_start


def get_chapter_text(transcript_data: Dict) -> str:
    """Extract all text from transcript segments."""
    if not transcript_data.get('segments'):
        return ""

    texts = [seg['text'] for seg in transcript_data['segments']]
    return " ".join(texts)


def ingest_basic_structure(mapping_path: str, audio_folder: str = "audio_chapters"):
    """
    Ingest basic book and chapter structure without LLM analysis.
    This is the fast first pass - just loads the structure.
    """
    print("=== AudiobookLearner Ingestion ===\n")

    # Load mapping
    print(f"Loading chapter mapping: {mapping_path}")
    mapping = load_chapter_mapping(mapping_path)

    # Create book
    print(f"\nCreating book: {mapping['book_title']}")
    book_id = db.add_book(
        title=mapping['book_title'],
        author=mapping.get('author'),
        genre=mapping.get('genre'),
        language='icelandic',
        transcript_source=audio_folder,
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
            json_path = Path(audio_folder) / json_filename

            if not json_path.exists():
                print(f"⚠️  Warning: {json_filename} not found, skipping")
                continue

            print(f"  Loading: {json_filename}")
            transcript_data = load_transcript_json(str(json_path))

            # Calculate duration
            duration = calculate_chapter_duration(transcript_data)
            chapter_duration += duration

            # Collect segments
            if transcript_data.get('segments'):
                all_segments.extend(transcript_data['segments'])

        if chapter_duration == 0:
            print(f"  ⚠️  No valid transcript data found for chapter {chapter_num}")
            continue

        # Add chapter to database
        chapter_start = cumulative_time
        chapter_end = cumulative_time + chapter_duration

        chapter_id = db.add_chapter(
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

    # Print summary
    print("\n" + "="*60)
    print("✓ Basic structure ingestion complete!")
    print(f"  Book ID: {book_id}")
    print(f"  Total duration: {cumulative_time:.1f}s ({cumulative_time/3600:.2f} hours)")
    print("\nNext step: Run with --analyze to extract characters and generate summaries")

    return book_id


def analyze_chapter_with_llm(
    book_id: str,
    chapter_id: str,
    chapter_number: int,
    chapter_title: str,
    transcript_text: str,
    llm_processor: learner_llm.LLMProcessor
):
    """
    Analyze a chapter using LLM to extract:
    - Summary
    - Characters
    - Key events
    - Timeline events
    - Study questions
    """
    print(f"  [LLM Analysis] Processing chapter {chapter_number}...")

    # Extract content using LLM
    extracted = llm_processor.extract_chapter_content(
        chapter_text=transcript_text,
        chapter_number=chapter_number,
        chapter_title=chapter_title
    )

    # Add chapter summary
    if extracted.get('summary'):
        db.add_chapter_summary(
            chapter_id=chapter_id,
            summary_text=extracted['summary'],
            key_events=extracted.get('key_events', []),
            key_concepts=extracted.get('key_concepts', []),
            plot_points=[],  # Could be extracted separately
            study_questions=extracted.get('study_questions', [])
        )
        print(f"    ✓ Added summary")

    # Add characters
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

            # Add character event for this chapter
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

    # Add timeline events
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

    print(f"    ✓ Analysis complete!")


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(description="Ingest IceScriber transcripts into learning database")
    parser.add_argument('--mapping', default='chapter_mapping.json', help='Path to chapter mapping file')
    parser.add_argument('--audio-folder', default='audio_chapters', help='Folder containing transcript JSONs')
    parser.add_argument('--analyze', action='store_true', help='Run LLM analysis (requires API key)')
    parser.add_argument('--chapter', type=int, help='Process only this chapter number')
    parser.add_argument('--reset', action='store_true', help='Delete existing database and start fresh')

    args = parser.parse_args()

    # Reset database if requested
    if args.reset:
        db_path = Path(db.DB_PATH)
        if db_path.exists():
            print(f"Removing existing database: {db_path}")
            db_path.unlink()
        db.initialize_database()

    # Make sure database exists
    if not Path(db.DB_PATH).exists():
        db.initialize_database()

    # Ingest basic structure
    book_id = ingest_basic_structure(args.mapping, args.audio_folder)

    # LLM analysis (if requested)
    if args.analyze:
        print("\n=== LLM Analysis Phase ===")

        # Initialize LLM
        try:
            llm_processor = learner_llm.LLMProcessor(provider="gemini")
        except Exception as e:
            print(f"❌ Error initializing LLM: {e}")
            print("Skipping analysis. Make sure GEMINI_API_KEY is set in .env file")
            return

        # Load chapter mapping
        mapping = load_chapter_mapping(args.mapping)

        # Get chapters from database
        chapters = db.get_chapters(book_id)

        for chapter in chapters:
            chapter_num = chapter['chapter_number']
            chapter_title = chapter['title']
            chapter_id = chapter['chapter_id']

            # Skip if specific chapter requested and this isn't it
            if args.chapter is not None and chapter_num != args.chapter:
                continue

            print(f"\n--- Analyzing Chapter {chapter_num}: {chapter_title} ---")

            # Load transcript text
            audio_files = json.loads(chapter['audio_file_paths']) if isinstance(chapter['audio_file_paths'], str) else chapter['audio_file_paths']
            chapter_text = ""

            for json_filename in audio_files:
                json_path = Path(args.audio_folder) / json_filename
                if json_path.exists():
                    transcript_data = load_transcript_json(str(json_path))
                    chapter_text += get_chapter_text(transcript_data) + " "

            if not chapter_text.strip():
                print(f"  ⚠️  No transcript text found, skipping")
                continue

            # Analyze with LLM
            try:
                analyze_chapter_with_llm(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    chapter_number=chapter_num,
                    chapter_title=chapter_title,
                    transcript_text=chapter_text[:20000],  # Limit to first 20k chars
                    llm_processor=llm_processor
                )

                # Rate limit pause
                llm_processor.rate_limit_pause()

            except Exception as e:
                print(f"  ❌ Error analyzing chapter: {e}")

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
