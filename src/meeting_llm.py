"""
Meeting analysis via Gemini.

Mirrors src/learner_llm.py (same google.genai client, .env loading, and
markdown-fence / JSON-parse handling) but produces meeting notes + an action
plan instead of audiobook study content.

Two-call design:
  analyze(transcript)  -> structured analysis in Icelandic (1 Gemini call)
  translate(analysis)  -> the SAME structure translated to English (1 call)

Analyzing once and translating (rather than analyzing twice) guarantees the
Icelandic and English notes describe the exact same decisions and action items.
"""

import os
import json

from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
from paths import PROJECT_ROOT
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Keys every analysis dict is expected to have.
ANALYSIS_KEYS = [
    "summary", "attendees", "topics", "decisions",
    "action_items", "open_questions", "next_steps",
]

MODEL = "gemini-2.5-flash"


class MeetingAnalyzer:
    """Turn a meeting transcript into structured notes + an action plan."""

    def __init__(self, provider: str = "gemini", api_key: str = None):
        self.provider = provider
        if provider != "gemini":
            raise ValueError(f"Provider {provider} not yet implemented")

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Add it to .env or run: "
                "export GEMINI_API_KEY='your-key'"
            )
        self.client = genai.Client(api_key=api_key)
        print("✓ Initialized Gemini API (MeetingAnalyzer)")

    # -- public API --------------------------------------------------------

    def analyze(self, transcript_text: str) -> dict:
        """Analyze an Icelandic meeting transcript -> structured dict (Icelandic)."""
        prompt = f"""Þú ert aðstoðarmaður sem breytir hljóðupptöku af fundi í skýra fundargerð og aðgerðaáætlun.

Textinn hér að neðan er sjálfvirkt afrit (transcription) af íslenskum fundi. Hann getur verið ófullkominn, án greinarmerkja á köflum og án þess að tilgreint sé hver talar.

FUNDARTEXTI:
{transcript_text}

Greindu textann og skilaðu AÐEINS JSON hlut með nákvæmlega þessari byggingu:

{{
  "summary": "3-5 setninga samantekt á því um hvað fundurinn snerist",
  "attendees": ["Nöfn þátttakenda sem nefnd eru upphátt (skildu eftir tómt ef engin nöfn koma fram)"],
  "topics": [
    {{"title": "Umræðuefni", "notes": "Stutt lýsing á því sem rætt var um þetta efni"}}
  ],
  "decisions": ["Ákvörðun sem tekin var á fundinum"],
  "action_items": [
    {{
      "task": "Verk sem þarf að vinna",
      "owner": "Sá sem ber ábyrgð (AÐEINS ef nafn er nefnt upphátt, annars tómt)",
      "due": "Tímafrestur (AÐEINS ef nefndur, annars tómt)",
      "priority": "high | medium | low"
    }}
  ],
  "open_questions": ["Óleyst spurning eða atriði"],
  "next_steps": ["Næstu skref eða eftirfylgni"]
}}

Reglur:
- Skrifaðu allt á ÍSLENSKU.
- Giskaðu ALDREI á ábyrgðaraðila (owner) eða tímafrest (due). Skildu eftir tómt ef það kemur ekki skýrt fram.
- Ef eitthvað svið á ekki við, skilaðu tómum lista [].
- Skilaðu AÐEINS JSON, engum öðrum texta."""
        return self._generate_json(prompt, fallback=self._empty_analysis())

    def translate(self, analysis: dict) -> dict:
        """Translate a structured analysis dict from Icelandic to English, same shape."""
        prompt = f"""Translate the following Icelandic meeting-analysis JSON into English.

Rules:
- Keep the EXACT same JSON structure and keys.
- Translate every human-readable string value into natural English.
- Do NOT translate the "priority" values (keep high/medium/low).
- Keep empty fields empty. Do not invent content.
- Return ONLY the JSON, no other text.

INPUT JSON:
{json.dumps(analysis, ensure_ascii=False, indent=2)}"""
        return self._generate_json(prompt, fallback=analysis)

    # -- internals ---------------------------------------------------------

    def _generate_json(self, prompt: str, fallback: dict) -> dict:
        """Call Gemini, strip markdown fences, parse JSON. Return fallback on error."""
        try:
            response = self.client.models.generate_content(model=MODEL, contents=prompt)
            result_text = (response.text or "").strip()

            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            data = json.loads(result_text)
            # Ensure all expected keys exist
            for key in ANALYSIS_KEYS:
                data.setdefault(key, [] if key != "summary" else "")
            return data

        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON parse error: {e}")
            return fallback
        except Exception as e:
            print(f"  ⚠️  LLM error: {e}")
            return fallback

    def _empty_analysis(self) -> dict:
        return {
            "summary": "",
            "attendees": [],
            "topics": [],
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "next_steps": [],
        }


def _test():
    """Smoke test with a short Icelandic sample."""
    analyzer = MeetingAnalyzer()
    sample = (
        "Góðan daginn öll. Við þurfum að klára vefsíðuna fyrir mánaðamót. "
        "Anna tekur að sér að skrifa textann og Jón sér um myndirnar fyrir föstudag. "
        "Við ákváðum að fresta kynningunni um viku. Það er enn óljóst hvað herferðin má kosta."
    )
    result = analyzer.analyze(sample)
    print("\n--- Icelandic analysis ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n--- English translation ---")
    print(json.dumps(analyzer.translate(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    _test()
