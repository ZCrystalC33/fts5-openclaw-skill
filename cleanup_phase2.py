#!/usr/bin/env python3
"""
FTS5 Phase 2 Cleanup - Remove session-level duplicates

The indexer has been re-indexing the same session file multiple times,
causing the same messages to appear 100-200x each.

Solution: Keep only the LATEST row per (session_key, message_id) combination.
Older duplicates are stale re-indexes.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.openclaw/fts5.db")

def main():
    print('=== FTS5 Phase 2: Session-Level Dedup ===')
    print(f'Started: {datetime.now().isoformat()}')
    print()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Report before
    total_before = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    print(f'Before: {total_before:,} rows')

    # For rows with same (session_key, message_id), keep the one with highest id (latest)
    # Delete older duplicates
    print()
    print('Removing session+message_id duplicates (keep latest)...')

    # Find duplicates: rows where same (session_key, message_id) exists with higher id
    cursor.execute('''
        DELETE FROM conversations
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM conversations
            GROUP BY session_key, message_id
        )
    ''')

    deleted = cursor.rowcount
    conn.commit()
    print(f'Removed {deleted:,} duplicate rows')

    # Vacuum
    print()
    print('Vacuuming...')
    conn.execute('VACUUM')
    conn.commit()

    # Report after
    total_after = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    print(f'After: {total_after:,} rows')

    # Content quality check
    unique = cursor.execute('SELECT COUNT(DISTINCT content) FROM conversations').fetchone()[0]
    print(f'Unique content: {unique:,}')
    dup_rate = (1 - unique/total_after)*100 if total_after > 0 else 0
    print(f'Duplicate rate: {dup_rate:.1f}%')

    # Session distribution after
    print()
    print('Session distribution after cleanup:')
    sessions = cursor.execute('''
        SELECT session_key, COUNT(*) as cnt
        FROM conversations
        GROUP BY session_key
        ORDER BY cnt DESC
        LIMIT 10
    ''').fetchall()
    for s in sessions:
        print(f'  {s[0][:60]}: {s[1]:,}')

    conn.close()

    print()
    print(f'=== Phase 2 Complete ===')
    print(f'Removed: {deleted:,} | Remaining: {total_after:,}')
    size_mb = os.path.getsize(DB_PATH) / (1024*1024)
    print(f'DB size: {size_mb:.1f} MB')

if __name__ == '__main__':
    main()