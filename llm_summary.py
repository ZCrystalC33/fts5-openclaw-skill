"""
FTS5 + LLM Summary Module
Combines FTS5 search with MiniMax LLM summarization.
Optimized prompts for different query types and languages.
Three-layer error handling with exponential backoff.
"""

import urllib.request
import json
import os
import time
import re
import logging
from typing import Dict, List, Any, Optional
from skills.fts5.error_handling import (
    RateLimitError, APITimeoutError, APIServerError, NetworkError,
    simple_template_summary, format_fallback_response, categorize_error
)

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.minimax.io/anthropic/v1/messages"
MODEL = "MiniMax-M2.7"
TIMEOUT_SECONDS = 30


def _get_api_key() -> str:
    """
    Get API key from environment or config file.
    Does NOT hardcode any key.
    """
    # Environment variable
    api_key = os.environ.get("MINIMAX_API_KEY")
    if api_key:
        return api_key
    
    # Config file
    setup_file = os.path.expanduser("~/.openclaw/fts5.env")
    if os.path.exists(setup_file):
        with open(setup_file, 'r') as f:
            for line in f:
                if line.startswith("MINIMAX_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "sk-cp-YOUR_KEY_HERE":
                        return key
    
    # Config.json fallback
    config_file = os.path.expanduser("~/.openclaw/config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if "fts5" in config and config["fts5"].get("api_key"):
                    return config["fts5"]["api_key"]
        except:
            pass
    
    raise ValueError(
        "MINIMAX_API_KEY not configured. Please run:\n"
        "  python3 ~/.openclaw/skills/fts5/setup.py\n"
    )


# Rate limiting
MAX_CALLS_PER_MINUTE = 30
_rate_limiter_history: List[float] = []


def _check_rate_limit():
    """Check and enforce rate limiting."""
    global _rate_limiter_history
    now = time.time()
    
    # Clean old entries (older than 60 seconds)
    _rate_limiter_history = [t for t in _rate_limiter_history if now - t < 60]
    
    if len(_rate_limiter_history) >= MAX_CALLS_PER_MINUTE:
        oldest = _rate_limiter_history[0]
        wait_time = 60 - (now - oldest) + 1
        if wait_time > 0:
            time.sleep(wait_time)
        _rate_limiter_history = [t for t in _rate_limiter_history if now - t < 60]
    
    _rate_limiter_history.append(now)


# ============================================================
# EXPONENTIAL BACKOFF - From Task Decomposition Pattern
# ============================================================

MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds
BACKOFF_MULTIPLIER = 2


def _exponential_backoff(attempt: int, error_type: str) -> float:
    """
    Calculate exponential backoff wait time.
    
    Args:
        attempt: Current retry attempt (0-indexed)
        error_type: Type of error for adjusted wait times
    
    Returns:
        Wait time in seconds
    """
    base_wait = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
    
    # Adjust based on error type
    if error_type == "rate_limit":
        base_wait *= 2  # Longer wait for rate limits
    elif error_type == "timeout":
        base_wait *= 1  # Standard backoff for timeouts
    
    return min(base_wait, 60)  # Cap at 60 seconds


def call_llm_with_fallback(prompt: str, max_tokens: int = 500, system: Optional[str] = None) -> Dict[str, Any]:
    """
    Call MiniMax LLM API with three-layer error handling + exponential backoff.
    
    Returns:
        Dict with:
            - success: bool
            - text: str (response text if successful)
            - fallback: bool (whether fallback was used)
            - error: str (error message if failed)
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            text = _call_llm_internal(prompt, max_tokens, system)
            if attempt > 0:
                logger.info(f"LLM call succeeded on retry {attempt + 1}")
            return {
                "success": True,
                "text": text,
                "fallback": False,
                "error": None
            }
        
        except RateLimitError as e:
            error_type = "rate_limit"
            last_error = e
            logger.warning(f"Rate limit error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        
        except APITimeoutError as e:
            error_type = "timeout"
            last_error = e
            logger.warning(f"Timeout error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        
        except APIServerError as e:
            error_type = "server_error"
            last_error = e
            logger.warning(f"Server error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        
        except NetworkError as e:
            error_type = "network"
            last_error = e
            logger.error(f"Network error: {e}")
            # Don't retry network errors with backoff
            break
        
        except Exception as e:
            error_type = "unknown"
            last_error = e
            logger.error(f"Unexpected error (attempt {attempt + 1}/{MAX_RETRIES}): {type(e).__name__}: {e}")
        
        # Exponential backoff before next retry
        if attempt < MAX_RETRIES - 1:
            wait_time = _exponential_backoff(attempt, error_type)
            logger.info(f"Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    # All retries exhausted
    error_msg = str(last_error) if last_error else "Unknown error"
    return {
        "success": False,
        "text": None,
        "fallback": True,
        "error": error_msg
    }


def _call_llm_internal(prompt: str, max_tokens: int = 500, system: Optional[str] = None) -> str:
    """
    Internal LLM API call - raises specific exceptions on errors.
    """
    # Rate limit check
    _check_rate_limit()
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages
    }
    
    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
        "x-api-key": _get_api_key(),
        "anthropic-version": "2023-06-01"
    }
    
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read())
        content = result.get('content', [])
        for item in content:
            if item.get('type') == 'text':
                return item['text']
    return ""


# Optimized prompts for different query types and languages
PROMPTS = {
    "default": {
        "zh-TW": """你是一個聰明的 AI 助理，正在幫用戶總結對話歷史。

請根據以下搜尋結果，總結用戶感興趣的主題。重點包括：
- 用戶討論的核心內容
- 重要的結論或決定
- 未解決的問題或後續行動

搜尋關鍵詞：「{query}」

---
{context}
---

請用繁體中文回答，總結要點，保持脈絡清晰。""",

        "zh-CN": """你是一个聪明的 AI 助理，正在帮用户总结对话历史。

请根据以下搜索结果，总结用户感兴趣的主题。重点包括：
- 用户讨论的核心内容
- 重要的结论或决定
- 未解决的问题或后续行动

搜索关键词：「{query}」

---
{context}
---

请用简体中文回答，总结要点，保持脉络清晰。""",

        "en": """You are an intelligent AI assistant summarizing conversation history.

Based on the search results below, summarize topics of user interest:
- Core topics discussed
- Important conclusions or decisions
- Unresolved issues or follow-up actions

Search keywords: "{query}"

---
{context}
---

Please respond in English, summarize key points clearly."""
    },

    "technical": {
        "zh-TW": """你是一個專業的技術顧問，正在幫用戶回顧技術相關的討論。

請根據以下對話歷史，總結技術要點：
- 涉及的技術主題和工具
- 已解決的問題和方案
- 未解決的技術難題
- 建議的下一步

技術關鍵詞：「{query}」

---
{context}
---

請用繁體中文回答，技術術語請保持英文原文，條理分明。""",

        "zh-CN": """你是一个专业的技术顾问，正在帮用户回顾技术相关的讨论。

请根据以下对话历史，总结技术要点：
- 涉及的技术主题和工具
- 已解决的问题和方案
- 未解决的技术难题
- 建议的下一步

技术关键词：「{query}」

---
{context}
---

请用简体中文回答，技术术语请保持英文原文，条理分明。""",

        "en": """You are a professional technical consultant reviewing technical discussions.

Based on the conversation history below, summarize technical points:
- Technical topics and tools involved
- Problems solved and solutions implemented
- Unresolved technical issues
- Recommended next steps

Technical keywords: "{query}"

---
{context}
---

Please respond in English, keeping technical terms in their original form, well-organized."""
    },

    "status": {
        "zh-TW": """你是一個項目助理，正在幫用戶回顧專案狀態。

請根據以下對話，總結專案進度：
- 目前進度狀態
- 已完成的事項
- 進行的障礙或問題
- 接下來的計畫

專案關鍵詞：「{query}」

---
{context}
---

請用繁體中文回答，格式清晰，適合快速了解狀態。""",

        "zh-CN": """你是一个项目助理，正在帮用户回顾项目状态。

请根据以下对话，总结项目进度：
- 目前进度状态
- 已完成的事项
- 进行的障碍或问题
- 接下来的计划

项目关键词：「{query}」

---
{context}
---

请用简体中文回答，格式清晰，适合快速了解状态。""",

        "en": """You are a project assistant helping the user review project status.

Based on the conversations below, summarize project progress:
- Current progress status
- Completed items
- Obstacles or issues encountered
- Next steps

Project keywords: "{query}"

---
{context}
---

Please respond in English, with clear formatting suitable for quick status overview."""
    },

    "preference": {
        "zh-TW": """你是一個個人助理，正在幫用戶回顧個人偏好和設定。

請根據以下對話，總結用戶的偏好：
- 明確表示的喜好
- 設定的選項或配置
- 特殊的習慣或要求
- 需要記住的重要事項

偏好關鍵詞：「{query}」

---
{context}
---

請用繁體中文回答，總結事項請分條列點。""",

        "zh-CN": """你是一个个人助理，正在帮用户回顾个人偏好和设定。

请根据以下对话，总结用户的偏好：
- 明确表示的喜好
- 设定的选项或配置
- 特殊的习惯或要求
- 需要记住的重要事项

偏好关键词：「{query}」

---
{context}
---

请用简体中文回答，总结事项请分条列点。""",

        "en": """You are a personal assistant helping the user review personal preferences and settings.

Based on the conversations below, summarize user preferences:
- Clearly stated preferences
- Configured options or settings
- Special habits or requirements
- Important things to remember

Preference keywords: "{query}"

---
{context}
---

Please respond in English, with items listed clearly."""
    }
}


def detect_language(text: str) -> str:
    """
    Detect the language of input text.
    Supports: zh-TW (Traditional Chinese), zh-CN (Simplified Chinese), en (English), ja (Japanese)
    
    Returns language code: 'zh-TW', 'zh-CN', 'en', 'ja', or 'default' (zh-TW)
    """
    if not text:
        return "zh-TW"
    
    # Japanese detection (before Chinese to avoid misdetection)
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "ja"
    
    # Chinese detection - look for Chinese characters
    if re.search(r'[\u4e00-\u9fff]', text):
        # Characters that clearly indicate Simplified Chinese
        simp_only = set('简体系发龙经国时对会那在能但还来已'.replace('', ' '))
        # Characters that clearly indicate Traditional Chinese
        trad_only = set('簡體繫發龍經國時對會那在能但還來已'.replace('', ' '))
        
        text_set = set(text)
        simp_matches = len(text_set & simp_only)
        trad_matches = len(text_set & trad_only)
        
        if simp_matches > trad_matches:
            return "zh-CN"
        elif trad_matches > simp_matches:
            return "zh-TW"
        else:
            # Fallback: check for other common differentiators
            # "开" (simplified) vs "開" (traditional)
            if '开' in text:
                return "zh-CN"
            elif '開' in text:
                return "zh-TW"
            # "关" (simplified) vs "關" (traditional)
            elif '关' in text:
                return "zh-CN"
            elif '關' in text:
                return "zh-TW"
            # Default to Traditional
            return "zh-TW"
    
    # Default to English for other languages
    return "en"


def _detect_query_type(query: str, results: List[Dict]) -> str:
    """Detect what type of query this is for optimal prompt selection."""
    query_lower = query.lower()
    
    # Technical keywords
    tech_keywords = ['python', 'code', 'api', '安裝', '設定', 'config', 'docker', 'git', 'sql', 'database', '程式']
    if any(kw in query_lower for kw in tech_keywords):
        return "technical"
    
    # Status keywords
    status_keywords = ['現在怎麼樣', '進度', '狀態', '結果', '完成了', '進展', 'status', 'progress']
    if any(kw in query_lower for kw in status_keywords):
        return "status"
    
    # Preference keywords
    pref_keywords = ['喜歡', '偏好', '設定', '配置', '習慣', 'prefer', '設定', '要', '不要']
    if any(kw in query_lower for kw in pref_keywords):
        return "preference"
    
    return "default"


def summarize_conversations(query: str, search_results: List[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
    """
    Take FTS5 search results and generate an LLM summary.
    
    Args:
        query: The original search query
        search_results: List of dicts with 'content', 'timestamp', 'sender', 'channel'
        limit: Max number of results to include in context
    
    Returns:
        Dict with 'summary', 'references', 'query'
    """
    if not search_results:
        return {
            "summary": "找不到相關對話記錄。你可以問我更具體的主題，比如「我們上次談的 Discord Bot」或「FTS5 系統」",
            "references": [],
            "query": query
        }
    
    # Detect query type and language for optimal prompt
    query_type = _detect_query_type(query, search_results)
    language = detect_language(query)
    
    # Get prompt template with language support
    query_prompts = PROMPTS.get(query_type, PROMPTS["default"])
    if isinstance(query_prompts, dict):
        # Multi-language prompts
        prompt_template = query_prompts.get(language, query_prompts.get("zh-TW"))
    else:
        # Legacy single-language prompts (fallback)
        prompt_template = query_prompts
    
    # Build context from search results
    context_parts = []
    for i, r in enumerate(search_results[:limit]):
        sender = r.get('sender', 'unknown')
        channel = r.get('channel', 'unknown')
        timestamp = r.get('timestamp', '')[:19]
        content = r.get('content', '')[:800]  # Truncate long messages
        context_parts.append(f"[{i+1}] [{timestamp}] {sender}: {content}")
    
    context = "\n\n".join(context_parts)
    
    # Format prompt
    prompt = prompt_template.format(query=query, context=context)
    
    system_prompt = """你是一個有用的助手，擅長總結對話內容。請簡潔明瞭地回覆。"""
    
    # Use error-handled LLM call (now with exponential backoff)
    result = call_llm_with_fallback(prompt, max_tokens=600, system=system_prompt)
    
    if result["success"]:
        return {
            "summary": result["text"],
            "references": [
                {
                    "content": r.get('content', '')[:200] + "...",
                    "timestamp": r.get('timestamp', ''),
                    "sender": r.get('sender', ''),
                    "channel": r.get('channel', '')
                }
                for r in search_results[:limit]
            ],
            "query": query,
            "query_type": query_type,
            "language": language,
            "total_found": len(search_results),
            "fallback": result["fallback"]
        }
    else:
        # Fallback to simple template
        logger.warning(f"LLM call failed, using fallback: {result['error']}")
        fallback_text = simple_template_summary(search_results)
        return {
            "summary": fallback_text,
            "references": [
                {
                    "content": r.get('content', '')[:200] + "...",
                    "timestamp": r.get('timestamp', ''),
                    "sender": r.get('sender', ''),
                    "channel": r.get('channel', '')
                }
                for r in search_results[:limit]
            ],
            "query": query,
            "query_type": query_type,
            "language": language,
            "total_found": len(search_results),
            "fallback": True,
            "fallback_reason": result["error"]
        }


# Quick test
if __name__ == "__main__":
    print("🧪 Testing optimized LLM summary module...")
    
    test_results = [
        {
            "content": "技術問題：Python 3.12 安裝成功",
            "timestamp": "2026-04-16T10:00:00",
            "sender": "user",
            "channel": "telegram"
        },
        {
            "content": "回答：很好，Python 版本正確",
            "timestamp": "2026-04-16T10:01:00",
            "sender": "assistant",
            "channel": "telegram"
        }
    ]
    
    print(f"Query type detection: {_detect_query_type('Python 安裝', test_results)}")
    result = summarize_conversations("Python 安裝", test_results)
    print(f"\n📝 Summary: {result['summary']}")
    print(f"📊 Total found: {result['total_found']}")
