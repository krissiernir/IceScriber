# IceScriber Reorganization Guide

**Created:** January 28, 2026

## 🎯 Goals

1. **Clean folder structure** - Separate docs, scripts, data, and config
2. **Better I/O handling** - Don't mix input audio with output transcripts
3. **File picker system** - GUI/CLI file selection for eventual UI
4. **Scalability** - Support future GUI development

---

## 📁 New Structure

```
IceScriber/
├── docs/              # All documentation
├── scripts/           # All executable scripts
│   ├── transcription/ # Transcription engines
│   ├── learner/       # Learning assistant
│   └── utils/         # Utility scripts
├── src/               # Core library code
├── config/            # Configuration files
├── data/              # Data storage (git-ignored)
│   ├── input/         # Audio files
│   │   ├── icelandic/
│   │   └── english/
│   ├── output/        # Generated transcripts
│   │   ├── icelandic/
│   │   └── english/
│   └── databases/     # SQLite databases
└── logs/              # Log files (git-ignored)
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for full details.

---

## 🚀 Quick Start

### Option 1: Automatic Reorganization

Run the reorganization script to set up the new structure:

```bash
python reorganize_project.py
```

This will:
- ✅ Create new folder structure
- ✅ Copy files to new locations
- ✅ Update .gitignore
- ✅ Create documentation
- ⚠️  Keep old files in root (for safety)

After verifying everything works:
```bash
./cleanup_old_structure.sh  # Remove old files
```

### Option 2: Manual Setup

Create folders manually:
```bash
mkdir -p docs scripts/{transcription,learner,utils} src config
mkdir -p data/{input/{icelandic,english},output/{icelandic,english},databases}
mkdir -p logs
```

---

## 🎮 New Features

### 1. File Picker System

**GUI Mode** (with tkinter):
```python
from file_picker import pick_files

# Pick audio files
files = pick_files(mode='gui', filetype='audio')

# Pick folder
folder = pick_folder(mode='gui')

# Scan folder for audio
files = scan_folder(folder, filetype='audio', recursive=True)
```

**CLI Mode** (manual entry):
```python
files = pick_files(mode='cli', filetype='audio')
```

**Auto Mode** (GUI if available, CLI fallback):
```python
files = pick_files(mode='auto', filetype='audio')
```

**Command Line:**
```bash
# GUI file picker
python file_picker.py --mode gui --type audio

# Scan folder
python file_picker.py --scan /path/to/folder --recursive

# Pick single file
python file_picker.py --single
```

### 2. Interactive Transcription

New all-in-one tool with file picker integration:

```bash
python transcribe_interactive.py
```

Features:
- 🎯 Choose language (Icelandic/English)
- 📂 GUI file picker or folder scanner
- 📁 Automatic folder organization
- 📝 Progress logging
- ✅ Clean output structure

---

## 🔄 Migration from Old Structure

### Current State (Old Structure)

```
IceScriber/
├── chapterbatch.py                # ← Script in root
├── learner_db.py                  # ← Library in root
├── ARCHITECTURE.md                # ← Doc in root
├── audio_chapters/                # ← Input mixed with output
│   ├── file.mp3
│   ├── file.mp3.json              # ← Output mixed with input
│   └── file.mp3_TRANSCRIPT.txt
└── transcripts.db                 # ← Database in root
```

**Problems:**
- ❌ Files scattered everywhere
- ❌ Input/output mixed in same folder
- ❌ Hard to find things
- ❌ Doesn't scale for GUI

### New State (After Reorganization)

```
IceScriber/
├── scripts/transcription/
│   └── chapterbatch_v2.py         # ← Clean location
├── src/
│   └── learner_db.py              # ← Library code
├── docs/
│   └── ARCHITECTURE.md            # ← Documentation
├── data/
│   ├── input/icelandic/
│   │   └── file.mp3               # ← Input only
│   ├── output/icelandic/
│   │   ├── file.mp3.json          # ← Output only
│   │   └── file.mp3_TRANSCRIPT.txt
│   └── databases/
│       └── transcripts.db         # ← Databases
└── logs/
    └── transcription.log          # ← Logs
```

**Benefits:**
- ✅ Everything has a place
- ✅ Input/output separated
- ✅ Easy to navigate
- ✅ Ready for GUI
- ✅ Git-friendly (.gitignore data/)

---

## 📋 Migration Checklist

### Step 1: Run Reorganization
```bash
python reorganize_project.py
```

Expected output:
```
📁 Creating folder structure...
   ✓ docs/
   ✓ scripts/transcription/
   ✓ scripts/learner/
   ✓ src/
   ✓ data/input/icelandic/
   ...

📦 Moving files...
   ✓ ARCHITECTURE.md → docs/
   ✓ chapterbatch_v2.py → scripts/transcription/
   ...

✅ Reorganization Complete!
```

### Step 2: Test New Structure
```bash
# Test file picker
python file_picker.py --mode gui --type audio

# Test transcription scripts
python scripts/transcription/chapterbatch_v2.py --help
python scripts/learner/learner_query.py --help

# Test interactive tool
python transcribe_interactive.py
```

### Step 3: Update Your Workflow

**Old workflow:**
```bash
# Put files in audio_chapters/
cp podcast.mp3 audio_chapters/

# Run script from root
python chapterbatch_v2.py

# Output mixed with input in audio_chapters/
```

**New workflow:**
```bash
# Option A: Use interactive tool
python transcribe_interactive.py

