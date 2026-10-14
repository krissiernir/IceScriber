"""
Intelligent Q&A for AudiobookLearner using Gemini
Answers questions by retrieving context from database and using LLM

Usage:
    python learner_chat_intelligent.py
    python learner_chat_intelligent.py --chapters 5,6
    python learner_chat_intelligent.py --book-dir data/books/the-hate-u-give
    python learner_chat_intelligent.py --book-dir data/books/the-hate-u-give --chapters 1,2,3
"""

import sys
import sqlite3
import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from google import genai

# Add src/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from paths import PROJECT_ROOT, LEARNER_DB

# Load environment variables
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)


class IntelligentLearnerChat:
    """Intelligent Q&A using database + Gemini LLM."""

    def __init__(self, db_path: str = str(LEARNER_DB), chapters: Optional[List[int]] = None):
        self.db_path = db_path
        self.book_id = None
        self.book_title = None
        self.book_author = None
        self.chapters = chapters  # Filter to specific chapters

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        self.client = genai.Client(api_key=api_key)
        print("✓ Connected to Gemini API")

        self._load_book_info()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_book_info(self):
        """Load book information."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT book_id, title, author FROM books LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            self.book_id = row['book_id']
            self.book_title = row['title']
            self.book_author = row['author']
            print(f"✓ Loaded: {self.book_title} by {self.book_author}\n")

    def _chapter_filter_sql(self, chapter_col: str = "c.chapter_number") -> tuple:
        """Build SQL WHERE clause and params for chapter filtering."""
        if self.chapters:
            placeholders = ",".join("?" * len(self.chapters))
            return f"AND {chapter_col} IN ({placeholders})", list(self.chapters)
        return "", []

    def gather_context(self, question: str) -> str:
        """Gather relevant context from database for the question."""
        context_parts = []
        chapter_filter, chapter_params = self._chapter_filter_sql()

        conn = self._get_connection()
        cursor = conn.cursor()

        # Get chapter summaries (filtered)
        cursor.execute(f"""
            SELECT c.chapter_number, c.title, cs.summary_text
            FROM chapters c
            LEFT JOIN chapter_summaries cs ON c.chapter_id = cs.chapter_id
            WHERE cs.summary_text IS NOT NULL {chapter_filter}
            ORDER BY c.chapter_number
        """, chapter_params)

        summaries = cursor.fetchall()
        if summaries:
            context_parts.append("CHAPTER SUMMARIES:")
            for row in summaries:
                context_parts.append(f"Chapter {row['chapter_number']} ({row['title']}): {row['summary_text']}")
            context_parts.append("")

        # Get characters (filtered to those appearing in selected chapters)
        if self.chapters:
            placeholders = ",".join("?" * len(self.chapters))
            cursor.execute(f"""
                SELECT DISTINCT ch.name, ch.occupation, ch.age, ch.traits
                FROM characters ch
                WHERE ch.book_id = ?
                AND ch.first_appearance_chapter IN ({placeholders})
                ORDER BY ch.first_appearance_chapter
                LIMIT 50
            """, [self.book_id] + list(self.chapters))
        else:
            cursor.execute("""
                SELECT DISTINCT name, occupation, age, traits
                FROM characters
                WHERE book_id = ?
                ORDER BY first_appearance_chapter
                LIMIT 50
            """, (self.book_id,))

        characters = cursor.fetchall()
        if characters:
            context_parts.append("CHARACTERS:")
            for row in characters:
                char_info = f"- {row['name']}"
                if row['occupation']:
                    char_info += f" ({row['occupation']})"
                if row['age']:
                    char_info += f", {row['age']} years old"
                if row['traits']:
                    try:
                        traits = json.loads(row['traits'])
                        char_info += f" - Traits: {', '.join(traits[:3])}"
                    except:
                        pass
                context_parts.append(char_info)
            context_parts.append("")

        # Get character events (filtered)
        if self.chapters:
            placeholders = ",".join("?" * len(self.chapters))
            cursor.execute(f"""
                SELECT ch.name, ce.event_description
                FROM character_events ce
                JOIN characters ch ON ce.character_id = ch.character_id
                JOIN chapters c ON ce.chapter_id = c.chapter_id
                WHERE c.chapter_number IN ({placeholders})
                ORDER BY c.chapter_number
            """, list(self.chapters))

            char_events = cursor.fetchall()
            if char_events:
                context_parts.append("CHARACTER ACTIONS IN THESE CHAPTERS:")
                for row in char_events:
                    context_parts.append(f"- {row['name']}: {row['event_description']}")
                context_parts.append("")

        # Get timeline events (filtered)
        cursor.execute(f"""
            SELECT c.chapter_number, te.event_date, te.location, te.event_description
            FROM timeline_events te
            JOIN chapters c ON te.chapter_id = c.chapter_id
            WHERE 1=1 {chapter_filter}
            ORDER BY c.chapter_number
            LIMIT 30
        """, chapter_params)

        events = cursor.fetchall()
        if events:
            context_parts.append("TIMELINE EVENTS:")
            for row in events:
                event_info = f"- Ch {row['chapter_number']}"
                if row['event_date']:
                    event_info += f" ({row['event_date']})"
                if row['location']:
                    event_info += f" in {row['location']}"
                event_info += f": {row['event_description']}"
                context_parts.append(event_info)
            context_parts.append("")

        conn.close()

        return "\n".join(context_parts)

    def ask_question(self, question: str) -> str:
        """Ask a question and get an intelligent answer."""
        # Gather context from database
        context = self.gather_context(question)

        # Build prompt for Gemini
        chapter_note = ""
        if self.chapters:
            chapter_note = f"\nNote: The user is focusing on chapters {', '.join(str(c) for c in self.chapters)}. Prioritize information from these chapters.\n"

        prompt = f"""You are a helpful assistant answering questions about the book "{self.book_title}" by {self.book_author}.
{chapter_note}
Use the following information from the book to answer the user's question:

