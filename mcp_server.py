#!/usr/bin/env python3
"""
FTS5 MCP Server - Minimal Viable Edition
JSON-RPC over stdio, exposes FTS5 search/summarize/stats tools.

Protocol: LSP-framed JSON-RPC (Content-Length header)
Version: 2025-03-26 (matches Claw Code MCP)
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional

# ── LSP Framing ──────────────────────────────────────────────

def read_frame() -> Optional[Dict[str, Any]]:
    """Read one LSP-framed JSON-RPC message from stdin."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if line == '':
            return None  # EOF
        if line.strip() == '':
            break
        key, val = line.split(':', 1)
        headers[key.strip()] = val.strip()
    
    if 'Content-Length' not in headers:
        return None
    
    length = int(headers['Content-Length'])
    body = sys.stdin.read(length)
    
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None

def write_frame(msg: Dict[str, Any]):
    """Write one LSP-framed JSON-RPC message to stdout."""
    body = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(f"Content-Length: {len(body)}\r\n")
    sys.stdout.write(f"\r\n{body}")
    sys.stdout.flush()

# ── FTS5 Import ──────────────────────────────────────────────

import importlib.util
import pathlib

# Dynamically load FTS5 from skills directory
# This avoids needing to install the skill as a pip package
_FTS5_PATH = pathlib.Path(__file__).parent

def _import_fts5():
    """Import FTS5 module from local skills/fts5 directory."""
    spec = importlib.util.spec_from_file_location(
        "fts5_module", 
        _FTS5_PATH / "__init__.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_fts5 = _import_fts5()

# Aliases to FTS5 functions
search = _fts5.search
summarize = _fts5.summarize
get_stats = _fts5.get_stats

# ── Tool Definitions ──────────────────────────────────────────

TOOLS = [
    {
        "name": "fts5_search",
        "description": "Search conversation history stored in FTS5. Returns matching messages with sender, timestamp, and channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in natural language"
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fts5_summarize",
        "description": "Search and summarize conversation history using LLM. Returns a natural language summary of relevant discussions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in natural language"
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of messages to analyze for summary"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fts5_stats",
        "description": "Get FTS5 database statistics: total messages indexed, message count per channel, database size.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# ── Request Handlers ─────────────────────────────────────────

def handle_initialize(msg_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "fts5",
                "version": "1.5.0",
                "description": "OpenClaw FTS5 conversation search and LLM summarization"
            }
        }
    }

def handle_tools_list(msg_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {"tools": TOOLS}
    }

def handle_tools_call(msg_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    
    try:
        if tool_name == "fts5_search":
            results = search(
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )
            # Format results as text for the LLM
            output = _format_search_results(results)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": output}]
                }
            }
        
        elif tool_name == "fts5_summarize":
            search_results = search(
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )
            summary = summarize(
                query=arguments.get("query", ""),
                search_results=search_results,
                limit=arguments.get("limit", 5)
            )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": summary["summary"]}]
                }
            }
        
        elif tool_name == "fts5_stats":
            stats = get_stats()
            output = _format_stats(stats)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": output}]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32603,
                "message": f"Tool execution failed: {str(e)}"
            }
        }

def _format_search_results(results: List[Dict]) -> str:
    """Format FTS5 search results as readable text."""
    if not results:
        return "No matching conversations found."
    
    lines = []
    lines.append(f"找到 {len(results)} 筆記錄：\n")
    
    for i, r in enumerate(results, 1):
        sender = r.get('sender', 'unknown')
        channel = r.get('channel', 'unknown')
        ts = r.get('timestamp', '')[:19]
        content = r.get('content', '')[:300]
        lines.append(f"[{i}] {ts} | {sender} ({channel})")
        lines.append(f"    {content}")
        lines.append("")
    
    return "\n".join(lines)

def _format_stats(stats: Dict) -> str:
    """Format FTS5 stats as readable text."""
    lines = ["📊 FTS5 資料庫統計", ""]
    
    total = stats.get('total', 0)
    lines.append(f"總訊息數：{total:,}")
    
    channels = stats.get('channels', {})
    if isinstance(channels, dict) and channels:
        lines.append("\n各頻道訊息數：")
        for ch, count in sorted(channels.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"  • {ch}: {count:,}")
    elif isinstance(channels, int):
        lines.append(f"\n頻道數：{channels}")
    
    senders = stats.get('senders', 0)
    if isinstance(senders, int):
        lines.append(f"發送者數：{senders}")
    
    oldest = stats.get('oldest', '')
    newest = stats.get('newest', '')
    if oldest:
        lines.append(f"\n最舊訊息：{oldest[:19]}")
    if newest:
        lines.append(f"最新訊息：{newest[:19]}")
    
    db_path = stats.get('db_path', '')
    if db_path:
        import os
        size_mb = os.path.getsize(db_path) / (1024*1024) if os.path.exists(db_path) else 0
        lines.append(f"\n資料庫大小：{size_mb:.1f} MB")
    
    return "\n".join(lines)

# ── Protocol Dispatcher ──────────────────────────────────────

def dispatch(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Dispatch JSON-RPC request to appropriate handler."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    
    # Notification (no id) — handle for side effects, no reply
    if msg_id is None:
        return None
    
    if method == "initialize":
        return handle_initialize(msg_id)
    elif method == "tools/list":
        return handle_tools_list(msg_id)
    elif method == "tools/call":
        return handle_tools_call(msg_id, msg.get("params", {}))
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"method not found: {method}"}
        }

# ── Main Loop ───────────────────────────────────────────────

def main():
    # Send initial server info (optional but helpful for debugging)
    sys.stderr.write("[FTS5 MCP Server] Starting...\n")
    sys.stderr.flush()
    
    while True:
        msg = read_frame()
        if msg is None:
            break
        
        response = dispatch(msg)
        if response is not None:
            write_frame(response)

if __name__ == "__main__":
    main()