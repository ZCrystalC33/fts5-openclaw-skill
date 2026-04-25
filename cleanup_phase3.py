#!/usr/bin/env python3
"""
FTS5 Phase 3: Remove structural noise (metadata wrappers)

These are OpenClaw internal metadata structures that shouldn't be in the index:
- "Conversation info (untrusted metadata)" JSON blocks
- "System (untrusted):" system notifications
- "[[Queued messages while..." state messages
- System compact/compression notifications
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.openclaw/fts5.db")

# Patterns to remove
NOISE_PATTERNS = [
    'Conversation info (untrusted metadata)',
    'Sender (untrusted metadata)',
    'System (untrusted):',
    '[[Queued messages while',
    'Replied message (untrusted',
    'Compact completed',
]

def main():
    print('=== FTS5 Phase 3: Remove Structural Noise ===')
    print(f'Started: {datetime.now().isoformat()}')
    print()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Report before
    total_before = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    print(f'Before: {total_before:,} rows')

    # Count noise rows before
    noise_count = 0
    for pattern in NOISE_PATTERNS:
        cnt = cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE content LIKE ?",
            (f'%{pattern}%',)
        ).fetchone()[0]
        noise_count += cnt
        print(f'  "{pattern[:40]}...": {cnt:,}')

    print()
    print(f'Total noise rows: {noise_count:,}')

    # Delete noise
    conditions = " OR ".join(["content LIKE ?" for _ in NOISE_PATTERNS])
    params = [f'%{p}%' for p in NOISE_PATTERNS]
    cursor.execute(f'DELETE FROM conversations WHERE {conditions}', params)
    
    deleted = cursor.rowcount
    conn.commit()
    print(f'Deleted: {deleted:,} rows')

    # Vacuum
    print()
    print('Vacuuming...')
    conn.execute('VACUUM')
    conn.commit()

    # Report after
    total_after = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    print(f'After: {total_after:,} rows')

    # Content quality
    unique = cursor.execute('SELECT COUNT(DISTINCT content) FROM conversations').fetchone()[0]
    print(f'Unique content: {unique:,}')
    dup_rate = (1 - unique/total_after)*100 if total_after > 0 else 0
    print(f'Duplicate rate: {dup_rate:.1f}%')

    # Message quality
    print()
    print('=== Message Quality After Cleanup ===')
    # Real user/assistant messages
    real_msgs = cursor.execute(
        "SELECT COUNT(*) FROM conversations WHERE sender IN ('user', 'assistant') AND content NOT LIKE '%Conversation info%'"
    ).fetchone()[0]
    print(f'Real messages (user/assistant, non-metadata): {real_msgs:,}')

    # Sender distribution
    print()
    print('Sender distribution:')
    senders = cursor.execute('SELECT sender, COUNT(*) FROM conversations GROUP BY sender ORDER BY COUNT(*) DESC').fetchall()
    for s in senders:
        print(f'  {s[0]}: {s[1]:,}')

    # Sample content
    print()
    print('Sample content:')
    samples = cursor.execute('''
        SELECT content, sender, timestamp 
        FROM conversations 
        WHERE sender IN ('user', 'assistant')
        ORDER BY timestamp DESC 
        LIMIT 5
    ''').fetchall()
    for s in samples:
        preview = s[0][:80].replace('\n', ' ')
        print(f'  [{s[1]}] {s[2][:10]}: {preview}...')

    conn.close()

    print()
    print(f'=== Phase 3 Complete ===')
    size_mb = os.path.getsize(DB_PATH) / (1024*1024)
    print(f'Final DB size: {size_mb:.1f} MB')

if __name__ == '__main__':
    main()