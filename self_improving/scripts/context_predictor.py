#!/usr/bin/env python3
"""
Context Predictor for Self-Improving
Analyzes recent conversation context to predict likely user needs.
"""

import os
import re
import sys
from typing import Dict, List, Optional

# Context trigger patterns
CONTEXT_TRIGGERS = {
    "openclaw": {
        "keywords": ["openclaw", "open claw", "技能", "agent"],
        "memory_hint": "OpenClaw 框架與技能開發"
    },
    "fts5": {
        "keywords": ["fts5", "搜尋", "歷史", "上次", "全文", "search"],
        "memory_hint": "FTS5 系統架構與優化"
    },
    "github": {
        "keywords": ["github", "git clone", "push", "repo", "repository"],
        "memory_hint": "GitHub 操作與 Repo 管理"
    },
    "python": {
        "keywords": ["python", "安裝", "套件", "pip", "import"],
        "memory_hint": "Python 開發與除錯"
    },
    "api": {
        "keywords": ["api", "key", "token", "endpoint", "請求"],
        "memory_hint": "API 整合與金鑰管理"
    },
    "docker": {
        "keywords": ["docker", "container", "image", "containerized"],
        "memory_hint": "Docker 容器化部署"
    },
    "trade": {
        "keywords": ["freqtrade", "交易", "策略", "量化", "crypto"],
        "memory_hint": "量化交易策略"
    },
    "chinese": {
        "keywords": ["繁體", "中文", "台灣", "Taiwan"],
        "memory_hint": "繁體中文使用者偏好"
    }
}

# User intent patterns
INTENT_PATTERNS = {
    "explanation": {
        "patterns": ["什麼是", "怎麼", "如何", "為什麼", "why", "how", "what is"],
        "memory_type": "concept"
    },
    "task": {
        "patterns": ["幫我", "做", "執行", "build", "create", "do", "make"],
        "memory_type": "task"
    },
    "correction": {
        "patterns": ["不對", "錯誤", "應該", "wrong", "incorrect", "should"],
        "memory_type": "correction"
    },
    "status": {
        "patterns": ["怎麼樣", "狀態", "進度", "status", "progress", "how's"],
        "memory_type": "status_check"
    },
    "history": {
        "patterns": ["上次", "之前", "曾經", "last time", "before", "previously"],
        "memory_type": "context_recall"
    }
}


def analyze_text(text: str, include_fts5_context: bool = False) -> Dict:
    """
    Analyze text and return contextual predictions.
    
    Returns:
        dict with keys: topics, intents, suggested_memory_load
    """
    if not text:
        return {"topics": [], "intents": [], "suggested_memory_load": []}
    
    text_lower = text.lower()
    
    # Detect topics
    detected_topics = []
    for topic, config in CONTEXT_TRIGGERS.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                detected_topics.append({
                    "topic": topic,
                    "hint": config["memory_hint"]
                })
                break
    
    # Detect intents
    detected_intents = []
    for intent, config in INTENT_PATTERNS.items():
        for pattern in config["patterns"]:
            if pattern in text_lower:
                detected_intents.append({
                    "intent": intent,
                    "memory_type": config["memory_type"]
                })
                break
    
    # Build memory load suggestion
    suggested_memory_load = []
    
    # Try to import FTS5 integration
    FTS5_INTEGRATION_AVAILABLE = False
    try:
        sys.path.insert(0, os.path.expanduser("~/self-improving/scripts"))
        import fts5_integration
        FTS5_INTEGRATION_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        pass
    
    # If history intent, suggest FTS5
    if any(i["intent"] == "history" for i in detected_intents):
        suggested_memory_load.append("fts5:recent_conversations")
    
    # If correction intent, note for corrections log
    if any(i["intent"] == "correction" for i in detected_intents):
        suggested_memory_load.append("corrections:log_this")
    
    # Add topic-specific memory hints
    for topic_info in detected_topics:
        suggested_memory_load.append(f"domains/{topic_info['topic']}")
    
    return {
        "topics": detected_topics,
        "intents": detected_intents,
        "suggested_memory_load": suggested_memory_load
    }


def predict_next_action(current_context: str) -> Optional[str]:
    """
    Predict what the user might want to do next.
    
    Args:
        current_context: Latest user message or conversation summary
        
    Returns:
        Suggested next action or None
    """
    analysis = analyze_text(current_context)
    
    # Simple rule-based predictions
    if not analysis["topics"] and not analysis["intents"]:
        return None
    
    # If user asks about something technical, suggest related topics
    if any(t["topic"] == "fts5" for t in analysis["topics"]):
        return "建議搜尋 FTS5 相關的歷史對話"
    
    if any(i["intent"] == "task" for i in analysis["intents"]):
        return "任務開始，記錄相關偏好於 memory.md"
    
    if any(i["intent"] == "correction" for i in analysis["intents"]):
        return "捕捉到修正，寫入 corrections.md 並評估是否更新 memory.md"
    
    return None


def get_memory_load_suggestions(text: str) -> List[str]:
    """
    Get which memory files should be loaded for this context.
    
    Returns:
        List of file paths or identifiers
    """
    analysis = analyze_text(text)
    return analysis["suggested_memory_load"]


def format_analysis_report(text: str) -> str:
    """
    Format analysis into a readable report.
    """
    analysis = analyze_text(text)
    
    lines = ["📊 Context Analysis Report"]
    lines.append("=" * 40)
    
    if analysis["topics"]:
        lines.append("\n🔍 Detected Topics:")
        for t in analysis["topics"]:
            lines.append(f"  • {t['topic']}: {t['hint']}")
    else:
        lines.append("\n🔍 Topics: None detected")
    
    if analysis["intents"]:
        lines.append("\n🎯 Detected Intents:")
        for i in analysis["intents"]:
            lines.append(f"  • {i['intent']} ({i['memory_type']})")
    else:
        lines.append("\n🎯 Intents: None detected")
    
    if analysis["suggested_memory_load"]:
        lines.append("\n💡 Suggested Memory Load:")
        for m in analysis["suggested_memory_load"]:
            lines.append(f"  → {m}")
    
    return "\n".join(lines)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    test_text = sys.argv[1] if len(sys.argv) > 1 else "我想了解 FTS5 的使用方法"
    
    print(f"Input: {test_text}")
    print()
    print(format_analysis_report(test_text))
    print()
    print(f"Predicted next action: {predict_next_action(test_text)}")
    print(f"Suggested memory load: {get_memory_load_suggestions(test_text)}")