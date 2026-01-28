#!/usr/bin/env python3
"""
Compare v1 vs v2 transcription performance and quality.
Analyzes existing v1 output and new v2 output for the same file.

Usage: python compare_v1_v2.py <audio_file.mp3>
"""

import json
import sys
import os
from pathlib import Path

def analyze_json(json_path):
    """Extract metrics from JSON transcript."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data['metadata']
    segments = data['segments']

    # Count total words
    total_words = sum(len(seg['text'].split()) for seg in segments)

    # Check for repetitions (simple heuristic)
    all_text = ' '.join(seg['text'] for seg in segments)
    words = all_text.split()
    repetitions = 0
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            repetitions += 1

    return {
        'segments': len(segments),
        'total_words': total_words,
        'repetitions': repetitions,
        'model': metadata.get('model', 'unknown'),
        'version': metadata.get('version', 'v1'),
        'optimizations': metadata.get('optimizations', [])
    }

def load_transcript_text(txt_path):
    """Load transcript text file."""
    if not os.path.exists(txt_path):
        return None
    with open(txt_path, 'r', encoding='utf-8') as f:
        return f.read()

def compare_texts(v1_text, v2_text):
    """Compare transcript texts."""
    if not v1_text or not v2_text:
        return None

    # Simple metrics
    v1_lines = [l.strip() for l in v1_text.split('\n') if l.strip()]
    v2_lines = [l.strip() for l in v2_text.split('\n') if l.strip()]

    return {
        'v1_lines': len(v1_lines),
        'v2_lines': len(v2_lines),
        'v1_chars': len(v1_text),
        'v2_chars': len(v2_text)
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_v1_v2.py <audio_file.mp3>")
        sys.exit(1)

    audio_file = sys.argv[1]
    base_path = Path("audio_chapters") / audio_file

    v1_json = base_path.with_suffix('.mp3.json')
    v2_json = Path(str(base_path) + '.v2.json')

    v1_txt = Path(str(base_path) + '_TRANSCRIPT.txt')
    v2_txt = Path(str(base_path) + '_TRANSCRIPT.v2.txt')

    print("=" * 70)
    print("TRANSCRIPTION COMPARISON: v1 vs v2")
    print("=" * 70)
    print(f"\nFile: {audio_file}")
    print()

    # Check if files exist
    if not v1_json.exists():
        print(f"❌ v1 JSON not found: {v1_json}")
        return

    if not v2_json.exists():
        print(f"❌ v2 JSON not found: {v2_json}")
        print(f"   Run: python chapterbatch_v2.py")
        return

    # Analyze JSONs
    print("📊 JSON Analysis:")
    print("-" * 70)

    v1_metrics = analyze_json(v1_json)
    v2_metrics = analyze_json(v2_json)

    print(f"\nv1 (original):")
    print(f"  Version: {v1_metrics['version']}")
    print(f"  Segments: {v1_metrics['segments']}")
    print(f"  Total words: {v1_metrics['total_words']}")
    print(f"  Repetitions (3-word): {v1_metrics['repetitions']}")

    print(f"\nv2 (optimized):")
    print(f"  Version: {v2_metrics['version']}")
    print(f"  Segments: {v2_metrics['segments']}")
    print(f"  Total words: {v2_metrics['total_words']}")
    print(f"  Repetitions (3-word): {v2_metrics['repetitions']}")
    print(f"  Optimizations:")
    for opt in v2_metrics['optimizations']:
        print(f"    - {opt}")

    # Compare
    print(f"\n📈 Comparison:")
    print("-" * 70)

    seg_diff = v2_metrics['segments'] - v1_metrics['segments']
    word_diff = v2_metrics['total_words'] - v1_metrics['total_words']
    rep_diff = v2_metrics['repetitions'] - v1_metrics['repetitions']

    print(f"  Segments: {seg_diff:+d} ({v2_metrics['segments']} vs {v1_metrics['segments']})")
    print(f"  Words: {word_diff:+d} ({v2_metrics['total_words']} vs {v1_metrics['total_words']})")
    print(f"  Repetitions: {rep_diff:+d} ({v2_metrics['repetitions']} vs {v1_metrics['repetitions']})")

    if rep_diff < 0:
        print(f"  ✅ v2 has FEWER repetitions (better)")
    elif rep_diff > 0:
        print(f"  ⚠️  v2 has MORE repetitions")
    else:
        print(f"  ✅ Both have same repetition count")

    # Text comparison
    v1_text = load_transcript_text(v1_txt)
    v2_text = load_transcript_text(v2_txt)

    if v1_text and v2_text:
        print(f"\n📝 Text Comparison:")
        print("-" * 70)

        text_metrics = compare_texts(v1_text, v2_text)
        print(f"  v1 lines: {text_metrics['v1_lines']}")
        print(f"  v2 lines: {text_metrics['v2_lines']}")
        print(f"  v1 chars: {text_metrics['v1_chars']}")
        print(f"  v2 chars: {text_metrics['v2_chars']}")

        # Sample comparison (first 200 chars)
        print(f"\n📖 Sample (first 200 characters):")
        print("-" * 70)
        print("v1:")
        print(v1_text[:200])
        print("\nv2:")
        print(v2_text[:200])

    print("\n" + "=" * 70)
    print("✅ Comparison complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
