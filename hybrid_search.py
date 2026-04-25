"""
Hybrid Search for PFSI

Combines FTS5 (keyword) + Honcho (semantic) search.
FTS5 is primary for speed, Honcho provides semantic fallback.

Usage:
    from skills.fts5.hybrid_search import hybrid_search
    
    results = await hybrid_search("天氣", limit=10)
"""

import asyncio
from typing import List, Dict, Any, Optional

from skills.fts5 import search as fts5_search, search_async

from .honcho_client import HonchoClient, HONCHO_ASSISTANT_PEER

# ============================================================
# HYBRID SEARCH CONFIG
# ============================================================

HONCHO_FALLBACK_THRESHOLD = 3
FTS5_BOOST = 1.5


def _merge_results(
    fts5: List[Dict[str, Any]],
    semantic: List[Dict[str, Any]],
    fts5_weight: float,
    semantic_weight: float,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Merge FTS5 and semantic results using weighted scoring."""
    seen_ids = set()
    merged = []
    
    fts5_index = 0
    semantic_index = 0
    fts5_len = len(fts5)
    semantic_len = len(semantic)
    
    while len(merged) < (fts5_len + semantic_len) and len(merged) < limit * 2:
        if fts5_index < fts5_len:
            fts5_item = fts5[fts5_index]
            fts5_id = fts5_item.get("message_id") or fts5_item.get("id")
            if fts5_id not in seen_ids:
                score = fts5_weight * (1 - fts5_index / max(fts5_len, 1))
                fts5_item["_search_score"] = score
                fts5_item["_search_source"] = "fts5"
                merged.append(fts5_item)
                seen_ids.add(fts5_id)
            fts5_index += 1
        
        if semantic_index < semantic_len:
            semantic_item = semantic[semantic_index]
            semantic_id = semantic_item.get("id")
            if semantic_id not in seen_ids:
                score = semantic_weight * (1 - semantic_index / max(semantic_len, 1))
                semantic_item["_search_score"] = score
                semantic_item["_search_source"] = "semantic"
                merged.append(semantic_item)
                seen_ids.add(semantic_id)
            semantic_index += 1
    
    merged.sort(key=lambda x: x.get("_search_score", 0), reverse=True)
    
    return merged[:limit]


async def hybrid_search(
    query: str,
    limit: int = 10,
    channel: Optional[str] = None,
    use_semantic: bool = True,
    fts5_weight: float = 0.6,
    semantic_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid search combining FTS5 (keyword) + Honcho (semantic).
    
    Strategy:
    1. Run FTS5 search (fast, keyword-based)
    2. If FTS5 returns < HONCHO_FALLBACK_THRESHOLD results, run Honcho search
    3. Merge results with weighted scoring
    """
    fts5_results = await search_async(query, limit=limit * 2, channel=channel)
    
    if not use_semantic or len(fts5_results) >= HONCHO_FALLBACK_THRESHOLD:
        return fts5_results[:limit]
    
    hc = HonchoClient()
    
    if not await hc.health_check():
        return fts5_results[:limit]
    
    try:
        semantic_results = await asyncio.wait_for(
            hc.search(HONCHO_ASSISTANT_PEER, query, limit=limit * 2),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        semantic_results = []
    except Exception as e:
        print(f"[HybridSearch] Honcho search failed: {e}")
        semantic_results = []
    
    if not semantic_results:
        return fts5_results[:limit]
    
    return _merge_results(fts5_results, semantic_results, fts5_weight, semantic_weight, limit)


async def search_with_honcho(
    query: str,
    limit: int = 10,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search that returns both FTS5 and Honcho results separately.
    
    Returns:
        Dict with "fts5" and "honcho" keys
    """
    fts5_results = await search_async(query, limit=limit, channel=channel)
    
    hc = HonchoClient()
    honcho_results = []
    
    if await hc.health_check():
        try:
            honcho_results = await asyncio.wait_for(
                hc.search(HONCHO_ASSISTANT_PEER, query, limit=limit),
                timeout=5.0
            )
        except (asyncio.TimeoutError, Exception):
            pass
    
    return {
        "fts5": fts5_results,
        "honcho": honcho_results,
        "fts5_count": len(fts5_results),
        "honcho_count": len(honcho_results),
    }
