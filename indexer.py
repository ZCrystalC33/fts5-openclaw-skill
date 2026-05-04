"""
FTS5 Indexer v1.5 - with checkpoint/resume + two-phase eviction

Fixes applied:
1. Two-phase eviction: write temp then atomic rename
2. Checkpoint/resume for long-running imports
3. Typed session IDs with prefixes
4. Exponential backoff for failures
"""

import os
import sys
import json
import time
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.fts5 import init_db, add_message, get_stats, search

# Lazy-load Honcho client to avoid import errors when Honcho is unavailable
_honcho_client = None

def _get_honcho_client():
    global _honcho_client
    if _honcho_client is None:
        try:
            from skills.fts5.honcho_client import HonchoClient
            _honcho_client = HonchoClient()
        except Exception:
            return None
    return _honcho_client

def _push_to_honcho(peer: str, session_key: str, content: str, message_id: str):
    """Push message to Honcho for semantic indexing (best-effort)."""
    try:
        hc = _get_honcho_client()
        if hc is None:
            return
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            hc.add_message(peer, session_key, content, {"message_id": message_id})
        )
    except Exception:
        pass  # Best-effort, don't fail indexing if Honcho is unavailable

# ============================================================
# PATHS - Bootstrap Sequence: config parsing before use
# ============================================================

STATE_FILE = Path(os.path.expanduser("~/.openclaw/fts5/indexer_state.json"))
SESSIONS_DIR = Path(os.path.expanduser("~/.openclaw/agents/main/sessions"))
_TMP_DIR = Path(os.path.expanduser("~/.openclaw/fts5/.tmp"))

# Ensure tmp directory exists
_TMP_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# TYPED IDs - Session tracking with type prefixes
# ============================================================

SESSION_TYPE_PREFIX = "session:"
INDEX_TYPE_PREFIX = "index:"

def make_session_id(filename: str) -> str:
    """Create a typed session ID from filename."""
    return f"{SESSION_TYPE_PREFIX}{filename}"

def make_index_id(session_id: str, batch: int) -> str:
    """Create a typed index batch ID."""
    return f"{INDEX_TYPE_PREFIX}{session_id}:{batch}"

# ============================================================
# TWO-PHASE EVICTION - From Task Decomposition Pattern
# ============================================================

def save_state_atomic(state: Dict) -> bool:
    """
    Two-phase state save: write to temp file first, then atomic rename.
    
    Phase 1: Write to .tmp file
    Phase 2: fsync + atomic rename
    
    This ensures:
    - If crash between phases: old state is intact
    - No partial state files
    """
    try:
        tmp_file = _TMP_DIR / f"indexer_state.{os.getpid()}.tmp"
        
        # Phase 1: Write to temp file
        with open(tmp_file, 'w') as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Phase 2: Atomic rename
        os.rename(tmp_file, STATE_FILE)
        
        return True
    except Exception as e:
        print(f"❌ Atomic state save failed: {e}")
        return False


def load_state() -> Dict:
    """
    Load indexer state with disk-backed recovery.
    """
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        "indexed_sessions": {},
        "last_run": None,
        "total_indexed": 0,
        "checkpoints": {}  # NEW: checkpoint tracking
    }


def get_session_info(filepath: str) -> Dict:
    """Get current session file info."""
    stat = os.stat(filepath)
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }


def count_messages_in_file(filepath: str) -> int:
    """Count message events in a session file."""
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get('type') == 'message':
                        msg = event.get('message', {})
                        if msg.get('role') in ('user', 'assistant'):
                            count += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    except (IOError, UnicodeDecodeError):
        pass
    return count


# ============================================================
# CHECKPOINT/RESUME - From Long-Running Agents Pattern
# ============================================================

CHECKPOINT_BATCH_SIZE = 100  # Save checkpoint every N messages


