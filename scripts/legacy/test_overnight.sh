#!/bin/bash
# Overnight integration test for IceScriber SQLite portable core
# Tests: ingest, search, query functionality on full audiobook

set -e

echo "================================"
echo "🌙 IceScriber Overnight Test"
echo "================================"
echo ""

# Clean slate
echo "1️⃣  Cleaning database..."
rm -f transcripts.db
echo "   ✓ Old database removed"
echo ""

# Ingest all JSON files
echo "2️⃣  Ingesting all audiobook chapters..."
python3 ingest.py --all --book-title "Dauði Trúðsins" --author "Árni Þórarinsson" 2>&1 | tail -8
echo ""

# List books
echo "3️⃣  Listing all books..."
python3 query.py --list-books | head -15
echo ""

# Test keyword searches
echo "4️⃣  Testing keyword searches..."
echo ""
echo "   Search: 'Dauði'"
python3 query.py "Dauði" --limit 1 | head -10
echo ""

echo "   Search: 'orð'"
python3 query.py "orð" --limit 1 | head -10
echo ""

# Show database stats
echo "5️⃣  Final database stats..."
python3 -c "
import sqlite3
conn = sqlite3.connect('transcripts.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM books')
books = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM audio_files')
audio_files = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM segments')
segments = cursor.fetchone()[0]

import os
db_size = os.path.getsize('transcripts.db') / 1024
print(f'   Books: {books}')
print(f'   Audio Files: {audio_files}')
print(f'   Total Segments: {segments}')
print(f'   Database Size: {db_size:.1f} KB')
"
echo ""
echo "================================"
echo "✅ Overnight test complete!"
echo "================================"
