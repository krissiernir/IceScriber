#!/usr/bin/env python3
"""
Reorganize IceScriber project structure
Creates clean folder hierarchy and moves files to proper locations
"""

import os
import shutil
from pathlib import Path

# Define new structure
STRUCTURE = {
    "docs": [
        "ARCHITECTURE.md",
        "ROADMAP.md",
        "technical_notes.md",
        "OVERNIGHT_TEST.md",
        "QUICK_START.txt",
        "V1_VS_V2_COMPARISON.md",
        "V2_TEST_RESULTS.md",
        "TRANSCRIPTION_V2_CHANGELOG.md",
        "TRANSCRIPTION_UPGRADE_SUMMARY.md",
        "ENGLISH_VERSION_README.md",
        "LEARNER_STATUS.md",
        "TEST_RESULTS.md"
    ],
    "scripts/transcription": [
        "chapterbatch.py",
        "chapterbatch_v2.py",
        "chapterbatch_english.py"
    ],
    "scripts/learner": [
        "learner_ingest.py",
        "learner_query.py",
        "learner_chat_simple.py",
        "learner_chat_intelligent.py"
    ],
    "scripts/utils": [
        "compare_v1_v2.py",
        "check_analysis_progress.sh",
        "test_v2_performance.sh",
        "test_qa.py"
    ],
    "src": [
        "learner_db.py",
        "learner_llm.py",
        "learner_schema.sql"
    ],
    "config": [
        "chapter_mapping.json"
    ]
}

# Folders to create
FOLDERS_TO_CREATE = [
    "docs",
    "scripts/transcription",
    "scripts/learner",
    "scripts/utils",
    "src",
    "config",
    "data/input/icelandic",
    "data/input/english",
    "data/output/icelandic",
    "data/output/english",
    "data/databases",
    "logs"
]

def create_folders():
    """Create new folder structure."""
    print("📁 Creating folder structure...")
    for folder in FOLDERS_TO_CREATE:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {folder}/")

def move_files():
    """Move files to their new locations."""
    print("\n📦 Moving files...")

    for dest_folder, files in STRUCTURE.items():
        for filename in files:
            src = Path(filename)
            if src.exists():
                dest = Path(dest_folder) / filename
                shutil.copy2(src, dest)
                print(f"   ✓ {filename} → {dest_folder}/")
            else:
                print(f"   ⚠️  {filename} not found (skipping)")

def move_data_files():
    """Move data files to data/ folder."""
    print("\n📊 Moving data files...")

    # Move databases
    db_files = ["transcripts.db", "learner.db"]
    for db in db_files:
        src = Path(db)
        if src.exists():
            dest = Path("data/databases") / db
            shutil.copy2(src, dest)
            print(f"   ✓ {db} → data/databases/")

    # Create README in data/input folders
    input_readme = """# Audio Input Folder

Place your audio files here:
- **icelandic/**: Icelandic audiobooks (for chapterbatch_v2.py)
- **english/**: English podcasts/audiobooks (for chapterbatch_english.py)

Supported formats: .mp3, .m4a, .wav
"""

    with open("data/input/README.md", "w") as f:
        f.write(input_readme)
    print("   ✓ Created data/input/README.md")

    output_readme = """# Transcription Output Folder

Generated transcripts are saved here:
- **icelandic/**: Icelandic transcriptions (.json, .txt, .md, etc.)
- **english/**: English transcriptions

Output formats:
- `.json` - Source of truth (timestamped segments)
- `_TRANSCRIPT.txt` - Human-readable with timestamps
- `_MARKDOWN.md` - Clean paragraphs
- `_LLM.txt` - Optimized for LLM ingestion
"""

    with open("data/output/README.md", "w") as f:
        f.write(output_readme)
    print("   ✓ Created data/output/README.md")

def create_gitkeep():
    """Create .gitkeep in empty folders."""
    print("\n🔖 Creating .gitkeep files...")

    folders = [
        "data/input/icelandic",
        "data/input/english",
        "data/output/icelandic",
        "data/output/english",
        "logs"
    ]

    for folder in folders:
        gitkeep = Path(folder) / ".gitkeep"
        gitkeep.touch()
        print(f"   ✓ {folder}/.gitkeep")