def import_session_with_checkpoint(filepath: str, force: bool = False, state: Dict = None) -> Tuple[int, bool, Optional[Dict]]:
    """
    Import messages with checkpoint/resume support.
    
    Args:
        filepath: Path to session file
        force: Force re-index even if unchanged
        state: Shared state dict (for tracking indexed_sessions)
    
    Returns:
        (count imported, was_updated, checkpoint_info)
    """
    filename = os.path.basename(filepath)
    session_id = make_session_id(filename)
    
    # Use provided state or load new
    if state is None:
        state = load_state()
    
    # Get current file info
    session_info = get_session_info(filepath)
    
    # Check if file changed
    if not force and filename in state.get("indexed_sessions", {}):
        last_info = state["indexed_sessions"][filename]
        if (last_info.get("size") == session_info["size"] and 
            last_info.get("mtime") == session_info["mtime"]):
            return 0, False, None
    
    # Get checkpoint if exists
    checkpoint = state.get("checkpoints", {}).get(session_id)
    start_offset = checkpoint.get("last_line", 0) if checkpoint else 0
    
    # Import messages
    count = 0
    last_line = start_offset
    batch_num = checkpoint.get("batch", 0) if checkpoint else 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num < start_offset:
                    continue
                
                try:
                    event = json.loads(line.strip())
                    if event.get('type') == 'message':
                        msg = event.get('message', {})
                        if msg.get('role') in ('user', 'assistant'):
                            msg_id = event.get('id')
                            content = _extract_content(msg)
                            peer = msg.get('role')
                            
                            # Infer channel from filepath for accuracy
                            inferred_channel = infer_channel_from_filepath(filepath)
                            
                            add_message(
                                sender=peer,
                                sender_label=peer,
                                content=content,
                                channel=event.get('metadata', {}).get('channel', inferred_channel),
                                session_key=session_id,
                                message_id=msg_id,
                                timestamp=event.get('timestamp')
                            )
                            
                            # Push to Honcho for semantic search (best-effort)
                            _push_to_honcho(peer, session_id, content, msg_id)
                            
                            count += 1
                            
                            # Checkpoint every batch size
                            if count % CHECKPOINT_BATCH_SIZE == 0:
                                last_line = line_num + 1
                                _save_checkpoint(session_id, last_line, batch_num)
                                batch_num += 1
                
                except (json.JSONDecodeError, KeyError):
                    continue
                
                last_line = line_num + 1
            
            # Final checkpoint
            last_line = last_line if last_line > 0 else start_offset
            _save_checkpoint(session_id, last_line, batch_num)
    
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return count, True, None
    
    # Update state
    state["indexed_sessions"][filename] = {
        **session_info,
        "indexed_at": datetime.now().isoformat(),
        "messages_indexed": count,
        "session_id": session_id
    }
    
    # Clear checkpoint on successful complete import
    if session_id in state.get("checkpoints", {}):
        del state["checkpoints"][session_id]
    
    save_state_atomic(state)
    
    return count, True, None


# Noise content patterns to skip during indexing
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

# ============================================================
# CHANNEL INFERENCE - From Session Path
# ==========================================================

def infer_channel_from_filepath(filepath: str) -> str:
    """
    Infer channel from session filepath.
    
    Args:
        filepath: Path to session file (e.g., /path/to/xxx.jsonl)
    
    Returns:
        Channel string: 'telegram', 'discord', 'cli', etc.
    """
    filepath_lower = filepath.lower()
    
    # Known channel indicators in path
    if 'telegram' in filepath_lower:
        return 'telegram'
    if 'discord' in filepath_lower:
        return 'discord'
    if 'whatsapp' in filepath_lower or 'wa_' in filepath_lower:
        return 'whatsapp'
    
    # Checkpoint/sessions directories often indicate the source
    if '/agents/' in filepath_lower:
        # Agent sessions - check parent directory for channel
        if '/main/' in filepath_lower:
            return 'cli'  # Default for main agent
    
    # Default to 'cli' for local/workspace sessions
    return 'cli'


