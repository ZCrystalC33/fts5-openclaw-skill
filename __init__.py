"""
FTS5 Full-Text Search for OpenClaw
Provides instant search across all conversation history.

Features:
- FTS5 full-text search
- LLM-powered summarization
- Sensitive data filtering
- Context length management
- Incremental indexing
- Multi-language support (zh-TW, zh-CN, en, ja)

Design Principles (from Agentic Harness Patterns):
1. Compress: Truncation requires recovery pointer
2. Tool & Safety: Canonical check for sensitive content
3. Select: Just-in-time context loading
"""

import sqlite3
import os
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Callable

DB_PATH = os.path.expanduser("~/.openclaw/fts5.db")
SETUP_FILE = os.path.expanduser("~/.openclaw/fts5.env")
CREDENTIALS_DIR = os.path.expanduser("~/.openclaw/credentials")
CREDENTIAL_FILE = os.path.join(CREDENTIALS_DIR, "minimax.key")
CONFIG_FILE = os.path.expanduser("~/.openclaw/config.json")


# ============================================================
# BOOTSTRAP SEQUENCE - Ordered initialization
# ============================================================

def _bootstrap_load_api_key() -> str:
    """
    Bootstrap: Load API key with priority order.
    Priority:
      1. Environment variable (MINIMAX_API_KEY)
      2. ~/.openclaw/credentials/minimax.key (standard location)
      3. ~/.openclaw/fts5.env (legacy location)
      4. ~/.openclaw/config.json (OpenClaw config)
    """
    # Priority 1: Environment variable
    api_key = os.environ.get("MINIMAX_API_KEY")
    if api_key:
        return api_key
    
    # Priority 2: Standard credentials location
    if os.path.exists(CREDENTIAL_FILE):
        with open(CREDENTIAL_FILE, 'r') as f:
            key = f.read().strip()
            if key and len(key) > 20:
                return key
    
    # Priority 3: fts5.env (legacy location)
    if os.path.exists(SETUP_FILE):
        with open(SETUP_FILE, 'r') as f:
            for line in f:
                if line.startswith("MINIMAX_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "sk-cp-YOUR_KEY_HERE":
                        return key
    
    # Priority 4: config.json
    CONFIG_FILE = os.path.expanduser("~/.openclaw/config.json")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if "fts5" in config and config["fts5"].get("api_key"):
                    return config["fts5"]["api_key"]
        except:
            pass
    
    raise ValueError(
        "MINIMAX_API_KEY not found. Please set up PFSI:\n"
        "  1. Run: python3 ~/.openclaw/skills/fts5/setup.py\n"
        "  2. Or create: ~/.openclaw/credentials/minimax.key with your API key\n"
        "  3. Or set environment variable: export MINIMAX_API_KEY=sk-cp-xxx"
    )


def load_api_key() -> str:
    """Public API key loader (uses bootstrap sequence internally)."""
    return _bootstrap_load_api_key()


# Context length limits
DEFAULT_CONTEXT_LIMIT = 2000  # Max chars per message in context
MAX_TOTAL_CONTEXT = 8000     # Max total chars for LLM context
MAX_MESSAGES_IN_CONTEXT = 10  # Max messages to include

# Sensitive data patterns
SENSITIVE_PATTERNS = [
    (r'api[_-]?key[:\s=]+[A-Za-z0-9\-_]{20,}', 'api_key'),
    (r'bearer[:\s]+[A-Za-z0-9\-_\.]{20,}', 'auth_header'),
    (r'[MN][A-Za-z\d]{23,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{27,}', 'bot_token'),
    (r'\d{8,10}:[A-Za-z\d_-]{35,}', 'bot_token'),
    (r'TG[A-Za-z0-9]{20,}', 'telegram_token'),
    (r'-----BEGIN.*?PRIVATE KEY-----', 'private_key'),
    (r'[a-fA-F0-9]{64,}', 'hex_key'),
    (r'0x[a-fA-F0-9]{40}', 'wallet_address'),
]


# ============================================================
# CANONICAL CHECK - From Tool & Safety Pattern
# ============================================================

def _contains_sensitive(content: str) -> Tuple[bool, List[str]]:
    """
    Canonical check for sensitive content.
    Returns (is_sensitive, detected_types).
    Uses single-pass scanning for efficiency.
    """
    if not content or len(content) < 8:
        return False, []
    
    detected_set: List[str] = []
    for pattern, label in SENSITIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            if label not in detected_set:
                detected_set.append(label)
    
    return len(detected_set) > 0, detected_set


def _mask_sensitive(content: str) -> str:
    """Mask sensitive data in content."""
    if not content:
        return content
    
    masked = content
    
    # Mask Discord/Telegram bot tokens
    masked = re.sub(r'[MN][A-Za-z\d]{23,}\.[A-Za-z\d_-]{6,}\.[A-Za-z\d_-]{27,}', '[BOT_TOKEN]', masked)
    masked = re.sub(r'\d{8,10}:[A-Za-z\d_-]{35,}', '[BOT_TOKEN]', masked)
    masked = re.sub(r'TG[A-Za-z0-9]{20,}', '[TELEGRAM_TOKEN]', masked)
    
    # Mask API keys
    masked = re.sub(r'api[_-]?key[:\s=]+[A-Za-z0-9\-_]{20,}', 'API_KEY=[MASKED]', masked, flags=re.IGNORECASE)
    
    # Mask private keys
    masked = re.sub(r'-----BEGIN.*?PRIVATE KEY-----[\s\S]*?-----END.*?PRIVATE KEY-----', '[PRIVATE_KEY]', masked)
    
    # Mask long hex strings
    masked = re.sub(r'[a-fA-F0-9]{64,}', '[HEX_KEY]', masked)
    
    return masked


# ============================================================
# COMPRESS PATTERN - Truncation with Recovery Pointer
# ============================================================

# Recovery pointer template for truncated content
TRUNCATION_MARKER = '...<truncated — recovery: re-run search() or check source session file>'

def _truncate_with_recovery(content: str, limit: int, operation: str = "search()") -> str:
    """
    Truncate content with recovery pointer (Compress Pattern).
    
    Args:
        content: Content to truncate
        limit: Max characters
        operation: Recovery operation hint (e.g., "search()", "cat file")
    
    Returns:
        Truncated content with recovery pointer
    """
    if len(content) <= limit:
        return content
    
    marker = f'...<truncated — recovery: {operation}>'
    return content[:limit - len(marker)] + marker


def _estimate_complexity(query: str) -> str:
    """Estimate query complexity for context adjustment."""
    query_lower = query.lower()
    
    # High complexity indicators
    complex_indicators = ['比較', '分析', '研究', '架構', '完整', '詳細', '所有', 'compare', 'analyze', 'architecture']
    simple_indicators = ['什麼', '哪個', '上次', '簡單', 'what', 'which', 'last']
    
    complex_count = sum(1 for i in complex_indicators if i in query_lower)
    simple_count = sum(1 for i in simple_indicators if i in query_lower)
    
    if complex_count > simple_count:
        return "high"
    elif simple_count > complex_count:
        return "low"
    return "medium"


def _get_context_limits(complexity: str) -> Tuple[int, int, int]:
    """Get context limits based on query complexity."""
    if complexity == "high":
        return 1500, 12000, 15  # per_msg, total, max_msgs
    elif complexity == "low":
        return 800, 4000, 5
    return DEFAULT_CONTEXT_LIMIT, MAX_TOTAL_CONTEXT, MAX_MESSAGES_IN_CONTEXT


def get_db() -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the FTS5 database."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Main conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sender TEXT,
            sender_label TEXT,
            content TEXT,
            channel TEXT,
            session_key TEXT,
            message_id TEXT,
            is_sensitive BOOLEAN DEFAULT 0
        )
    """)
    
    # FTS5 virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
            content,
            sender,
            sender_label,
            channel,
            tokenize='unicode61 remove_diacritics 2'
        )
    """)
    
    # Check if trigger exists
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='trigger' AND name='conversations_ai'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TRIGGER conversations_ai AFTER INSERT ON conversations BEGIN
                INSERT INTO conversations_fts(rowid, content, sender, sender_label, channel)
                VALUES (new.id, new.content, new.sender, new.sender_label, new.channel);
            END
        """)
    
    conn.commit()
    conn.close()


def add_message(
    sender: str,
    content: str,
    channel: str,
    sender_label: Optional[str] = None,
    session_key: Optional[str] = None,
    message_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    skip_sensitive_filter: bool = False
) -> int:
    """
    Add a message to the conversation history.
    
    Args:
        sender: 'user' or 'assistant'
        content: message text
        channel: messaging channel (telegram, discord, etc.)
        sender_label: display name/label
        session_key: session identifier
        message_id: message ID
        timestamp: ISO timestamp
        skip_sensitive_filter: if True, skip sensitive data filtering
    
    Returns:
        Row ID of inserted message, or 0 if filtered
    """
    # Skip [SKIP] markers from indexer's _extract_content
    if content == "[SKIP]":
        return 0

    # Check for sensitive data (canonical check)
    is_sensitive = False
    if not skip_sensitive_filter:
        is_sensitive, _ = _contains_sensitive(content)
    
    # If highly sensitive, mask it instead of skipping
    if is_sensitive:
        content = _mask_sensitive(content)
    
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    # Deduplication guard: if same (sender, content, session_key) exists, delete OLDEST first
    # Then insert new row. This ensures "keep newest" behavior.
    if sender and content and session_key:
        cursor.execute("""
            DELETE FROM conversations 
            WHERE sender = ? AND content = ? AND session_key = ?
        """, (sender, content, session_key))
    
    # Use INSERT OR REPLACE to handle race conditions with unique index
    # This replaces existing row if unique constraint is hit (shouldn't happen after DELETE above)
    cursor.execute("""
        INSERT OR REPLACE INTO conversations (sender, sender_label, content, channel, session_key, message_id, timestamp, is_sensitive)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sender, sender_label, content, channel, session_key, message_id, timestamp, is_sensitive))
    
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def search(query: str, limit: int = 10, channel: Optional[str] = None, 
           complexity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search conversations using FTS5.
    
    Args:
        query: search query
        limit: max results to return
        channel: filter by channel
        complexity: 'low', 'medium', or 'high' (auto-detected if None)
    
    Returns:
        List of matching messages
    """
    if complexity is None:
        complexity = _estimate_complexity(query)
    
    per_msg_limit, total_limit, max_msgs = _get_context_limits(complexity)
    
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query with FTS5
    if channel:
        cursor.execute("""
            SELECT c.*, snippet(conversations_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
            FROM conversations_fts
            JOIN conversations c ON conversations_fts.rowid = c.id
            WHERE conversations_fts MATCH ? AND c.channel = ?
            ORDER BY rank
            LIMIT ?
        """, (query, channel, max_msgs * 2))  # Fetch extra for filtering
    else:
        cursor.execute("""
            SELECT c.*, snippet(conversations_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
            FROM conversations_fts
            JOIN conversations c ON conversations_fts.rowid = c.id
            WHERE conversations_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, max_msgs * 2))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Apply context length management with RECOVERY POINTER
    pruned_results = []
    total_chars = 0
    
    for r in results:
        content = r.get('content', '')
        
        # Truncate long messages WITH recovery pointer (Compress Pattern)
        if len(content) > per_msg_limit:
            content = _truncate_with_recovery(content, per_msg_limit, "search() with higher limit")
            r['content'] = content
        
        # Check total length limit
        if total_chars + len(content) > total_limit and len(pruned_results) >= max_msgs:
            break
        
        pruned_results.append(r)
        total_chars += len(content)
    
    # Apply user's limit
    return pruned_results[:limit]


async def search_async(query: str, limit: int = 10, channel: Optional[str] = None,
                       complexity: Optional[str] = None) -> List[Dict[str, Any]]:
    """Async wrapper for search() - runs SQLite search in thread pool."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search, query, limit, channel, complexity)


def get_recent(limit: int = 20, channel: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get most recent conversations."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    if channel:
        cursor.execute("""
            SELECT * FROM conversations
            WHERE channel = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (channel, limit))
    else:
        cursor.execute("""
            SELECT * FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_stats() -> Dict[str, Any]:
    """Get FTS5 database statistics."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM conversations")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as sensitive FROM conversations WHERE is_sensitive = 1")
    sensitive = cursor.fetchone()["sensitive"]
    
    cursor.execute("SELECT COUNT(DISTINCT channel) as channels FROM conversations")
    channels = cursor.fetchone()["channels"]
    
    cursor.execute("SELECT COUNT(DISTINCT sender) as senders FROM conversations")
    senders = cursor.fetchone()["senders"]
    
    cursor.execute("SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM conversations")
    range_row = cursor.fetchone()
    
    conn.close()
    
    return {
        "total": total,
        "sensitive_masked": sensitive,
        "channels": channels,
        "senders": senders,
        "oldest": range_row["oldest"] if range_row else None,
        "newest": range_row["newest"] if range_row else None,
        "db_path": DB_PATH
    }


