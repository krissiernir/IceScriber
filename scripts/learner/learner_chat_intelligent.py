"""
Intelligent Q&A for AudiobookLearner using Gemini
Answers questions by retrieving context from database and using LLM

Usage:
    python learner_chat_intelligent.py
"""

import sys
import sqlite3
import json
import os
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

    def __init__(self, db_path: str = str(LEARNER_DB)):
        self.db_path = db_path
        self.book_id = None
        self.book_title = None
        self.book_author = None

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

    def gather_context(self, question: str) -> str:
        """Gather relevant context from database for the question."""
        context_parts = []

        # Get all chapter summaries
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.chapter_number, c.title, cs.summary_text
            FROM chapters c
            LEFT JOIN chapter_summaries cs ON c.chapter_id = cs.chapter_id
            WHERE cs.summary_text IS NOT NULL
            ORDER BY c.chapter_number
        """)

        summaries = cursor.fetchall()
        if summaries:
            context_parts.append("CHAPTER SUMMARIES:")
            for row in summaries:
                context_parts.append(f"Chapter {row['chapter_number']} ({row['title']}): {row['summary_text']}")
            context_parts.append("")

        # Get all characters
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

        # Get timeline events
        cursor.execute("""
            SELECT c.chapter_number, te.event_date, te.location, te.event_description
            FROM timeline_events te
            JOIN chapters c ON te.chapter_id = c.chapter_id
            ORDER BY c.chapter_number
            LIMIT 30
        """)

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
        prompt = f"""You are a helpful assistant answering questions about the Icelandic book "{self.book_title}" by {self.book_author}.

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
    try:
        chat = IntelligentLearnerChat()
        chat.run()
    except ValueError as e:
        print(f"❌ {e}")
    except FileNotFoundError:
        print(f"❌ Database not found at {LEARNER_DB}. Run learner_ingest.py first.")
