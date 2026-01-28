"""
AudiobookLearner LLM Integration
Handles all LLM interactions for content extraction

Supports:
- Google Gemini API
- Claude API (future)
- OpenAI API (future)
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded configuration from .env file")


class LLMProcessor:
    """Handle LLM API calls for content extraction."""

    def __init__(self, provider: str = "gemini", api_key: str = None):
        """
        Initialize LLM processor.

        Args:
            provider: "gemini", "claude", or "openai"
            api_key: API key (or use environment variable)
        """
        self.provider = provider

        if provider == "gemini":
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set. Set it with: export GEMINI_API_KEY='your-key'")

            self.client = genai.Client(api_key=api_key)
            print(f"✓ Initialized Gemini API")

        else:
            raise ValueError(f"Provider {provider} not yet implemented")

    def extract_chapter_content(self, chapter_text: str, chapter_number: int, chapter_title: str) -> Dict[str, Any]:
        """
        Extract all learning content from a chapter.

        Returns dict with:
        - summary: Brief summary (3-5 sentences)
        - characters: List of characters with details
        - key_events: Important events in this chapter
        - timeline_events: Dates, times, locations mentioned
        - key_concepts: Important ideas
        - study_questions: Potential test questions
        """
        prompt = f"""You are analyzing an Icelandic mystery/crime novel chapter for a student learning assistant.

**Chapter {chapter_number}: {chapter_title}**

Analyze the following chapter text and extract key information for study purposes.

CHAPTER TEXT:
{chapter_text[:15000]}

Please provide a JSON response with the following structure:

{{
  "summary": "3-5 sentence summary of what happens in this chapter",
  "characters": [
    {{
      "name": "Character name",
      "aliases": ["Nickname1", "Nickname2"],
      "age": 35,
      "occupation": "Job or role",
      "traits": ["trait1", "trait2"],
      "actions": "What this character does in this chapter"
    }}
  ],
  "key_events": [
    "Important event 1",
    "Important event 2"
  ],
  "timeline_events": [
    {{
      "date": "Date if mentioned (YYYY-MM-DD or descriptive)",
      "time": "Time if mentioned (HH:MM or descriptive)",
      "location": "Where this happened",
      "event": "What happened"
    }}
  ],
  "key_concepts": [
    "Important concept or theme 1",
    "Important concept or theme 2"
  ],
  "study_questions": [
    "Question 1 for testing understanding?",
    "Question 2 for testing understanding?"
  ]
}}

Guidelines:
- Extract actual character names from the text (Icelandic names)
- Include age/occupation ONLY if explicitly mentioned
- Focus on facts that would appear on a test
- Timeline events: include any dates, times, or locations mentioned
- Study questions should test comprehension of key plot points

Return ONLY the JSON, no other text.
"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            result_text = response.text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result_text = result_text.strip()

            # Parse JSON
            extracted = json.loads(result_text)

            print(f"  ✓ Extracted: {len(extracted.get('characters', []))} characters, "
                  f"{len(extracted.get('key_events', []))} events")

            return extracted

        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON parse error: {e}")
            print(f"  Raw response: {result_text[:200]}...")
            return self._empty_extraction()

        except Exception as e:
            print(f"  ⚠️  LLM error: {e}")
            return self._empty_extraction()

    def _empty_extraction(self) -> Dict[str, Any]:
        """Return empty extraction structure."""
        return {
            "summary": "",
            "characters": [],
            "key_events": [],
            "timeline_events": [],
            "key_concepts": [],
            "study_questions": []
        }

    def rate_limit_pause(self):
        """Pause to respect API rate limits."""
        time.sleep(1)  # Gemini free tier: 15 requests per minute


def test_llm():
    """Test LLM integration with sample text."""
    print("Testing LLM integration...\n")

    processor = LLMProcessor(provider="gemini")

    sample_text = """
    Einar var blaðamaður á síðdegisblaðinu. Hann var sendur til Akureyrar
    til að fjalla um drauga í gömlu húsi. Það var sumarhátíð í bænum og
    þúsundir manna komu í heimsókn. Einar var 42 ára og hafði starfað
    sem blaðamaður í tíu ár.
    """

    result = processor.extract_chapter_content(
        chapter_text=sample_text,
        chapter_number=1,
        chapter_title="Test Chapter"
    )

    print("\nExtracted content:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n✓ Test complete!")


if __name__ == "__main__":
    test_llm()