def update_gitignore():
    """Update .gitignore for new structure."""
    print("\n📝 Updating .gitignore...")

    gitignore_additions = """
# Data folders (keep structure, ignore contents)
data/input/icelandic/*
data/input/english/*
!data/input/*/.gitkeep
!data/input/*/README.md

data/output/*
!data/output/*/.gitkeep
!data/output/*/README.md

data/databases/*.db
data/databases/*.db-*

# Logs
logs/*.txt
logs/*.log
!logs/.gitkeep

# Old structure (deprecated)
audio_chapters/
audio_chapters_english/
v1_backup/
"""

    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        with open(gitignore_path, "a") as f:
            f.write("\n# === Auto-added by reorganize_project.py ===\n")
            f.write(gitignore_additions)
        print("   ✓ Updated .gitignore")
    else:
        print("   ⚠️  .gitignore not found")

def create_cleanup_script():
    """Create script to clean up old files."""
    print("\n🧹 Creating cleanup script...")

    cleanup = """#!/bin/bash
# Cleanup old files after reorganization
# Run this AFTER verifying the new structure works

echo "⚠️  WARNING: This will DELETE old files from root directory"
echo "Make sure you've verified the new structure works first!"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo "Cleaning up old files..."

# Remove old documentation from root
rm -f ARCHITECTURE.md ROADMAP.md technical_notes.md
rm -f OVERNIGHT_TEST.md QUICK_START.txt
rm -f V1_VS_V2_COMPARISON.md V2_TEST_RESULTS.md
rm -f TRANSCRIPTION_V2_CHANGELOG.md TRANSCRIPTION_UPGRADE_SUMMARY.md
rm -f ENGLISH_VERSION_README.md LEARNER_STATUS.md TEST_RESULTS.md

# Remove old scripts from root
rm -f chapterbatch.py chapterbatch_v2.py chapterbatch_english.py
rm -f learner_ingest.py learner_query.py
rm -f learner_chat_simple.py learner_chat_intelligent.py
rm -f compare_v1_v2.py check_analysis_progress.sh test_v2_performance.sh
rm -f test_qa.py

# Remove old src files from root
rm -f learner_db.py learner_llm.py learner_schema.sql

# Remove old config from root
rm -f chapter_mapping.json

# Remove old data files from root
rm -f transcripts.db learner.db

# Remove log files from root
rm -f analysis_log.txt transcription_log.txt testv2_log.txt v2_timing.txt
rm -f testv2_log_clean.txt

echo "✅ Cleanup complete!"
echo ""
echo "Old structure removed. New structure:"
echo "  docs/          - All documentation"
echo "  scripts/       - All scripts"
echo "  src/           - Core libraries"
echo "  config/        - Configuration files"
echo "  data/          - Data folders"
echo "  logs/          - Log files"
"""

    with open("cleanup_old_structure.sh", "w") as f:
        f.write(cleanup)

    os.chmod("cleanup_old_structure.sh", 0o755)
    print("   ✓ Created cleanup_old_structure.sh")