def _extract_content(msg: Dict) -> str:
    """
    Extract content from message, stripping metadata headers.
    
    Handles Telegram format:
    - 'Conversation info (untrusted metadata): ```json {...} ```\n\n[actual content]'
    - 'Sender (untrusted metadata): ```json {...} ```\n\n[actual content]'
    """
    content_list = msg.get('content', [])
    content = ""
    if isinstance(content_list, list):
        for item in content_list:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    content += item.get('text', '')
                elif item.get('type') == 'toolResult':
                    content += f"[tool: {item.get('toolUseId', 'unknown')}] "
            elif isinstance(item, str):
                content += item
    
    # Strip metadata headers that OpenClaw prepends to messages
    # These are NOT part of the actual user/assistant message
    content = _strip_metadata_headers(content)
    
    result = content.strip()
    
    # Skip only if purely noise (not if it just starts with noise prefix)
    if _is_pure_noise(result):
        return "[SKIP]"  # Marker for add_message to detect and skip
    return result


METADATA_PREFIXES = [
    'Conversation info (untrusted metadata):',
    'Sender (untrusted metadata):',
    'Replied message (untrusted',
    'System (untrusted):',
    '[[Queued messages while',
]

def _strip_metadata_headers(content: str) -> str:
    """
    Strip OpenClaw metadata headers from content, keeping actual message.
    
    Example input:
    'Conversation info (untrusted metadata):\n```json\n{"message_id": "123"}\n```\n\n實際的用戶訊息內容'
    
    Example output:
    '實際的用戶訊息內容'
    """
    if not content:
        return content
    
    result = content
    for prefix in METADATA_PREFIXES:
        if result.startswith(prefix):
            # Find the end of the metadata block (```json ... ```)
            # and strip everything before actual content
            idx = result.find('```')
            if idx >= 0:
                # Find closing ```
                end_idx = result.find('```', idx + 3)
                if end_idx >= 0:
                    # Skip past the code block and any newlines
                    result = result[end_idx + 3:]
                    # Strip leading/trailing whitespace and newlines
                    result = result.lstrip('\n').rstrip()
                    break
            else:
                # No code block, try to find double newline
                idx = result.find('\n\n')
                if idx >= 0:
                    result = result[idx + 2:].lstrip('\n').rstrip()
                    break
                else:
                    # No recognized pattern, strip the prefix only
                    result = result[len(prefix):].strip()
    
    return result


def _is_pure_noise(content: str) -> bool:
    """
    Check if content is purely noise (no actual message).
    
    Returns True only for:
    - Empty content
    - Exact noise patterns (HEARTBEAT_OK, NO_REPLY, etc.)
    - Content that is ONLY metadata prefix with no actual message
    """
    if not content or not content.strip():
        return True
    
    # Exact match noise patterns
    pure_noise = ['NO_REPLY', 'HEARTBEAT_OK', '__KEEPALIVE__', '[[empty]]', '[empty]']
    if content.strip() in pure_noise:
        return True
    
    # Check if content is only metadata prefix (no actual message after)
    stripped = content.strip()
    for prefix in ['Conversation info', 'Sender (untrusted', 'System (untrusted']:
        if stripped.startswith(prefix) and len(stripped) < 200:
            # Check if there's any actual content after the metadata
            # If the content is mostly metadata, consider it noise
            if '```' in content:
                # Has code block - check if there's content after it
                parts = content.split('```')
                if len(parts) >= 3:
                    after = parts[-1].strip()
                    if not after or len(after) < 10:
                        return True
    
    return False


def _save_checkpoint(session_id: str, last_line: int, batch: int):
    """Save a checkpoint for resume."""
    state = load_state()
    if "checkpoints" not in state:
        state["checkpoints"] = {}
    
    state["checkpoints"][session_id] = {
        "last_line": last_line,
        "batch": batch,
        "saved_at": datetime.now().isoformat()
    }
    save_state_atomic(state)


def index_session(filepath: str, force: bool = False, state: Dict = None) -> Tuple[int, bool]:
    """
    Index new messages from a session file.
    
    Args:
        filepath: Path to session file
        force: Force re-index even if unchanged
        state: Shared state dict (for tracking indexed_sessions)
    
    Returns:
        (count imported, was_updated)
    """
    count, updated, _ = import_session_with_checkpoint(filepath, force, state)
    return count, updated


# ============================================================
# EXPONENTIAL BACKOFF - For failed operations
# ============================================================

MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds

