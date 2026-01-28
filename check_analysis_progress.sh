#!/bin/bash
# Check analysis progress

echo "=== Analysis Progress Check ==="
echo ""

# Check database stats
echo "📊 Database Statistics:"
echo "  Chapters with summaries: $(sqlite3 learner.db 'SELECT COUNT(*) FROM chapter_summaries' 2>/dev/null || echo '0')"
echo "  Total characters: $(sqlite3 learner.db 'SELECT COUNT(*) FROM characters' 2>/dev/null || echo '0')"
echo "  Timeline events: $(sqlite3 learner.db 'SELECT COUNT(*) FROM timeline_events' 2>/dev/null || echo '0')"
echo "  Character events: $(sqlite3 learner.db 'SELECT COUNT(*) FROM character_events' 2>/dev/null || echo '0')"
echo ""

# Check log file if exists
if [ -f analysis_log.txt ]; then
    echo "📝 Recent log output:"
    tail -20 analysis_log.txt
else
    echo "ℹ️  No analysis_log.txt found yet"
fi

echo ""
echo "💡 To watch live: tail -f analysis_log.txt"
