"""
Simple Interactive Q&A for AudiobookLearner (Test Version)
Query the learning database interactively

Usage:
    python learner_chat_simple.py
"""

import sys
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from paths import LEARNER_DB


class SimpleLearnerChat:
    """Simple Q&A interface for testing."""

    def __init__(self, db_path: str = str(LEARNER_DB)):
        self.db_path = db_path
        self.book_id = self._get_book_id()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_book_id(self) -> Optional[str]:
        """Get the first book ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT book_id, title, author FROM books LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            print(f"\n📚 Book: {row['title']} by {row['author']}")
            return row['book_id']
        return None

    def search_characters(self, query: str) -> List[Dict]:
        """Search for characters by name."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT name, occupation, age, traits, first_appearance_chapter, description
            FROM characters
            WHERE name LIKE ?
            ORDER BY first_appearance_chapter
            LIMIT 5
        """, (f"%{query}%",))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            char = dict(row)
            if char.get('traits'):
                try:
                    char['traits'] = json.loads(char['traits'])
                except:
                    pass
            results.append(char)

        return results

    def get_chapter_by_number(self, chapter_num: int) -> Optional[Dict]:
        """Get chapter info and summary."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.chapter_number, c.title, c.duration_s,
                   cs.summary_text, cs.key_events, cs.key_concepts, cs.study_questions
            FROM chapters c
            LEFT JOIN chapter_summaries cs ON c.chapter_id = cs.chapter_id
            WHERE c.chapter_number = ?
            LIMIT 1
        """, (chapter_num,))

        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            for field in ['key_events', 'key_concepts', 'study_questions']:
                if result.get(field):
                    try:
                        result[field] = json.loads(result[field])
                    except:
                        pass
            return result
        return None

    def list_all_characters(self) -> List[Dict]:
        """List all unique characters."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get unique characters by name
        cursor.execute("""
            SELECT name,
                   MIN(first_appearance_chapter) as first_chapter,
                   GROUP_CONCAT(DISTINCT occupation) as occupations
            FROM characters
            WHERE book_id = ?
            GROUP BY LOWER(name)
            ORDER BY first_chapter, name
        """, (self.book_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_character_actions(self, name: str) -> List[Dict]:
        """Get what a character did across chapters."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT c.chapter_number, c.title, ce.event_description
            FROM character_events ce
            JOIN characters ch ON ce.character_id = ch.character_id
            JOIN chapters c ON ce.chapter_id = c.chapter_id
            WHERE ch.name LIKE ?
            ORDER BY c.chapter_number
        """, (f"%{name}%",))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_in_summaries(self, keyword: str) -> List[Dict]:
        """Search for keyword in chapter summaries."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.chapter_number, c.title, cs.summary_text
            FROM chapter_summaries cs
            JOIN chapters c ON cs.chapter_id = c.chapter_id
            WHERE cs.summary_text LIKE ?
            ORDER BY c.chapter_number
        """, (f"%{keyword}%",))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_timeline_events(self, location: str = None) -> List[Dict]:
        """Get timeline events, optionally filtered by location."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if location:
            cursor.execute("""
                SELECT c.chapter_number, c.title, te.event_date, te.event_time,
                       te.location, te.event_description
                FROM timeline_events te
                JOIN chapters c ON te.chapter_id = c.chapter_id
                WHERE te.location LIKE ?
                ORDER BY c.chapter_number
            """, (f"%{location}%",))
        else:
            cursor.execute("""
                SELECT c.chapter_number, c.title, te.event_date, te.event_time,
                       te.location, te.event_description
                FROM timeline_events te
                JOIN chapters c ON te.chapter_id = c.chapter_id
                ORDER BY c.chapter_number
                LIMIT 20
            """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def handle_question(self, question: str):
        """Process and answer a question."""
        q_lower = question.lower()

        # Detect question type and respond
        if "who" in q_lower and ("character" in q_lower or "people" in q_lower):
            print("\n📋 All Characters:")
            characters = self.list_all_characters()
            for char in characters:
                occ = f" ({char['occupations']})" if char['occupations'] else ""
                print(f"  • {char['name']}{occ} - First appears: Ch {char['first_chapter']}")

        elif "who is" in q_lower or "who's" in q_lower:
            # Extract name
            name = question.split("who is")[-1].split("who's")[-1].strip().strip("?").strip()
            print(f"\n🔍 Searching for: {name}")
            characters = self.search_characters(name)

            if characters:
                for char in characters:
                    print(f"\n{'─'*50}")
                    print(f"Name: {char['name']}")
                    if char.get('occupation'):
                        print(f"Occupation: {char['occupation']}")
                    if char.get('age'):
                        print(f"Age: {char['age']}")
                    if char.get('traits'):
                        print(f"Traits: {', '.join(char['traits'][:5])}")
                    print(f"First appears: Chapter {char['first_appearance_chapter']}")

                    # Get their actions
                    actions = self.get_character_actions(char['name'])
                    if actions:
                        print(f"\nActions across chapters:")
                        for action in actions:
                            print(f"  • Ch {action['chapter_number']}: {action['event_description'][:100]}...")
            else:
                print(f"  ❌ Character '{name}' not found.")

        elif "what happened" in q_lower and "chapter" in q_lower:
            # Extract chapter number
            words = question.split()
            for i, word in enumerate(words):
                if word.lower() == "chapter" and i + 1 < len(words):
                    try:
                        chapter_num = int(words[i + 1].strip("?"))
                        chapter = self.get_chapter_by_number(chapter_num)

                        if chapter:
                            print(f"\n📖 Chapter {chapter['chapter_number']}: {chapter['title']}")
                            print(f"Duration: {chapter['duration_s']/60:.1f} minutes")
                            print(f"\n{chapter.get('summary_text', 'No summary available.')}")

                            if chapter.get('key_events'):
                                print(f"\n🔑 Key Events:")
                                for event in chapter['key_events']:
                                    print(f"  • {event}")
                        else:
                            print(f"  ❌ Chapter {chapter_num} not analyzed yet.")
                        break
                    except ValueError:
                        continue

        elif "where" in q_lower or "location" in q_lower:
            print("\n🗺️  Timeline Events by Location:")
            events = self.get_timeline_events()
            current_location = None
            for event in events:
                if event['location'] != current_location:
                    current_location = event['location']
                    print(f"\n📍 {current_location or 'Unknown location'}:")
                print(f"  • Ch {event['chapter_number']}: {event['event_description'][:80]}...")

        elif "timeline" in q_lower or "when" in q_lower:
            print("\n⏱️  Timeline of Events:")
            events = self.get_timeline_events()
            for event in events:
                date_str = event.get('event_date', 'Unknown date')
                time_str = f" at {event['event_time']}" if event.get('event_time') else ""
                print(f"\n{date_str}{time_str} (Ch {event['chapter_number']})")
                print(f"  📍 {event.get('location', 'Unknown location')}")
                print(f"  {event['event_description']}")

        elif any(word in q_lower for word in ['summary', 'summarize', 'about']):
            # Search in summaries
            print("\n📝 Searching summaries...")
            # Extract key terms (simple approach)
            search_terms = [word for word in question.split() if len(word) > 4 and word.lower() not in ['what', 'about', 'summary', 'summarize']]
            if search_terms:
                results = self.search_in_summaries(search_terms[0])
                if results:
                    for result in results:
                        print(f"\n📖 Chapter {result['chapter_number']}: {result['title']}")
                        print(f"  {result['summary_text'][:200]}...")
                else:
                    print(f"  No chapters found matching '{search_terms[0]}'")

        else:
            print("\n❓ I can answer questions like:")
            print("  • 'Who are the characters?'")
            print("  • 'Who is [character name]?'")
            print("  • 'What happened in chapter 5?'")
            print("  • 'Where did events take place?'")
            print("  • 'Show me the timeline'")
            print("  • 'What is this book about?'")

    def run(self):
        """Run interactive Q&A session."""
        print("\n" + "="*60)
        print("  📚 AudiobookLearner - Interactive Q&A (Test Version)")
        print("="*60)
        print("\nAnalyzed: Chapters 1, 5, 6")
        print("Type 'help' for examples, 'quit' to exit\n")

        while True:
            try:
                question = input("❓ Question: ").strip()

                if not question:
                    continue

                if question.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                if question.lower() in ['help', '?']:
                    print("\n📖 Example Questions:")
                    print("  • Who are the characters?")
                    print("  • Who is the narrator?")
                    print("  • What happened in chapter 5?")
                    print("  • Where did events take place?")
                    print("  • Show me the timeline")
                    print("  • What is the book about?")
                    continue

                self.handle_question(question)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n⚠️  Error: {e}")


if __name__ == "__main__":
    chat = SimpleLearnerChat()
    if chat.book_id:
        chat.run()
    else:
        print("❌ No book found in database. Run learner_ingest.py first.")
