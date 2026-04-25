#!/usr/bin/env python3
"""
FTS5 Cleanup Script v2.0
- Remove duplicate messages (dedup by content_hash)
- Filter out noise: HEARTBEAT_OK, NO_REPLY, [[empty]], system messages
- Add content_hash for future dedup
- Report cleanup results
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.openclaw/fts5.db")
BACKUP_PATH = os.path.expanduser("~/.openclaw/fts5.db.backup_before_cleanup")

# Noise content patterns to filter
NOISE_PATTERNS = [
    'HEARTBEAT_OK',
    'NO_REPLY',
    '[[empty]]',
    'Read HEARTBEAT.md if it exists',
    'Follow it strictly. Do not infer',
]

def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def is_noise(content: str) -> bool:
    if not content:
        return True
    for pattern in NOISE_PATTERNS:
        if pattern in content:
            return True
    return False

def main():
    print('=== FTS5 Database Cleanup ===')
    print(f'Started: {datetime.now().isoformat()}')
    print()

    # Create backup first
    print('Step 0: Backing up database...')
    if os.path.exists(DB_PATH):
        import shutil
        shutil.copy2(DB_PATH, BACKUP_PATH)
        size_mb = os.path.getsize(DB_PATH) / (1024*1024)
        print(f'  Backup created: {BACKUP_PATH} ({size_mb:.1f} MB)')
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()

    # Report before state
    print('Step 1: Before state...')
    total_before = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    noise_before = cursor.execute(
        "SELECT COUNT(*) FROM conversations WHERE " + 
        " OR ".join([f"content LIKE '%{p}%'" for p in NOISE_PATTERNS])
    ).fetchone()[0]
    print(f'  Total rows: {total_before:,}')
    print(f'  Noise rows: {noise_before:,}')

    # Populate content_hash
    print()
    print('Step 2: Populating content_hash...')
    cursor.execute("UPDATE conversations SET content_hash = ? WHERE content_hash IS NULL", (content_hash(''),))
    # Actually compute real hashes
    rows = cursor.execute('SELECT id, content FROM conversations WHERE content_hash IS NULL OR content_hash = ?', (content_hash(''),)).fetchall()
    print(f'  Updating {len(rows):,} rows with real hashes...')
    for i, (row_id, content) in enumerate(rows):
        if content:
            cursor.execute('UPDATE conversations SET content_hash = ? WHERE id = ?', (content_hash(content), row_id))
        if i % 50000 == 0 and i > 0:
            print(f'  Processed {i:,}...')
            conn.commit()
    conn.commit()
    print(f'  Done. Updated {len(rows):,} hashes')

    # Phase 1: Remove exact duplicates (keep oldest by timestamp)
    print()
    print('Step 3: Removing exact duplicates (keep oldest)...')
    # Find duplicates
    dupes = cursor.execute('''
        SELECT content_hash, COUNT(*) as cnt, MIN(timestamp) as oldest
        FROM conversations
        GROUP BY content_hash
        HAVING COUNT(*) > 1
    ''').fetchall()
    print(f'  Found {len(dupes):,} content groups with duplicates')

    # For each duplicate group, keep the row with oldest timestamp, delete rest
    removed_dupes = 0
    for hash_val, cnt, oldest in dupes:
        # Get all ids in this group except the oldest
        ids_to_delete = cursor.execute('''
            SELECT id FROM conversations 
            WHERE content_hash = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (hash_val, oldest)).fetchall()
        if ids_to_delete:
            id_list = ','.join(str(id[0]) for id in ids_to_delete)
            cursor.execute(f'DELETE FROM conversations WHERE id IN ({id_list})')
            removed_dupes += len(ids_to_delete)
    
    conn.commit()
    print(f'  Removed {removed_dupes:,} duplicate rows')

    # Phase 2: Remove noise content
    print()
    print('Step 4: Removing noise content...')
    noise_conditions = " OR ".join([f"content LIKE '%{p}%'" for p in NOISE_PATTERNS])
    cursor.execute(f'DELETE FROM conversations WHERE {noise_conditions}')
    removed_noise = cursor.rowcount
    conn.commit()
    print(f'  Removed {removed_noise:,} noise rows')

    # Phase 3: Remove orphaned FTS entries (sync FTS table with main table)
    print()
    print('Step 5: Rebuilding FTS index...')
    cursor.execute('DELETE FROM conversations_fts WHERE rowid NOT IN (SELECT id FROM conversations)')
    conn.commit()
    print(f'  FTS entries cleaned')

    # Vacuum to reclaim space
    print()
    print('Step 6: Vacuuming database...')
    conn.execute('VACUUM')
    conn.commit()
    print('  Vacuum complete')

    # Report after state
    print()
    print('Step 7: After state...')
    total_after = cursor.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]
    print(f'  Total rows: {total_after:,} (was {total_before:,})')
    print(f'  Removed: {total_before - total_after:,} rows ({(total_before - total_after)/total_before*100:.1f}%)')

    # Content distribution
    print()
    print('Step 8: Content quality after cleanup...')
    unique_content = cursor.execute('SELECT COUNT(DISTINCT content_hash) FROM conversations').fetchone()[0]
    print(f'  Unique content: {unique_content:,}')
    print(f'  Total rows: {total_after:,}')
    dup_rate = (1 - unique_content/total_after)*100 if total_after > 0 else 0
    print(f'  Duplicate rate: {dup_rate:.1f}%')

    conn.close()

    print()
    print(f'=== Cleanup Complete ===')
    print(f'Finished: {datetime.now().isoformat()}')
    
    # Show new stats
    from skills.fts5 import get_stats
    s = get_stats()
    print(f'\nNew FTS5 stats:')
    for k, v in s.items():
        print(f'  {k}: {v}')

if __name__ == '__main__':
    main()