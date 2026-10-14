# IceScriber Meeting Mode — Design Spec

**Date:** 2026-07-16
**Status:** Approved design, pending implementation plan

## Goal

Add a reusable "meeting mode" to IceScriber: one command turns an Icelandic
voice memo into a dated folder of meeting notes and an action plan, produced in
**both Icelandic and English**. The transcription and text-cleanup engine is the
existing IceScriber pipeline, reused unchanged; only the analysis stage is new.

## User-facing behavior

```bash
python scripts/meeting/meeting_notes.py path/to/memo.m4a
# or: drop memo into data/input/meetings/ and run with no args
python scripts/meeting/meeting_notes.py
```

The command runs end-to-end (transcribe → clean → analyze → translate → render)
and writes a dated output folder:

```
data/output/meetings/2026-07-16_1430_<slug>/
├── transcript.json      raw Whisper output (segments + metadata), source of truth
├── transcript.txt       cleaned, punctuated, timestamped transcript
├── analysis.json        structured meeting analysis (machine-readable, both langs)
├── notes-is.md          meeting notes + action plan, Icelandic
└── notes-en.md          meeting notes + action plan, English
```

`<slug>` and the date/time prefix derive from the audio filename and its
modification time. Supported input formats: `.m4a` (iPhone Voice Memos), `.mp3`,
`.wav` — same as the existing engine.

## Notes content (per language)

Each `notes-*.md` and the `analysis.json` contain:

- **Yfirlit / Summary** — 3–5 sentences on what the meeting covered
- **Þátttakendur / Attendees** — best-effort list (only names said aloud)
- **Umræðuefni / Topics** — agenda/topic breakdown with per-topic notes
- **Ákvarðanir / Decisions** — concrete decisions made
- **Aðgerðir / Action items** — the action plan: `task · owner · due · priority`
- **Opnar spurningar / Open questions** — unresolved items
- **Næstu skref / Next steps** — follow-ups, next meeting

`owner` and `due` are filled **only** when explicitly stated in the meeting;
otherwise left blank. No guessing. (There is no speaker diarization, so owners
are only known when someone is addressed by name aloud.)

## Architecture

```
your .m4a/.mp3/.wav
    │
    ▼  scripts/meeting/meeting_notes.py  (orchestrator)
┌──────────────────────────────────────────────┐
│ 1. transcribe_core.transcribe(audio)          │  ← reused engine (see below)
│      → JSON source-of-truth + cleaned text     │
│ 2. MeetingAnalyzer.analyze(text)  [Gemini]     │  → analysis dict (Icelandic)
│ 3. MeetingAnalyzer.translate(analysis) [Gemini]│  → same dict, English
│ 4. meeting_render.render(analysis, lang)       │  → notes-is.md / notes-en.md
└──────────────────────────────────────────────┘
    ▼
data/output/meetings/<dated-folder>/
```

### Component 1 — `src/transcribe_core.py` (refactor, extracted from existing engine)

The full "fix and chunk" pipeline currently lives inside
`scripts/transcription/chapterbatch_v2.py`. This refactor **extracts all of it**
into a shared, importable module so both the batch script and meeting mode use
the identical engine. The five stages, all moved intact:

1. **Chunking** — sliding window, 30s window / 5s stride (25s overlap).
2. **Anti-hallucination decoding** — `repetition_penalty=1.1`,
   `no_repeat_ngram_size=3` (prevents repeat loops in silence/crosstalk —
   valuable for meeting audio with pauses).
3. **Overlap de-duplication** — `find_overlap_end()`, longest-common-substring
   matching at 85% threshold, stitches overlapping chunks without duplication.
4. **Text fixing** — `format_text_with_punctuation()`: sentence-boundary
   detection, period insertion, capitalization, Icelandic UTF-8 preserved.
5. **Format derivation** — from the JSON source-of-truth: timestamped TXT,
   Markdown, and `format_llm_optimized()` clean-continuous-text.

**Public interface:** `transcribe(audio_path, language="icelandic") -> dict`
returning the JSON transcript structure plus the derived text formats (at least
the LLM-optimized text and the timestamped text).

