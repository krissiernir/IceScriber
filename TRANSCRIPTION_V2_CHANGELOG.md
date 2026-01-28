# Transcription Engine v2 - Optimization Changelog

## Version 2 Improvements

Based on Hugging Face documentation for `whisper-large-icelandic` and Apple Silicon optimization research, version 2 includes two key optimizations:

### 🚀 Optimization 1: SDPA Attention Implementation

**What Changed:**
```python
# v1 (old)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True
).to(device)

# v2 (new)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True,
    attn_implementation="sdpa"  # ← NEW
).to(device)
```

**Why:**
- SDPA = Scaled Dot Product Attention
- Optimized for Apple Neural Engine in PyTorch 2.1+
- Uses hardware-accelerated matrix operations on Apple Silicon

**Expected Benefit:**
- ~20% speed improvement on M-series chips
- No quality loss (same mathematical operation, just faster)

**Source:**
- technical_notes.md line 19-20
- PyTorch 2.1+ documentation on SDPA for MPS backend

---

### 🛡️ Optimization 2: Anti-Hallucination Parameters

**What Changed:**
```python
# v1 (old)
predicted_ids = model.generate(
    input_features,
    language="icelandic",
    task="transcribe"
)

# v2 (new)
predicted_ids = model.generate(
    input_features,
    language="icelandic",
    task="transcribe",
    condition_on_previous_text=False,  # ← NEW
    repetition_penalty=1.1,            # ← NEW
    no_repeat_ngram_size=3             # ← NEW
)
```

**Why:**
- Fine-tuned Whisper models are prone to "repetition loops" during silence or music
- `repetition_penalty=1.1`: Lightly penalizes repeating the same n-grams (1.1 = 10% penalty)
- `no_repeat_ngram_size=3`: Hard blocks 3-word repetition loops

**Note:** `condition_on_previous_text` was mentioned in technical_notes.md but is not supported in current transformers version. Removed from implementation.

**Expected Benefit:**
- Fewer hallucinations during silent sections
- No "stuck in a loop" repetitions
- Cleaner transcripts with better quality

**Source:**
- technical_notes.md lines 23-27
- Hugging Face transformers documentation on generation parameters

---

## Testing Protocol

### How to Test

1. **Choose a test file:**
   - Pick 1-2 audio files that have:
     - Some silence or music sections (tests anti-hallucination)
     - Challenging Icelandic pronunciation
     - ~5-10 minutes duration (for reasonable test time)

2. **Rename existing transcripts (backup):**
   ```bash
   # Backup v1 outputs if you want to keep them
   cd audio_chapters
   mkdir -p v1_backup
   cp *_TRANSCRIPT.txt v1_backup/
   cp *.json v1_backup/
   ```

3. **Run v2 on same files:**
   ```bash
   # Delete the .json file for files you want to re-transcribe
   rm audio_chapters/YOUR_TEST_FILE.mp3.json

   # Run v2
   python chapterbatch_v2.py
   ```

4. **Compare outputs:**
   - v2 creates files with `.v2.json`, `.v2.txt`, `.v2.md` suffixes
   - Compare side-by-side:
     ```bash
     # Check for repetition loops (should be fewer in v2)
     grep -o -E '(\w+\s+){3}\1' audio_chapters/FILE_TRANSCRIPT.txt | head
     grep -o -E '(\w+\s+){3}\1' audio_chapters/FILE_TRANSCRIPT.v2.txt | head
     ```

### Metrics to Track

| Metric | v1 | v2 | Notes |
|--------|----|----|-------|
| Processing time (per chapter) | __ min | __ min | Should be ~20% faster |
| Repetition loops detected | __ | __ | Count obvious repetitions |
| Quality (subjective 1-10) | __ | __ | Read both, which is better? |
| Hallucinations in silence | __ | __ | Check silent sections |

### Expected Results

**Speed:**
- v2 should be 15-25% faster on Apple Silicon
- Example: If v1 takes 10 minutes → v2 should take ~8 minutes

**Quality:**
- v2 should have fewer repetition artifacts
- Silence/music sections should be cleaner
- Overall transcription quality should be same or better

**No Regression:**
- Icelandic character accuracy should remain excellent (þ, ð, æ, ö)
- Timestamp accuracy should be identical
- JSON structure should be valid

---

## Files Changed

- **New:** `chapterbatch_v2.py` - Optimized version
- **Unchanged:** `chapterbatch.py` - Original version (kept for comparison)

**Output Naming:**
- v1: `FILE.json`, `FILE_TRANSCRIPT.txt`, `FILE_MARKDOWN.md`, `FILE_LLM.txt`
- v2: `FILE.v2.json`, `FILE_TRANSCRIPT.v2.txt`, `FILE_MARKDOWN.v2.md`, `FILE_LLM.v2.txt`

This allows side-by-side comparison without overwriting existing transcripts.

---

## When to Use v2

**Use v2 for:**
- All new transcriptions
- Re-transcribing files with quality issues
- Production use after testing validates improvements

**Keep v1 around for:**
- Baseline comparison
- Fallback if v2 has unexpected issues
- Reference implementation

---

## Future Optimizations (Not Implemented Yet)

These are documented in `technical_notes.md` but require more significant refactoring:

1. **Hugging Face Pipeline with Gaussian Kernel Blending**
   - Pro: Better overlap handling than manual chunking
   - Con: Harder to get precise timestamps for JSON output

2. **File Path Streaming Instead of Numpy Arrays**
   - Pro: Lower memory usage
   - Con: Requires refactoring chunking logic

3. **English Fast-Track with Distil-Whisper or Faster-Whisper**
   - Pro: 4-6x faster for English content
   - Con: Not applicable to Icelandic audiobooks

---

## Rollout Plan

1. ✅ Create v2 with SDPA + anti-hallucination (this file)
2. ⏳ Test on 2-3 sample chapters
3. ⏳ Compare speed and quality metrics
4. ⏳ If successful → use v2 as default
5. ⏳ Update documentation and roadmap

---

**Created:** January 28, 2026
**Status:** Ready for testing
**Next Step:** Run comparative test on sample chapters
