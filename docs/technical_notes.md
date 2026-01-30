📋 Technical Findings & Optimization Report
Project: IceScriber (Icelandic Audiobook Transcription)
Hardware: Apple Silicon (M-Series) / MPS Backend
Library: Hugging Face transformers + pytorch

1. The "Chunking" Bug (Reference PR #20104)
Context: Long-form transcription using pipeline.
The Issue: Early versions of the pipeline simple concatenated 30s chunks. This caused context loss at boundaries, leading to hallucinations or silence.
The Fix (PR #20104): The introduction of stride_length_s.
Implementation:
Chunk: 30.0s (Model native input).
Stride: 5.0s to 6.0s.
Mechanism: The pipeline now uses a Gaussian kernel to weight the center of the logits higher than the edges, stitching the overlapping strides together seamlessly rather than hard-cutting them.
2. Mac Silicon (MPS) Specific Constraints
Precision Bug: Using torch.float16 or torch.bfloat16 on the mps device with the Whisper-Large architecture results in NaN or gibberish outputs (e.g., "!!m!!!!").
Optimization: Must use torch.float32 for stability, despite the memory cost.
Memory Management: The pipeline creates a significant memory overhead when processing raw numpy arrays (KeyError: num_frames bug).
Optimization: Pass file paths (strings) to the pipeline, not raw data. This allows the internal ffmpeg handler to stream data efficiently.
Attention Kernel:
Optimization: Use model_kwargs={"attn_implementation": "sdpa"}. This forces PyTorch to use Scaled Dot Product Attention, which is optimized for Apple Neural Engines in PyTorch 2.1+, offering a ~20% speed boost over Eager attention.
3. Fine-Tuned Model Hallucinations
Context: language-and-voice-lab/whisper-large-icelandic
The Issue: Fine-tuned Whisper models are prone to "repetition loops" during long silences or music.
Optimization:
condition_on_previous_text=False: Prevents the model from getting stuck on a previous error.
repetition_penalty=1.1: lightly penalizes repeating the same n-grams.
no_repeat_ngram_size=3: Hard blocks 3-word loops.
🚀 English "Turbo" Strategy (For Claude)
Tell Claude you want to implement a separate pipeline for English that uses Distillation and Quantization, which are possible for English but harder for Icelandic.

Option A: Distil-Whisper (The "Fast" Hugging Face Way)
Model: distil-whisper/distil-large-v3
Why: It is 6x faster than standard Whisper and 50% smaller, losing less than 1% accuracy.
Mac Optimization:
It runs natively in the transformers pipeline.
Because it is smaller, you can likely use float16 on Mac without the crash, doubling the speed again.
Option B: Faster-Whisper (The "CTranslate2" Way)
Library: faster-whisper (Standalone library, not Hugging Face).
Mechanism: Uses CTranslate2, a C++ inference engine that is heavily optimized.
Mac Optimization:
Supports int8 quantization on Mac CPU/GPU.
Speed: Approx 4x-5x faster than PyTorch/MPS.
Trade-off: You cannot easily use your custom Icelandic fine-tune here without manually converting the weights. For English, it works out of the box.