**Constraint:** `chapterbatch_v2.py` must produce byte-for-byte identical output
after the refactor. It becomes a thin folder-loop that imports from
`transcribe_core`. Verified by a before/after regression run (see Testing).

The model is loaded once. For meeting mode (single file) this is in-process — no
subprocess or file-copy dance.

### Component 2 — `src/meeting_llm.py` (new)

`MeetingAnalyzer`, mirroring the existing `src/learner_llm.py` `LLMProcessor`
and reusing the same `google.genai` client, `.env` loading, markdown-fence
stripping, and JSON-parse error handling (`_empty_extraction`-style fallback).

- `analyze(transcript_text) -> dict` — one Gemini call producing the Icelandic
  structured analysis (schema: summary, attendees, topics, decisions,
  action_items[{task, owner, due, priority}], open_questions, next_steps).
- `translate(analysis) -> dict` — one Gemini call translating the structured
  result to English, preserving structure.

**Feeds Gemini the `format_llm_optimized` cleaned text** (the format built for
LLM ingestion), and sends the **full** transcript — not truncated at 15k chars
like the audiobook path, since Gemini 2.5 Flash has ample context.

**Why analyze-then-translate (2 calls) rather than analyze-twice:** guarantees
the Icelandic and English notes describe the exact same decisions and action
items. Independent analysis in each language could diverge.

### Component 3 — `src/meeting_render.py` (new)

`render(analysis, lang) -> str` — turns one analysis dict into a Markdown
document with the bilingual section headers for the given language. Pure
function, no I/O, easy to unit-test.

### Component 4 — `scripts/meeting/meeting_notes.py` (new, CLI orchestrator)

- Resolves the audio path (arg, or scans `data/input/meetings/`).
- Calls `transcribe_core.transcribe`, then `MeetingAnalyzer.analyze` +
  `.translate`, then `meeting_render.render` for each language.
- Creates the dated output folder and writes all five files.
- Prints a short summary (folder path, #action items, #decisions).

### Paths — `src/paths.py` (small addition)

Add, following the existing pattern:

```python
INPUT_MEETINGS = DATA_DIR / "input" / "meetings"
OUTPUT_MEETINGS = DATA_DIR / "output" / "meetings"
```

and include both in the auto-`mkdir` loop.

## Error handling

- **No audio found** — clear message naming `data/input/meetings/` and exit.
- **Empty/near-empty transcript** — skip the Gemini calls, write the transcript
  files, warn that there was no usable speech.
- **Gemini API error / bad JSON** — reuse the existing pattern: log the error,
  fall back to an empty-structure analysis so the run still produces files
  rather than crashing. Notes render with empty sections and a warning banner.
- **Translation failure** — still write `notes-is.md`; skip `notes-en.md` with a
  warning rather than failing the whole run.

## Testing

- **Unit — analyzer schema:** a `test` entry (à la `learner_llm.test_llm`) runs
  `analyze` on a short Icelandic sample and asserts the expected keys/shape.
- **Unit — renderer:** feed a hand-written analysis dict to
  `meeting_render.render` for both languages, assert sections/headers present.
- **Regression — engine unchanged:** transcribe a sample file with the current
  `chapterbatch_v2.py`, save output; run again after the `transcribe_core`
  extraction; assert identical output.
- **End-to-end:** run `meeting_notes.py` on one real Icelandic memo and eyeball
  `notes-is.md` / `notes-en.md` before declaring done.

## Out of scope (YAGNI)

- **Speaker diarization** — no "who said what"; owners only when named aloud.
- **Meetings database** — files only, no SQLite meetings table. Both can be
  added later; the `analysis.json` per meeting keeps that door open.
- **Engine changes for meetings** — the existing cleanup is general-purpose
  audio handling and needs no meeting-specific tuning.

## Dependencies

No new dependencies. Reuses `torch`/`transformers`/`librosa` (transcription) and
`google-genai` + `python-dotenv` (analysis), all already in `requirements.txt`.
Requires `GEMINI_API_KEY` in `.env` (same as AudiobookLearner).
