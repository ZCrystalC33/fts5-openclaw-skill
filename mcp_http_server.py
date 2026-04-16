#!/usr/bin/env python3
"""
FTS5 MCP Server - HTTP Transport Version
Exposes FTS5 search/summarize/stats over HTTP POST endpoint.

This is more reliable than stdio for OpenClaw MCP integration.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List

# ── FTS5 Import ──────────────────────────────────────────────

import importlib.util
import pathlib

_FTS5_PATH = pathlib.Path(__file__).parent

def _import_fts5():
    spec = importlib.util.spec_from_file_location(
        "fts5_module", 
        _FTS5_PATH / "__init__.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_fts5 = _import_fts5()

search = _fts5.search
summarize = _fts5.summarize
get_stats = _fts5.get_stats

# ── MCP Protocol Constants ──────────────────────────────────

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "fts5"
SERVER_VERSION = "1.5.0"

# ── Tool Definitions ──────────────────────────────────────────

TOOLS = [
    {
        "name": "fts5_search",
        "description": "Search conversation history stored in FTS5. Returns matching messages with sender, timestamp, and channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in natural language"},
                "limit": {"type": "integer", "default": 5, "description": "Maximum number of results to return"}
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
                "query": {"type": "string", "description": "Search query in natural language"},
                "limit": {"type": "integer", "default": 5, "description": "Number of messages to analyze for summary"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "fts5_stats",
        "description": "Get FTS5 database statistics: total messages indexed, message count per channel, database size.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

# ── Request Handlers ─────────────────────────────────────────

def handle_initialize(params: Dict) -> Dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "description": "OpenClaw FTS5 conversation search and LLM summarization"
        }
    }

def handle_tools_list() -> Dict:
    return {"tools": TOOLS}

def handle_tools_call(tool_name: str, arguments: Dict) -> Dict:
    try:
        if tool_name == "fts5_search":
            results = search(query=arguments.get("query", ""), limit=arguments.get("limit", 5))
            output = _format_search_results(results)
            return {"content": [{"type": "text", "text": output}]}
        
        elif tool_name == "fts5_summarize":
            search_results = search(query=arguments.get("query", ""), limit=arguments.get("limit", 5))
            summary = summarize(query=arguments.get("query", ""), search_results=search_results, limit=arguments.get("limit", 5))
            return {"content": [{"type": "text", "text": summary["summary"]}]}
        
        elif tool_name == "fts5_stats":
            stats = get_stats()
            output = _format_stats(stats)
            return {"content": [{"type": "text", "text": output}]}
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def _format_search_results(results: List[Dict]) -> str:
    if not results:
        return "No matching conversations found."
    lines = [f"找到 {len(results)} 筆記錄：\n"]
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
        size_mb = os.path.getsize(db_path) / (1024*1024) if os.path.exists(db_path) else 0
        lines.append(f"\n資料庫大小：{size_mb:.1f} MB")
    return "\n".join(lines)

# ── HTTP Handler ─────────────────────────────────────────────

class McpHttpHandler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        """Handle MCP JSON-RPC requests over HTTP."""
        if self.path != '/mcp':
            self.send_error(404, "Not Found")
            return
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        # Process method
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})
        
        try:
            if method == "initialize":
                result = handle_initialize(params)
            elif method == "tools/list":
                result = handle_tools_list()
            elif method == "tools/call":
                name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = handle_tools_call(name, arguments)
            else:
                error = {"code": -32601, "message": f"Method not found: {method}"}
                response = {"jsonrpc": "2.0", "id": msg_id, "error": error}
                self._send_json(response)
                return
            
            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        
        except Exception as e:
            response = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}
        
        self._send_json(response)
    
    def _send_json(self, obj: Dict):
        body = json.dumps(obj, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body.encode())
    
    def log_message(self, format, *args):
        pass  # Suppress request logging

# ── Main ─────────────────────────────────────────────────────

def main():
    port = 18795  # Use high port for FTS5 MCP HTTP
    server = HTTPServer(('127.0.0.1', port), McpHttpHandler)
    print(f"FTS5 MCP HTTP Server running on http://127.0.0.1:{port}/mcp", flush=True)
    sys.stdout.flush()
    server.serve_forever()

if __name__ == "__main__":
    main()