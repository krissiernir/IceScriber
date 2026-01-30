"""
Simple Q&A Test for AudiobookLearner
Tests the database with simple questions on analyzed chapters

Usage:
    python test_qa.py
"""

import sys
import sqlite3
import json
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from paths import LEARNER_DB


def get_connection(db_path: str = str(LEARNER_DB)) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_book_id() -> str:
    """Get the first book ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT book_id FROM books LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row['book_id'] if row else None


def search_characters(query: str) -> List[Dict]:
    """Search for characters by name."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, occupation, age, traits, first_appearance_chapter, description
        FROM characters
        WHERE name LIKE ?
        ORDER BY first_appearance_chapter
    """, (f"%{query}%",))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        char = dict(row)
        if char.get('traits'):
            char['traits'] = json.loads(char['traits'])
        results.append(char)

    return results


def get_chapter_summary(chapter_number: int) -> Dict:
    """Get summary for a specific chapter."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.chapter_number, c.title, cs.summary_text, cs.key_events, cs.key_concepts, cs.study_questions
        FROM chapters c
        LEFT JOIN chapter_summaries cs ON c.chapter_id = cs.chapter_id
        WHERE c.chapter_number = ?
    """, (chapter_number,))

    row = cursor.fetchone()
    conn.close()

    if row:
        result = dict(row)
        for field in ['key_events', 'key_concepts', 'study_questions']:
            if result.get(field):
                result[field] = json.loads(result[field])
        return result
    return None


def get_all_characters() -> List[Dict]:
    """Get all characters."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, occupation, age, first_appearance_chapter
        FROM characters
        ORDER BY first_appearance_chapter, name
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_character_events(character_name: str) -> List[Dict]:
    """Get events for a character."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.chapter_number, c.title, ce.event_description, ce.event_type
        FROM character_events ce
        JOIN characters ch ON ce.character_id = ch.character_id
        JOIN chapters c ON ce.chapter_id = c.chapter_id
        WHERE ch.name LIKE ?
        ORDER BY c.chapter_number
    """, (f"%{character_name}%",))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_timeline_events() -> List[Dict]:
    """Get all timeline events."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.chapter_number, c.title, te.event_date, te.event_time, te.location, te.event_description
        FROM timeline_events te
        JOIN chapters c ON te.chapter_id = c.chapter_id
        ORDER BY c.chapter_number
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


def test_qa():
    """Run Q&A tests."""
    print("\n🧪 AudiobookLearner Q&A Test")
    print("Testing on Chapters 1, 5, 6")

    # Test 1: List all characters
    print_section("Q1: Who are the characters in the book?")
    characters = get_all_characters()
    if characters:
        for char in characters:
            age_str = f", {char['age']} years old" if char.get('age') else ""
            occ_str = f" ({char['occupation']})" if char.get('occupation') else ""
            print(f"  • {char['name']}{occ_str}{age_str} - First appears: Chapter {char['first_appearance_chapter']}")
    else:
        print("  No characters found.")

    # Test 2: What happened in Chapter 5?
    print_section("Q2: What happened in Chapter 5?")
    chapter_5 = get_chapter_summary(5)
    if chapter_5:
        print(f"Chapter {chapter_5['chapter_number']}: {chapter_5['title']}")
        print(f"\nSummary:")
        print(f"  {chapter_5['summary_text']}")

        if chapter_5.get('key_events'):
            print(f"\nKey Events:")
            for event in chapter_5['key_events']:
                print(f"  • {event}")

        if chapter_5.get('key_concepts'):
            print(f"\nKey Concepts:")
            for concept in chapter_5['key_concepts']:
                print(f"  • {concept}")
    else:
        print("  Chapter 5 not analyzed yet.")

    # Test 3: Who is the narrator?
    print_section("Q3: Who is the narrator?")
    narrators = search_characters("narrator")
    if narrators:
        for narrator in narrators:
            print(f"Name: {narrator['name']}")
            if narrator.get('occupation'):
                print(f"Occupation: {narrator['occupation']}")
            if narrator.get('age'):
                print(f"Age: {narrator['age']}")
            if narrator.get('traits'):
                print(f"Traits: {', '.join(narrator['traits'])}")
            if narrator.get('description'):
                print(f"Description: {narrator['description']}")
            print(f"First appears: Chapter {narrator['first_appearance_chapter']}")
            print()
    else:
        print("  Narrator not found.")

    # Test 4: What does the narrator do in each chapter?
    print_section("Q4: What does the narrator do in each chapter?")
    narrator_events = get_character_events("narrator")
    if narrator_events:
        for event in narrator_events:
            print(f"Chapter {event['chapter_number']}: {event['title']}")
            print(f"  {event['event_description']}")
            print()
    else:
        print("  No events found for narrator.")

    # Test 5: Timeline
    print_section("Q5: What dates/locations are mentioned?")
    timeline = get_timeline_events()
    if timeline:
        for event in timeline:
            date_str = event.get('event_date', 'Unknown date')
            time_str = f" at {event['event_time']}" if event.get('event_time') else ""
            loc_str = f" in {event['location']}" if event.get('location') else ""
            print(f"Chapter {event['chapter_number']}: {date_str}{time_str}{loc_str}")
            print(f"  {event['event_description']}")
            print()
    else:
        print("  No timeline events found.")

    # Test 6: What are the study questions for Chapter 6?
    print_section("Q6: Study questions for Chapter 6")
    chapter_6 = get_chapter_summary(6)
    if chapter_6 and chapter_6.get('study_questions'):
        for i, question in enumerate(chapter_6['study_questions'], 1):
            print(f"{i}. {question}")
    else:
        print("  No study questions found for Chapter 6.")

    print_section("Test Complete!")
    print("Data quality assessment:")
    print(f"  • Total characters: {len(characters)}")
    print(f"  • Chapters with summaries: 3 (Chapters 1, 5, 6)")
    print(f"  • Timeline events: {len(timeline)}")
    print("\nNext steps:")
    print("  1. If data quality is good → Run full analysis (25 chapters)")
    print("  2. If data needs improvement → Adjust prompts and re-test")
    print()


if __name__ == "__main__":
    test_qa()
