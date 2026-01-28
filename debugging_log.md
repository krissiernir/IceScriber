While your computer is busy doing the "heavy lifting," it’s a great time to review the journey. You actually hit almost every major "rite of passage" a developer face when working with AI on a Mac.

Here is the breakdown of why we started where we did, what broke, and why the current solution is the "pro" way to do it.

1. The Original Intent
Your goal was simple: Use a specific Icelandic AI model to turn long audiobooks into text.
You started with the "standard" advice for beginners: use the Hugging Face pipeline. A pipeline is like a "black box"—you throw audio in one side, and text comes out the other.

2. The Common Pitfalls (What went wrong?)

Pitfall A: The "Bleeding Edge" Trap (Python 3.14)
The biggest invisible enemy was Python 3.14. In the coding world, being "up to date" is usually good, but in AI, it’s dangerous.

The Error: You were getting ReadTimeout and ValueErrors for arguments like condition_on_previous_text.
The Reality: AI libraries (PyTorch/Transformers) are massive and complex. They are built for Python 3.10–3.12. Python 3.14 is currently "experimental." The "bridge" between the Python code and your Mac’s AI chips (MPS) hadn't been fully built for 3.14 yet. It was like trying to run a brand new video game on a version of Windows that hasn't been released yet.
Pitfall B: The 30-Second Wall (Long-form Content)
Whisper AI was trained to "listen" in exactly 30-second chunks.

The Error: The program would "Hang" (freeze) or produce gibberish like !!m!!!!.
The Reality: When you give a 24-minute (or 10-hour) file to a pipeline, the library tries to be "smart" and slice it up for you. However, for a 3GB "Large" model, this "smart" slicing uses a massive amount of RAM. Your Mac was likely running out of memory trying to hold the whole book and the whole AI model at once, causing it to "Hang."
Pitfall C: The "Middleman" Bug (KeyError: 'num_frames')
The Error: KeyError: 'num_frames'.
The Reality: This is a known bug in the pipeline library. The pipeline is a "convenience tool" (a middleman). Sometimes, when the middleman gets a piece of audio it doesn't recognize (like a raw slice from your audiobook), it looks for information (like num_frames) that isn't there and crashes.
3. The Ultimate Fix: What did we actually do?
To make this work, we moved from being a "User" of a library to being a "Developer" of a workflow.

Stable Foundation (Python 3.12): We moved you to the version of Python that the AI world actually uses. This fixed the weird connection errors and allowed your Mac’s GPU to talk to the code properly.
Bypassing the Middleman (Direct Model Access): We stopped using the pipeline. Instead, we loaded the Model (the brain) and the Processor (the ears) separately. This gave us total control. No more KeyError because we are now telling the AI exactly what it is hearing.
Manual Slicing (The Progress Bar): Instead of asking the AI to "handle the whole file," we wrote a loop that:
Slices 30 seconds of audio.
Feeds it to the AI.
Prints a progress bar.
Clears the memory.
Repeat.
This is why it doesn't "Hang" anymore. The computer is only ever working on 30 seconds of audio at a time, making it impossible to run out of memory.
4. Summary of Debugging
The Problem	What it looked like	The Solution
Experimental Python	Crashes and Timeouts	Moved to Python 3.12
GPU Incompatibility	Stuttering text (!!m!!!)	Used Float32 math
Memory Overload	Program "Hanging"	Manual Chunking (30s at a time)
Library Bugs	KeyError: num_frames	Used Direct Model (No Pipeline)
OS Issues	ModuleNotFoundError: tkinter	Switched to Folder Batching
What you learned:
You've learned that AI coding is all about data management. The AI itself is powerful, but it’s "fussy." It needs the audio in a specific format (16,000Hz), in specific sizes (30s), and on a stable version of Python.

By building a "Manual Loop," you created a tool that is much more professional than a simple pipeline—it's a robust "Batch Processor" that can handle 100 chapters just as easily as it handles one.

Is the current chapter finishing its progress bar? Once one finishes, check the audio_chapters folder; you should see your first Icelandic transcript waiting for you!