def create_project_readme():
    """Create README for new structure."""
    print("\n📖 Creating PROJECT_STRUCTURE.md...")

    readme = """# IceScriber Project Structure

## 📁 Folder Organization

```
IceScriber/
├── README.md                    # Main project README
├── CHANGELOG.md                 # Version history
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── .env.example                 # Environment variable template
├── .env                         # Your API keys (git-ignored)
│
├── docs/                        # 📚 All documentation
│   ├── ARCHITECTURE.md          # System design
│   ├── ROADMAP.md               # Future plans
│   ├── technical_notes.md       # Optimization notes
│   ├── V1_VS_V2_COMPARISON.md   # Performance comparison
│   ├── V2_TEST_RESULTS.md       # Test results
│   ├── TRANSCRIPTION_V2_CHANGELOG.md
│   ├── TRANSCRIPTION_UPGRADE_SUMMARY.md
│   ├── ENGLISH_VERSION_README.md
│   ├── LEARNER_STATUS.md
│   ├── TEST_RESULTS.md
│   ├── OVERNIGHT_TEST.md
│   └── QUICK_START.txt
│
├── scripts/                     # 🛠️ All executable scripts
│   ├── transcription/           # Transcription engines
│   │   ├── chapterbatch.py      # v1 (reference)
│   │   ├── chapterbatch_v2.py   # v2 Icelandic (recommended)
│   │   └── chapterbatch_english.py  # English edition
│   ├── learner/                 # Learning assistant scripts
│   │   ├── learner_ingest.py    # Ingest transcripts
│   │   ├── learner_query.py     # Query database
│   │   ├── learner_chat_simple.py    # Simple Q&A
│   │   └── learner_chat_intelligent.py  # AI-powered Q&A
│   └── utils/                   # Utility scripts
│       ├── compare_v1_v2.py     # Compare versions
│       ├── test_v2_performance.sh
│       ├── check_analysis_progress.sh
│       └── test_qa.py
│
├── src/                         # 🔧 Core library code
│   ├── learner_db.py            # Database utilities
│   ├── learner_llm.py           # LLM integration
│   └── learner_schema.sql       # Database schema
│
├── config/                      # ⚙️ Configuration files
│   └── chapter_mapping.json     # Chapter structure
│
├── data/                        # 💾 Data storage (git-ignored)
│   ├── input/                   # Audio files go here
│   │   ├── icelandic/           # .mp3, .m4a, .wav
│   │   └── english/
│   ├── output/                  # Generated transcripts
│   │   ├── icelandic/           # .json, .txt, .md, etc.
│   │   └── english/
│   └── databases/               # SQLite databases
│       ├── transcripts.db
│       └── learner.db
│
└── logs/                        # 📝 Log files (git-ignored)
    ├── analysis_log.txt
    └── transcription_log.txt
```

## 🎯 Quick Start

### Transcribe Icelandic Audio
```bash
# 1. Place audio in data/input/icelandic/
cp your_audiobook.mp3 data/input/icelandic/

# 2. Run v2 engine
python scripts/transcription/chapterbatch_v2.py

# 3. Find output in data/output/icelandic/
```

### Transcribe English Audio
```bash
# 1. Place audio in data/input/english/
cp your_podcast.mp3 data/input/english/

# 2. Run English engine
python scripts/transcription/chapterbatch_english.py

# 3. Find output in data/output/english/
```

### Run Learning Assistant
```bash
# Ingest transcripts
python scripts/learner/learner_ingest.py --analyze

# Query interactively
python scripts/learner/learner_chat_intelligent.py
```

## 📋 File Naming Convention

### Input Files
- Keep original names
- Supported: `.mp3`, `.m4a`, `.wav`

### Output Files
- `{filename}.json` - Source of truth (timestamped segments)
- `{filename}_TRANSCRIPT.txt` - With timestamps
- `{filename}_MARKDOWN.md` - Clean paragraphs
- `{filename}_LLM.txt` - LLM-optimized

### Version Suffix
- v2 outputs: `{filename}.v2.json`, `{filename}_TRANSCRIPT.v2.txt`

## 🔄 Migration from Old Structure

If you have files in the old structure:

1. **Run reorganization:**
   ```bash
   python reorganize_project.py
   ```

2. **Verify new structure works:**
   ```bash
   python scripts/transcription/chapterbatch_v2.py --help
   ```

3. **Clean up old files:**
   ```bash
   ./cleanup_old_structure.sh
   ```

## 🚫 What's Git-Ignored

- `data/input/**/*` - Your audio files (too large)
- `data/output/**/*` - Generated transcripts (regenerable)
- `data/databases/*.db` - Databases (local data)
- `logs/*.txt` - Log files
- `.env` - API keys (security)
- `__pycache__/` - Python cache

## 📝 Notes

- Keep `.gitkeep` files to preserve folder structure in git
- Don't commit large audio/database files
- API keys go in `.env` (use `.env.example` as template)
"""

    with open("PROJECT_STRUCTURE.md", "w") as f:
        f.write(readme)

    print("   ✓ Created PROJECT_STRUCTURE.md")

def main():
    print("=" * 70)
    print("IceScriber Project Reorganization")
    print("=" * 70)
    print()

    create_folders()
    move_files()
    move_data_files()
    create_gitkeep()
    update_gitignore()
    create_cleanup_script()
    create_project_readme()

    print("\n" + "=" * 70)
    print("✅ Reorganization Complete!")
    print("=" * 70)
    print()
    print("📁 New structure created in:")
    for folder in ["docs/", "scripts/", "src/", "config/", "data/", "logs/"]:
        print(f"   • {folder}")
    print()
    print("🔍 Review the new structure:")
    print("   cat PROJECT_STRUCTURE.md")
    print()
    print("⚠️  Old files are still in root (preserved for safety)")
    print("   After verifying everything works, run:")
    print("   ./cleanup_old_structure.sh")
    print()
    print("📖 Documentation updated:")
    print("   • .gitignore (added new patterns)")
    print("   • PROJECT_STRUCTURE.md (new structure guide)")
    print()

if __name__ == "__main__":
    main()
