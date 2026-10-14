#!/usr/bin/env python3
"""
IceScriber Meeting Mode.

Turn an Icelandic voice memo into a dated folder of meeting notes + an action
plan, in both Icelandic and English.

Usage:
    python scripts/meeting/meeting_notes.py path/to/memo.m4a
    python scripts/meeting/meeting_notes.py        # scans data/input/meetings/

Pipeline: transcribe (reused engine) -> analyze (Gemini, IS) -> translate (EN)
-> render Markdown. Output goes to data/output/meetings/<date>_<slug>/.
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from paths import INPUT_MEETINGS, OUTPUT_MEETINGS  # noqa: E402

AUDIO_EXTS = (".m4a", ".mp3", ".wav")


def _slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem or "meeting"


def resolve_audio(arg: str | None) -> Path:
    """Resolve the audio file from an arg, or scan the meetings input folder."""
    if arg:
        p = Path(arg).expanduser()
        if not p.exists():
            sys.exit(f"❌ Audio file not found: {p}")
        return p

    candidates = sorted(
        f for f in INPUT_MEETINGS.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    ) if INPUT_MEETINGS.exists() else []

    if not candidates:
        sys.exit(
            f"❌ No audio found.\n"
            f"   Pass a file: python scripts/meeting/meeting_notes.py path/to/memo.m4a\n"
            f"   Or drop a .m4a/.mp3/.wav into: {INPUT_MEETINGS}"
        )
    if len(candidates) > 1:
        print(f"ℹ️  {len(candidates)} files in {INPUT_MEETINGS.name}/, using the first: {candidates[0].name}")
    return candidates[0]


def output_dir_for(audio: Path) -> Path:
    ts = datetime.fromtimestamp(audio.stat().st_mtime).strftime("%Y-%m-%d_%H%M")
    return OUTPUT_MEETINGS / f"{ts}_{_slugify(audio.name)}"


def notify(message: str):
    """Best-effort macOS desktop notification (useful for the 'run when away' flow)."""
    print("\a", end="", flush=True)  # terminal bell
    if sys.platform != "darwin":
        return
    try:
        import subprocess
        safe = message.replace('"', "'")
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe}" with title "IceScriber" subtitle "Meeting notes ready" sound name "Glass"'],
            check=False, capture_output=True,
        )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="IceScriber Meeting Mode")
    parser.add_argument("audio", nargs="?", help="Path to the voice memo (.m4a/.mp3/.wav)")
    args = parser.parse_args()

    audio = resolve_audio(args.audio)
    out_dir = output_dir_for(audio)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("IceScriber Meeting Mode")
    print("=" * 70)
    print(f"🎙️  Audio : {audio}")
    print(f"📂 Output: {out_dir}")
    print()

    # 1. Transcribe (reused engine — full fix-and-chunk pipeline)
    print("→ Step 1/4: Transcribing (Icelandic Whisper)...")
    from transcribe_core import transcribe
    result = transcribe(str(audio), language="icelandic")

    # Write transcript files
    (out_dir / "transcript.json").write_text(
        json.dumps(result["json"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "transcript.txt").write_text(result["text_timestamped"], encoding="utf-8")

    llm_text = result["text_llm"].strip()
    if len(llm_text) < 15:
        print("⚠️  Transcript is empty / near-empty — no usable speech detected.")
        print(f"   Transcript files written to {out_dir}. Skipping analysis.")
        return

    # 2. Analyze (Gemini, Icelandic)
    print("→ Step 2/4: Analyzing meeting (Gemini)...")
    from meeting_llm import MeetingAnalyzer
    analyzer = MeetingAnalyzer()
    analysis_is = analyzer.analyze(llm_text)

    # 3. Translate (Gemini, English)
    print("→ Step 3/4: Translating notes to English (Gemini)...")
    analysis_en = analyzer.translate(analysis_is)

    (out_dir / "analysis.json").write_text(
        json.dumps({"is": analysis_is, "en": analysis_en}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 4. Render Markdown (both languages)
    print("→ Step 4/4: Rendering notes...")
    from meeting_render import render
    (out_dir / "notes-is.md").write_text(
        render(analysis_is, "is", source_file=audio.name), encoding="utf-8"
    )
    (out_dir / "notes-en.md").write_text(
        render(analysis_en, "en", source_file=audio.name), encoding="utf-8"
    )

    n_actions = len(analysis_is.get("action_items", []))
    n_decisions = len(analysis_is.get("decisions", []))
    print()
    print("✅ Done!")
    print(f"   {n_decisions} decision(s), {n_actions} action item(s)")
    print(f"   📂 {out_dir}")
    print(f"      ├── transcript.json / transcript.txt")
    print(f"      ├── analysis.json")
    print(f"      ├── notes-is.md")
    print(f"      └── notes-en.md")
    notify(f"{n_decisions} decisions, {n_actions} action items")


if __name__ == "__main__":
    main()
