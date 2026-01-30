"""
Central path resolver for IceScriber.
All scripts import paths from here to find project resources.
"""

from pathlib import Path

# Project root = parent of src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Core directories
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"

# Data subdirectories
INPUT_ICELANDIC = DATA_DIR / "input" / "icelandic"
INPUT_ENGLISH = DATA_DIR / "input" / "english"
OUTPUT_ICELANDIC = DATA_DIR / "output" / "icelandic"
OUTPUT_ENGLISH = DATA_DIR / "output" / "english"
DATABASES_DIR = DATA_DIR / "databases"

# Database files
LEARNER_DB = DATABASES_DIR / "learner.db"
TRANSCRIPTS_DB = DATABASES_DIR / "transcripts.db"

# Config files
CHAPTER_MAPPING = CONFIG_DIR / "chapter_mapping.json"

# Ensure directories exist on import
for d in [INPUT_ICELANDIC, INPUT_ENGLISH, OUTPUT_ICELANDIC, OUTPUT_ENGLISH,
          DATABASES_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
