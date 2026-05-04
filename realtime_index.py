#!/usr/bin/env python3
"""
Real-time FTS5 indexing script
Called by OpenClaw hooks to index messages immediately

Usage:
  python3 realtime_index.py <json_event>        # Single message
  python3 realtime_index.py --batch-file <file>   # Batch from file
"""

import sys
import json
from datetime import datetime

# Skip patterns (same as in indexer.py)
SKIP_PATTERNS = [
    'NO_REPLY',
    'HEARTBEAT_OK',
    '[[empty]]',
    '[empty]',
    'Conversation info (untrusted metadata)',
    'Sender (untrusted metadata)',
    'Replied message (untrusted',
    'System (untrusted):',
    '[[Queued messages while',
]

def is_noise(content: str) -> bool:
    if not content or not content.strip():
        return True
    for p in SKIP_PATTERNS:
        if p in content:
            return True
    return False

def index_message(event):
    """Index a single message"""
    sender = event.get('sender', 'unknown')
    content = event.get('content', '')
    channel = event.get('channel', 'telegram')
    sender_label = event.get('sender_label', sender)
    session_key = event.get('session_key', '')
    message_id = event.get('message_id', '')
    timestamp = event.get('timestamp', datetime.now().isoformat())
    
    if is_noise(content):
        return None  # Silent skip
    
    if not content or not content.strip():
        return None
    
    # Add to FTS5
    sys.path.insert(0, '/home/snow/.openclaw')
    from skills.fts5 import add_message
    
    row_id = add_message(
        sender=sender,
        sender_label=sender_label,
        content=content,
        channel=channel,
        session_key=session_key,
        message_id=message_id,
        timestamp=timestamp
    )
    return row_id

def main():
    # Check for batch mode
    if '--batch-file' in sys.argv:
        # Batch mode: read from file
        try:
            batch_idx = sys.argv.index('--batch-file')
            batch_file = sys.argv[batch_idx + 1]
            
            with open(batch_file, 'r') as f:
                messages = json.load(f)
            
            if not isinstance(messages, list):
                print(f"Error: Expected JSON array in batch file", file=sys.stderr)
                sys.exit(1)
            
            indexed = 0
            for msg in messages:
                try:
                    row_id = index_message(msg)
                    if row_id:
                        indexed += 1
                except Exception as e:
                    print(f"Warning: Failed to index message: {e}", file=sys.stderr)
            
            print(f"Batch indexed: {indexed}/{len(messages)} messages")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Single message mode (original behavior)
    if len(sys.argv) < 2:
        print("Usage: realtime_index.py <json_event>", file=sys.stderr)
        sys.exit(1)
    
    try:
        event = json.loads(sys.argv[1])
        row_id = index_message(event)
        if row_id:
            print(f"Indexed: id={row_id}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
