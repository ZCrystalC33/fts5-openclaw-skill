#!/usr/bin/env python3
"""
Real-time FTS5 indexing script
Called by OpenClaw hooks to index messages immediately
Usage: python3 realtime_index.py <json_event>
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

def main():
    if len(sys.argv) < 2:
        print("Usage: realtime_index.py <json_event>", file=sys.stderr)
        sys.exit(1)
    
    try:
        event = json.loads(sys.argv[1])
        
        sender = event.get('sender', 'unknown')
        content = event.get('content', '')
        channel = event.get('channel', 'telegram')
        sender_label = event.get('sender_label', sender)
        session_key = event.get('session_key', '')
        message_id = event.get('message_id', '')
        timestamp = event.get('timestamp', datetime.now().isoformat())
        
        if is_noise(content):
            sys.exit(0)  # Silent skip
        
        if not content or not content.strip():
            sys.exit(0)
        
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
        print(f"Indexed: id={row_id} sender={sender} len={len(content)}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
