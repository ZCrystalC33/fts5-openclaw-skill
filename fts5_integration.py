#!/usr/bin/env python3
"""
FTS5 ↔ Self-Improving Integration Module
Bidirectional sync between conversation history and learning memory.
"""

import os
import sys
from datetime import datetime
from typing import Optional, List, Dict

# Try to import FTS5
FTS5_AVAILABLE = False
try:
    sys.path.insert(0, os.path.expanduser("~/.openclaw/skills/fts5"))
    from skills.fts5 import search, summarize, add_message
    FTS5_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # Try alternative path
    try:
        sys.path.insert(0, os.path.expanduser("~/.openclaw/skills/fts5"))
        from __init__ import search, summarize, add_message
        FTS5_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        pass


# Paths
SELF_IMPROVING_DIR = os.path.expanduser("~/self-improving")
CORRECTIONS_FILE = os.path.expanduser("~/self-improving/corrections.md")
MEMORY_FILE = os.path.expanduser("~/self-improving/memory.md")
FTS5_LOG = os.path.expanduser("~/.openclaw/fts5.log")


def log_to_fts5(event_type: str, content: str, metadata: Optional[Dict] = None):
    """
    Log an event to FTS5 for future search.
    
    Args:
        event_type: 'correction', 'preference', 'pattern', 'learning'
        content: The content to index
        metadata: Additional metadata (source, timestamp, etc.)
    """
    if not FTS5_AVAILABLE:
        print("⚠️ FTS5 not available, skipping indexing")
        return False
    
    try:
        sender_label = "self-improving"
        channel = "self-improving"
        session_key = "self-improving-memory"
        
        # Format content with event type for better search
        formatted_content = f"[{event_type.upper()}] {content}"
        
        if metadata:
            formatted_content += f"\nMeta: {metadata}"
        
        add_message(
            sender="system",
            sender_label=sender_label,
            content=formatted_content,
            channel=channel,
            session_key=session_key
        )
        
        # Also log to local file for debugging
        os.makedirs(os.path.dirname(FTS5_LOG), exist_ok=True)
        with open(FTS5_LOG, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {event_type}: {content}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to log to FTS5: {e}")
        return False


def index_correction(correction_text: str, context: Optional[str] = None):
    """
    Index a correction from Self-Improving into FTS5.
    
    When user corrects something, this logs it so future FTS5 searches
    can find and reference it.
    """
    content = correction_text
    if context:
        content += f"\nContext: {context}"
    
    return log_to_fts5("correction", content, {
        "source": "self-improving",
        "indexed_at": datetime.now().isoformat()
    })


def index_preference(preference_text: str, project: Optional[str] = None):
    """
    Index a user preference into FTS5.
    """
    content = preference_text
    if project:
        content += f"\nProject: {project}"
    
    return log_to_fts5("preference", content, {
        "source": "self-improving",
        "indexed_at": datetime.now().isoformat()
    })


def index_learning(learning_text: str, topic: str):
    """
    Index a learned pattern or knowledge into FTS5.
    """
    return log_to_fts5("learning", learning_text, {
        "source": "self-improving",
        "topic": topic,
        "indexed_at": datetime.now().isoformat()
    })


def search_corrections(query: str, limit: int = 5) -> List[Dict]:
    """
    Search FTS5 for related corrections.
    
    Used when user asks about past corrections or mistakes.
    """
    if not FTS5_AVAILABLE:
        return []
    
    try:
        results = search(f"correction {query}", limit=limit)
        return [r for r in results if r.get('channel') == 'self-improving']
    except Exception as e:
        print(f"❌ FTS5 search failed: {e}")
        return []


def search_preferences(query: str, limit: int = 5) -> List[Dict]:
    """
    Search FTS5 for related preferences.
    """
    if not FTS5_AVAILABLE:
        return []
    
    try:
        results = search(f"preference {query}", limit=limit)
        return [r for r in results if r.get('channel') == 'self-improving']
    except Exception as e:
        print(f"❌ FTS5 search failed: {e}")
        return []


def get_fts5_context_for_topic(topic: str) -> Optional[str]:
    """
    Get relevant FTS5 conversation history for a topic.
    
    Used by context_predictor to enhance memory loading suggestions.
    """
    if not FTS5_AVAILABLE:
        return None
    
    try:
        result = summarize(topic, limit=3)
        if result and not result.get('fallback'):
            return result.get('summary')
    except Exception as e:
        print(f"❌ Failed to get FTS5 context: {e}")
    
    return None


def suggest_memory_for_query(query: str) -> List[str]:
    """
    Analyze a query and suggest which Self-Improving memories to load.
    
    Returns list of file paths/identifiers to load.
    """
    suggestions = []
    
    # Keywords that suggest needing specific memories
    topic_keywords = {
        "domains/fts5": ["fts5", "搜尋", "歷史", "全文", "index"],
        "domains/openclaw": ["openclaw", "技能", "agent", "框架"],
        "domains/python": ["python", "安裝", "程式"],
        "domains/github": ["github", "git", "repo"],
        "domains/trading": ["交易", "freqtrade", "策略", "量化"],
        "memory.md": ["偏好", "設定", "我的", "I prefer", "我喜歡"],
        "corrections.md": ["錯誤", "修正", "不對", "wrong", "mistake"]
    }
    
    query_lower = query.lower()
    
    for memory_path, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                suggestions.append(memory_path)
                break
    
    # If FTS5 available and query seems like history recall
    history_keywords = ["上次", "之前", "曾經", "last time", "before", "previously"]
    if any(kw in query_lower for kw in history_keywords):
        suggestions.append("fts5:context_recall")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique_suggestions.append(s)
    
    return unique_suggestions


def sync_self_improving_to_fts5():
    """
    Sync existing Self-Improving memories to FTS5.
    
    Run this once to index all corrections and preferences.
    """
    print("🔄 Syncing Self-Improving → FTS5...")
    
    synced = 0
    
    # Sync corrections
    if os.path.exists(CORRECTIONS_FILE):
        try:
            with open(CORRECTIONS_FILE, 'r') as f:
                content = f.read()
            
            # Split into lines and index last N corrections
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#')]
            for line in lines[-20:]:  # Last 20
                if line.startswith('-'):
                    line = line[1:].strip()
                if line and len(line) > 10:
                    if index_correction(line):
                        synced += 1
        except Exception as e:
            print(f"❌ Failed to sync corrections: {e}")
    
    print(f"✅ Synced {synced} entries to FTS5")
    return synced


def get_integration_status() -> Dict:
    """
    Get status of FTS5 ↔ Self-Improving integration.
    """
    return {
        "fts5_available": FTS5_AVAILABLE,
        "fts5_log_exists": os.path.exists(FTS5_LOG),
        "corrections_file": CORRECTIONS_FILE,
        "memory_file": MEMORY_FILE,
        "self_improving_dir": SELF_IMPROVING_DIR
    }


# CLI for testing
if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("🔗 FTS5 ↔ Self-Improving Integration")
    print("=" * 50)
    print()
    
    status = get_integration_status()
    print(f"FTS5 Available: {status['fts5_available']}")
    print(f"FTS5 Log: {status['fts5_log_exists']}")
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sync":
            sync_self_improving_to_fts5()
        
        elif command == "status":
            for k, v in status.items():
                print(f"  {k}: {v}")
        
        elif command == "suggest" and len(sys.argv) > 2:
            query = sys.argv[2]
            suggestions = suggest_memory_for_query(query)
            print(f"Query: {query}")
            print(f"Suggestions: {suggestions}")
        
        elif command == "context" and len(sys.argv) > 2:
            topic = sys.argv[2]
            context = get_fts5_context_for_topic(topic)
            if context:
                print(f"FTS5 Context for '{topic}':")
                print(context[:500] + "..." if len(context) > 500 else context)
            else:
                print("No context found or FTS5 unavailable")
    
    else:
        print("Commands:")
        print("  python3 fts5_integration.py sync          - Sync existing memories to FTS5")
        print("  python3 fts5_integration.py status        - Show integration status")
        print("  python3 fts5_integration.py suggest <query> - Suggest memories for query")
        print("  python3 fts5_integration.py context <topic> - Get FTS5 context for topic")