def with_exponential_backoff(func):
    """Decorator for operations with exponential backoff retry."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = INITIAL_BACKOFF * (2 ** attempt)
                    print(f"   ⏳ Retry {attempt+1}/{MAX_RETRIES} after {wait}s: {e}")
                    time.sleep(wait)
                continue
        raise last_error
    return wrapper


# ============================================================
# MAIN INDEXER
# ============================================================

def run_indexer() -> Dict:
    """
    Run the FTS5 indexer with checkpoint/resume support.
    
    Two-Phase State Management:
    - Phase 1: Load state from disk
    - Phase 2: Process sessions and update indexed_sessions
    - Phase 3: Save state atomically
    """
    init_db()
    state = load_state()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "sessions_checked": 0,
        "sessions_updated": 0,
        "new_messages": 0,
        "resumed_from_checkpoint": 0,
        "errors": []
    }
    
    if not SESSIONS_DIR.exists():
        results["errors"].append(f"Sessions directory not found: {SESSIONS_DIR}")
        return results
    
    # Check for resumable checkpoints
    pending_checkpoints = state.get("checkpoints", {})
    if pending_checkpoints:
        print(f"🔄 Resuming {len(pending_checkpoints)} checkpoint(s)...")
        for session_id, cp in pending_checkpoints.items():
            # Extract filename from session_id
            filename = session_id.replace(SESSION_TYPE_PREFIX, "")
            filepath = SESSIONS_DIR / filename
            if filepath.exists():
                count, _, _ = import_session_with_checkpoint(str(filepath), state=state)
                if count > 0:
                    results["resumed_from_checkpoint"] += 1
                    results["new_messages"] += count
    
    # Check all session files
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.jsonl') or '.reset.' in filename:
            continue
        
        filepath = SESSIONS_DIR / filename
        results["sessions_checked"] += 1
        
        try:
            count, updated = index_session(str(filepath), state=state)
            if updated:
                results["sessions_updated"] += 1
                results["new_messages"] += count
        except Exception as e:
            results["errors"].append(f"{filename}: {str(e)}")
    
    # Phase 3: Save state atomically
    state["last_run"] = datetime.now().isoformat()
    state["total_indexed"] = get_stats()["total"]
    save_state_atomic(state)
    
    return results


def get_indexer_status() -> Dict:
    """Get current indexer status."""
    state = load_state()
    stats = get_stats()
    
    sessions_tracked = len(state.get("indexed_sessions", {}))
    sessions_in_dir = 0
    if SESSIONS_DIR.exists():
        sessions_in_dir = len([f for f in os.listdir(SESSIONS_DIR) 
                              if f.endswith('.jsonl') and '.reset.' not in f])
    
    return {
        "state_file": str(STATE_FILE),
        "sessions_tracked": sessions_tracked,
        "last_run": state.get("last_run"),
        "total_messages_indexed": stats["total"],
        "total_sessions_in_dir": sessions_in_dir,
        "pending_checkpoints": len(state.get("checkpoints", {})),
        "sessions": {
            fname: info
            for fname, info in state.get("indexed_sessions", {}).items()
        }
    }


if __name__ == "__main__":
    print("🔍 FTS5 Indexer v1.5 Running...")
    print("   [Checkpoint/Resume + Two-Phase Eviction + Typed IDs]")
    print()
    
    # Show status
    status = get_indexer_status()
    print(f"📊 Current Status:")
    print(f"   Sessions tracked: {status['sessions_tracked']}")
    print(f"   Total messages: {status['total_messages_indexed']}")
    print(f"   Pending checkpoints: {status['pending_checkpoints']}")
    print(f"   Last run: {status['last_run'] or 'Never'}")
    print()
    
    # Run indexer
    print("🚀 Running indexer...")
    results = run_indexer()
    
    print(f"   Sessions checked: {results['sessions_checked']}")
    print(f"   Sessions updated: {results['sessions_updated']}")
    print(f"   Resumed from checkpoint: {results['resumed_from_checkpoint']}")
    print(f"   New messages: {results['new_messages']}")
    
    if results['errors']:
        print(f"   Errors: {results['errors']}")
    
    print()
    print("✅ Indexer complete!")
