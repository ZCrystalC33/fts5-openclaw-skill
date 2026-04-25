"""
Honcho Client for PFSI Integration

Provides semantic search via Honcho + Ollama embeddings.
Documents are indexed into Honcho's vector store for semantic search,
while PFSI maintains FTS5 for fast keyword search.

Usage:
    from skills.fts5.honcho_client import HonchoClient
    
    hc = HonchoClient()
    hc.add_message("workspace", "assistant", "session-1", "今天天氣很好")
    results = hc.search("workspace", "assistant", "天氣")
"""

import os
import httpx
from typing import Optional

# ============================================================
# HONCHO CONFIG - From config.env or defaults
# ============================================================

HONCHO_BASE_URL = os.environ.get("HONCHO_BASE_URL", "http://localhost:8000")
HONCHO_WORKSPACE = os.environ.get("HONCHO_PFSI_WORKSPACE", "openclaw-pfsi")
HONCHO_ASSISTANT_PEER = "assistant"
HONCHO_USER_PEER = "user"

# ============================================================
# HTTP CLIENT - Single client for connection pooling
# ============================================================

_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=HONCHO_BASE_URL, timeout=30.0)
    return _client

async def close_client():
    """Close the shared HTTP client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

# ============================================================
# HONCHO CLIENT CLASS
# ============================================================

class HonchoClient:
    """Client for Honcho semantic search API."""
    
    def __init__(self, base_url: str = HONCHO_BASE_URL):
        self.base_url = base_url
        self.workspace = HONCHO_WORKSPACE
    
    async def _ensure_workspace(self) -> bool:
        """Ensure OpenClaw workspace exists."""
        client = get_client()
        try:
            # Try to get workspace first
            resp = await client.get(f"/v3/workspaces/{self.workspace}")
            if resp.status_code == 200:
                return True
            
            # Create workspace if doesn't exist
            resp = await client.post("/v3/workspaces", json={
                "name": self.workspace,
                "namespace": "default"
            })
            return resp.status_code in (200, 201)
        except Exception:
            return False
    
    async def _ensure_peer(self, peer_name: str) -> bool:
        """Ensure peer exists in workspace."""
        client = get_client()
        try:
            resp = await client.get(f"/v3/workspaces/{self.workspace}/peers/{peer_name}")
            if resp.status_code == 200:
                return True
            
            resp = await client.post(f"/v3/workspaces/{self.workspace}/peers", json={
                "name": peer_name,
                "metadata": {}
            })
            return resp.status_code in (200, 201)
        except Exception:
            return False
    
    async def _ensure_session(self, session_name: str, peer_ids: list[str]) -> bool:
        """Ensure session exists in workspace."""
        client = get_client()
        try:
            resp = await client.get(f"/v3/workspaces/{self.workspace}/sessions/{session_name}")
            if resp.status_code == 200:
                return True
            
            resp = await client.post(f"/v3/workspaces/{self.workspace}/sessions", json={
                "name": session_name,
                "peer_ids": peer_ids
            })
            return resp.status_code in (200, 201)
        except Exception:
            return False
    
    async def initialize(self) -> bool:
        """Initialize workspace, peers, and sessions for PFSI."""
        await self._ensure_workspace()
        await self._ensure_peer(HONCHO_ASSISTANT_PEER)
        await self._ensure_peer(HONCHO_USER_PEER)
        await self._ensure_session("default", [HONCHO_ASSISTANT_PEER, HONCHO_USER_PEER])
        return True
    
    async def add_message(
        self,
        peer_name: str,
        session_name: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Add a message to Honcho for semantic indexing.
        
        Args:
            peer_name: "assistant" or "user"
            session_name: Session identifier
            content: Message content
            metadata: Optional metadata dict
        
        Returns:
            True if successful
        """
        client = get_client()
        try:
            # Ensure workspace and session exist
            await self._ensure_workspace()
            await self._ensure_peer(peer_name)
            await self._ensure_session(session_name, [HONCHO_ASSISTANT_PEER, HONCHO_USER_PEER])
            
            resp = await client.post(
                f"/v3/workspaces/{self.workspace}/sessions/{session_name}/messages",
                json={
                    "messages": [{
                        "content": content,
                        "peer_id": peer_name,
                        "metadata": metadata or {}
                    }]
                }
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"[HonchoClient] add_message failed: {e}")
            return False
    
    async def search(
        self,
        peer_name: str,
        query: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Search messages using semantic similarity.
        
        Args:
            peer_name: Peer to search within (assistant or user)
            query: Search query
            limit: Max results
        
        Returns:
            List of matching messages with score
        """
        client = get_client()
        try:
            resp = await client.post(
                f"/v3/workspaces/{self.workspace}/peers/{peer_name}/search",
                json={"query": query, "limit": limit}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Handle both list response and {"results": [...]} format
                if isinstance(data, list):
                    return data
                return data.get("results", data)
            
            # Fallback: try to extract from error detail
            return []
        except Exception as e:
            print(f"[HonchoClient] search failed: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if Honcho is reachable."""
        client = get_client()
        try:
            resp = await client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False


# ============================================================
# SYNC WRAPPER - For non-async contexts
# ============================================================

def search_sync(query: str, peer: str = HONCHO_ASSISTANT_PEER, limit: int = 10) -> list[dict]:
    """Synchronous wrapper for search."""
    import asyncio
    
    async def _search():
        hc = HonchoClient()
        return await hc.search(peer, query, limit)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, can't use this wrapper
            return []
        return asyncio.run(_search())
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(_search())