{context}

User Question: {question}

Instructions:
- Answer in a clear, informative way
- Use information from the context provided
- If the answer isn't in the context, say so
- Reference specific chapters when relevant
- Keep answers concise but complete
- Respond in English unless the user asks in Icelandic

Answer:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )

            return response.text.strip()

        except Exception as e:
            return f"Error: {e}"

    def run(self):
        """Run interactive Q&A session."""
        print("="*60)
        print("  📚 Intelligent Q&A with Gemini")
        print("="*60)
        if self.chapters:
            print(f"\n  Focused on chapters: {', '.join(str(c) for c in self.chapters)}")
        print("\nAsk questions about the book in English or Icelandic")
        print("Type 'quit' to exit\n")

        while True:
            try:
                question = input("❓ Question: ").strip()

                if not question:
                    continue

                if question.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break

                print("\n🤔 Thinking...\n")
                answer = self.ask_question(question)
                print(f"💡 Answer:\n{answer}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n⚠️  Error: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Intelligent Q&A for AudiobookLearner")
    parser.add_argument("--chapters", type=str, default=None,
                        help="Comma-separated chapter numbers to focus on (e.g., 5,6)")
    parser.add_argument("--book-dir", type=str, default=None,
                        help="Book directory (e.g., data/books/the-hate-u-give). Uses <dir>/learner.db")
    args = parser.parse_args()

    chapters = None
    if args.chapters:
        chapters = [int(c.strip()) for c in args.chapters.split(",")]

    if args.book_dir:
        db_path = str(Path(args.book_dir) / "learner.db")
    else:
        db_path = str(LEARNER_DB)

    try:
        chat = IntelligentLearnerChat(db_path=db_path, chapters=chapters)
        chat.run()
    except ValueError as e:
        print(f"❌ {e}")
    except FileNotFoundError:
        print(f"❌ Database not found at {db_path}. Run learner_ingest.py first.")
