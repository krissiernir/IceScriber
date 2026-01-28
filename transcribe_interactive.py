#!/usr/bin/env python3
"""
IceScriber Interactive Transcription Tool
Uses file picker GUI and organized folder structure

Features:
- GUI file picker (or CLI fallback)
- Automatic input/output folder organization
- Choose language (Icelandic v2 or English Distil-Whisper)
- Progress tracking
- Organized output in data/ folders

Usage:
    python transcribe_interactive.py
"""

import sys
import os
from pathlib import Path
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from file_picker import pick_files, pick_folder, scan_folder, HAS_GUI
except ImportError:
    print("❌ Error: file_picker.py not found")
    print("   Make sure you're running from the project root")
    sys.exit(1)


class InteractiveTranscriber:
    """Interactive transcription with file picker."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.input_icelandic = self.project_root / "data" / "input" / "icelandic"
        self.input_english = self.project_root / "data" / "input" / "english"
        self.output_icelandic = self.project_root / "data" / "output" / "icelandic"
        self.output_english = self.project_root / "data" / "output" / "english"
        self.logs = self.project_root / "logs"

        # Ensure folders exist
        self._ensure_folders()

    def _ensure_folders(self):
        """Create folder structure if needed."""
        for folder in [self.input_icelandic, self.input_english,
                       self.output_icelandic, self.output_english,
                       self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    def choose_language(self) -> str:
        """Ask user to choose language."""
        print("\n" + "=" * 70)
        print("IceScriber - Interactive Transcription")
        print("=" * 70)
        print("\n🌍 Select Language:")
        print("  1. Icelandic (chapterbatch_v2.py - SDPA optimized)")
        print("  2. English (chapterbatch_english.py - Distil-Whisper 6x faster)")
        print()

        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == '1':
                return 'icelandic'
            elif choice == '2':
                return 'english'
            else:
                print("  ❌ Invalid choice. Enter 1 or 2.")

    def choose_input_method(self) -> str:
        """Ask user how they want to provide files."""
        print("\n📁 How do you want to provide audio files?")
        if HAS_GUI:
            print("  1. File picker (GUI - select individual files)")
            print("  2. Folder scanner (select folder, auto-find all audio)")
            print("  3. Use files already in data/input/ folder")
        else:
            print("  1. Manual entry (type file paths)")
            print("  2. Use files already in data/input/ folder")
        print()

        while True:
            if HAS_GUI:
                choice = input("Enter choice (1, 2, or 3): ").strip()
                if choice in ['1', '2', '3']:
                    return choice
            else:
                choice = input("Enter choice (1 or 2): ").strip()
                if choice in ['1', '2']:
                    return choice

            print("  ❌ Invalid choice")

    def get_files(self, language: str, method: str) -> list:
        """Get list of files to transcribe."""
        input_folder = self.input_icelandic if language == 'icelandic' else self.input_english

        if method == '1':
            # File picker
            mode = 'gui' if HAS_GUI else 'cli'
            print(f"\n📂 Opening file picker ({mode})...")
            files = pick_files(mode=mode, filetype='audio', multiple=True)

            if files:
                # Copy to input folder
                print(f"\n📋 Copying files to {input_folder.name}/...")
                for f in files:
                    dest = input_folder / f.name
                    if dest.exists():
                        print(f"  ⚠️  {f.name} already exists, skipping")
                    else:
                        shutil.copy2(f, dest)
                        print(f"  ✓ {f.name}")

                # Return files in input folder
                return [input_folder / f.name for f in files if (input_folder / f.name).exists()]

        elif method == '2':
            # Folder scanner
            print(f"\n📂 Select folder containing audio files...")
            folder = pick_folder(mode='gui' if HAS_GUI else 'cli')

            if folder:
                print(f"\n🔍 Scanning {folder} for audio files...")
                files = scan_folder(folder, filetype='audio', recursive=False)

                if files:
                    print(f"  Found {len(files)} file(s)")

                    # Copy to input folder
                    print(f"\n📋 Copying files to {input_folder.name}/...")
                    for f in files:
                        dest = input_folder / f.name
                        if dest.exists():
                            print(f"  ⚠️  {f.name} already exists, skipping")
                        else:
                            shutil.copy2(f, dest)
                            print(f"  ✓ {f.name}")

                    return [input_folder / f.name for f in files if (input_folder / f.name).exists()]
                else:
                    print("  ❌ No audio files found in folder")

        elif method == '3':
            # Use existing files
            print(f"\n🔍 Scanning {input_folder}/ for audio files...")
            files = scan_folder(input_folder, filetype='audio', recursive=False)

            if files:
                print(f"  Found {len(files)} file(s):")
                for f in files:
                    print(f"    • {f.name}")
                return files
            else:
                print(f"  ❌ No audio files found in {input_folder}/")
                print(f"     Place audio files there and run again, or choose a different method")

        return []

    def run_transcription(self, language: str, files: list):
        """Run transcription engine on files."""
        if not files:
            print("\n❌ No files to transcribe")
            return

        print("\n" + "=" * 70)
        print(f"🚀 Starting Transcription")
        print("=" * 70)
        print(f"  Language: {language}")
        print(f"  Files: {len(files)}")
        print()

        # Determine which script to use
        if language == 'icelandic':
            script = self.project_root / "scripts" / "transcription" / "chapterbatch_v2.py"
            input_folder = self.input_icelandic
            output_folder = self.output_icelandic
        else:
            script = self.project_root / "scripts" / "transcription" / "chapterbatch_english.py"
            input_folder = self.input_english
            output_folder = self.output_english

        # Check if script exists
        if not script.exists():
            print(f"❌ Script not found: {script}")
            print("   Run: python reorganize_project.py")
            return

        log_file = self.logs / f"transcription_{language}.log"

        print(f"📝 Log file: {log_file}")
        print(f"📁 Input folder: {input_folder}")
        print(f"📂 Output folder: {output_folder}")
        print()

        # Ask for confirmation
        confirm = input("Start transcription? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

        # Run transcription
        import subprocess

        cmd = [
            sys.executable,
            str(script)
        ]

        print("\n🔄 Running transcription...")
        print(f"   Command: {' '.join(cmd)}")
        print()

        try:
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                # Stream output
                for line in process.stdout:
                    print(line, end='')
                    log.write(line)

                process.wait()

            if process.returncode == 0:
                print("\n✅ Transcription complete!")
                print(f"📂 Output saved to: {output_folder}/")
                print(f"📝 Log saved to: {log_file}")
            else:
                print(f"\n❌ Transcription failed (exit code {process.returncode})")
                print(f"   Check log: {log_file}")

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            process.kill()

        except Exception as e:
            print(f"\n❌ Error: {e}")

    def run(self):
        """Main interactive flow."""
        try:
            # Step 1: Choose language
            language = self.choose_language()

            # Step 2: Choose input method
            method = self.choose_input_method()

            # Step 3: Get files
            files = self.get_files(language, method)

            # Step 4: Run transcription
            if files:
                self.run_transcription(language, files)
            else:
                print("\n❌ No files selected. Exiting.")

        except KeyboardInterrupt:
            print("\n\n⚠️  Cancelled by user")
            sys.exit(0)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    transcriber = InteractiveTranscriber()
    transcriber.run()


if __name__ == "__main__":
    main()