# Option B: Manual
cp podcast.mp3 data/input/english/
python scripts/transcription/chapterbatch_english.py
# Output in data/output/english/
```

### Step 4: Clean Up (Optional)
```bash
# After verifying everything works
./cleanup_old_structure.sh
```

This removes old files from root but keeps new structure intact.

---

## 🔧 Updating Scripts for New Structure

### Before (Old Paths)
```python
INPUT_FOLDER = "audio_chapters"
OUTPUT_FOLDER = "audio_chapters"  # Same folder!
```

### After (New Paths)
```python
from pathlib import Path

project_root = Path(__file__).parent.parent  # If in scripts/
input_folder = project_root / "data" / "input" / "icelandic"
output_folder = project_root / "data" / "output" / "icelandic"
```

### Example: Update chapterbatch_v2.py

```python
# At top of file
from pathlib import Path

# Update paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # From scripts/transcription/
INPUT_FOLDER = PROJECT_ROOT / "data" / "input" / "icelandic"
OUTPUT_FOLDER = PROJECT_ROOT / "data" / "output" / "icelandic"
```

---

## 🎨 GUI Development Ready

The new structure and file picker make GUI development straightforward:

### Future GUI Layout
```
┌─────────────────────────────────────┐
│ IceScriber                      ─ □ × │
├─────────────────────────────────────┤
│                                     │
│  Language:  ○ Icelandic  ○ English │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Selected Files:               │ │
│  │  • podcast_ep01.mp3           │ │
│  │  • podcast_ep02.mp3           │ │
│  └───────────────────────────────┘ │
│                                     │
│  [📁 Browse Files] [📂 Scan Folder]│
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Progress: 2/5 files           │ │
│  │ ████████░░░░░░░░ 40%          │ │
│  └───────────────────────────────┘ │
│                                     │
│  [▶ Start Transcription] [■ Stop]  │
│                                     │
└─────────────────────────────────────┘
```

**Backend already ready:**
- ✅ File picker (`file_picker.py`)
- ✅ Folder organization (`data/`)
- ✅ Progress logging (`logs/`)
- ✅ Engines ready (`scripts/transcription/`)

**Just need:**
- [ ] GUI framework (tkinter/PyQt/Electron)
- [ ] Progress bar integration
- [ ] Settings panel

---

## 📊 Benefits Summary

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| **File organization** | Scattered | Organized | ⭐⭐⭐ |
| **Input/output** | Mixed | Separated | ⭐⭐⭐ |
| **Findability** | Hard | Easy | ⭐⭐ |
| **Scalability** | Poor | Good | ⭐⭐⭐ |
| **Git-friendly** | No | Yes | ⭐⭐ |
| **GUI-ready** | No | Yes | ⭐⭐⭐ |
| **File picker** | No | Yes (GUI/CLI) | ⭐⭐⭐ |

---

## 🚨 Troubleshooting

### "Module not found" errors

**Problem:** Scripts can't find imports after reorganization

**Solution:** Update import paths in scripts
```python
# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now imports work
from src.learner_db import add_book
```

### Old folder structure still exists

**Problem:** Files duplicated in old and new locations

**Solution:** Run cleanup script after verifying new structure
```bash
./cleanup_old_structure.sh
```

### File picker doesn't open

**Problem:** tkinter not installed (rare on macOS/Windows)

**Solution:** Falls back to CLI mode automatically
```python
# Will use CLI if GUI unavailable
files = pick_files(mode='auto')
```

### Paths don't work in scripts

**Problem:** Scripts still using old hardcoded paths

**Solution:** Use Path relative to script location
```python
from pathlib import Path

# Get project root (adjust based on script location)
if __file__.find('scripts/transcription') != -1:
    # Script is in scripts/transcription/
    project_root = Path(__file__).parent.parent.parent
else:
    # Script is in root
    project_root = Path(__file__).parent

# Build paths from root
input_folder = project_root / "data" / "input" / "icelandic"
```

---

## 📝 Files Created

This reorganization adds these new files:

1. **reorganize_project.py** - Reorganization automation
2. **file_picker.py** - GUI/CLI file picker utility
3. **transcribe_interactive.py** - Interactive transcription tool
4. **PROJECT_STRUCTURE.md** - Structure documentation
5. **REORGANIZATION_GUIDE.md** - This file
6. **cleanup_old_structure.sh** - Old file cleanup

---

## 🎯 Next Steps

### Immediate
- [ ] Run `python reorganize_project.py`
- [ ] Test `python transcribe_interactive.py`
- [ ] Try `python file_picker.py --mode gui`
- [ ] Verify everything works
- [ ] Run `./cleanup_old_structure.sh`

### Short Term
- [ ] Update existing scripts to use new paths
- [ ] Add file picker to learner scripts
- [ ] Create settings/config panel
- [ ] Update README with new structure

### Long Term
- [ ] Build GUI with file picker integration
- [ ] Add drag-and-drop support
- [ ] Progress bars and status updates
- [ ] Settings persistence
- [ ] Batch processing queue

---

## 💡 Design Principles

The reorganization follows these principles:

1. **Separation of Concerns**
   - Code (scripts/, src/)
   - Data (data/)
   - Documentation (docs/)
   - Configuration (config/)

2. **Input/Output Separation**
   - Input: `data/input/`
   - Output: `data/output/`
   - Never mixed

3. **Language Separation**
   - Icelandic and English in separate folders
   - Easy to add more languages later

4. **Git-Friendly**
   - Large files (.mp3, .db) git-ignored
   - Structure preserved with .gitkeep
   - Only code and docs in repo

5. **GUI-Ready**
   - File picker already built
   - Paths relative to project root
   - Logging infrastructure ready

---

**Summary:** Clean structure, separated I/O, file picker system, GUI-ready foundation

**Status:** ✅ Ready to implement

**Next:** Run `python reorganize_project.py`