def import_from_session_file(session_path: str, force_reindex: bool = False) -> int:
    """
    Import messages from an OpenClaw session JSONL file.
    
    Args:
        session_path: path to .jsonl session file
        force_reindex: if True, re-import all messages (skipping sensitive check)
    
    Returns:
        Count of imported messages
    """
    if not os.path.exists(session_path):
        return 0
    
    count = 0
    session_key = os.path.basename(session_path).replace('.jsonl', '')
    
    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                
                if event.get('type') != 'message':
                    continue
                    
                msg = event.get('message', {})
                role = msg.get('role')
                
                if role not in ('user', 'assistant'):
                    continue
                
                # Extract content
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
                
                content = content.strip()
                if not content:
                    continue
                
                timestamp = event.get('timestamp')
                metadata = event.get('metadata', {}) or {}
                sender_label = metadata.get('sender_label', role)
                channel = metadata.get('channel', 'unknown')
                message_id = event.get('id')
                
                add_message(
                    sender=role,
                    sender_label=sender_label,
                    content=content,
                    channel=channel,
                    session_key=session_key,
                    message_id=message_id,
                    timestamp=timestamp,
                    skip_sensitive_filter=force_reindex
                )
                count += 1
                
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    
    return count


def import_all_sessions(sessions_dir: str, force: bool = False) -> Dict[str, int]:
    """
    Import all session files from a directory.
    Uses incremental indexing - only imports new/modified files.
    
    Args:
        sessions_dir: directory containing .jsonl session files
        force: if True, re-import everything
    
    Returns:
        Dict with counts per file
    """
    results = {}
    state_file = os.path.expanduser("~/.openclaw/fts5/indexer_state.json")
    
    # Load state
    state = {}
    if os.path.exists(state_file) and not force:
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            state = {}
    
    indexed_sessions = state.get("indexed_sessions", {})
    
    if not os.path.exists(sessions_dir):
        return results
    
    for filename in os.listdir(sessions_dir):
        if not filename.endswith('.jsonl') or '.reset.' in filename:
            continue
        
        filepath = os.path.join(sessions_dir, filename)
        
        # Check if file is new or modified (incremental)
        if not force and filename in indexed_sessions:
            file_stat = os.stat(filepath)
            last_info = indexed_sessions[filename]
            if (last_info.get("size") == file_stat.st_size and 
                last_info.get("mtime") == file_stat.st_mtime):
                # No changes, skip
                continue
        
        count = import_from_session_file(filepath, force_reindex=force)
        if count > 0:
            results[filename] = count
            
            # Update state
            file_stat = os.stat(filepath)
            indexed_sessions[filename] = {
                "size": file_stat.st_size,
                "mtime": file_stat.st_mtime,
                "indexed_at": datetime.now().isoformat(),
                "messages_indexed": count
            }
    
    # Save state
    state["indexed_sessions"] = indexed_sessions
    state["last_run"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    return results


def summarize(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search conversations and generate an LLM summary.
    
    Uses context length management based on query complexity.
    """
    from skills.fts5.llm_summary import summarize_conversations
    
    complexity = _estimate_complexity(query)
    per_msg, total, max_msgs = _get_context_limits(complexity)
    
    results = search(query, limit=limit, complexity=complexity)
    return summarize_conversations(query, results, limit=limit)
