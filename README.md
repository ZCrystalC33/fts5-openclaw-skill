# FTS5 - Full-Text Search for OpenClaw

> 🤖 Make your AI assistant remember everything - with built-in Self-Improving intelligence.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.2.0-green.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)

**FTS5** indexes all your conversation history and generates smart LLM summaries. Includes built-in **Self-Improving** integration for automatic learning from corrections and patterns.

[English README](README_EN.md) | [繁體中文說明](README_ZH.md) | [更新日誌](CHANGELOG.md)

## ⚡ Quick Start

```bash
# Install (includes FTS5 + Self-Improving)
git clone https://github.com/ZCrystalC33/fts5-openclaw-skill.git ~/.openclaw/skills/fts5

# Configure
cp ~/.openclaw/skills/fts5/config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # Add MINIMAX_API_KEY

# Setup wizard
python3 ~/.openclaw/skills/fts5/setup.py

# Restart
openclaw gateway restart
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Full-Text Search** | Instant search across all conversations |
| 🤖 **LLM Summaries** | Auto-generated in your language |
| 🌐 **Multi-Language** | zh-TW, zh-CN, en, ja |
| 🧠 **Self-Improving** | Learn from corrections, track patterns |
| 🔄 **Auto-Index** | Cron-based incremental updates |
| ⚡ **Rate Limiting** | 30 calls/min |
| 🛡️ **Error Recovery** | 3-layer fallback |

## 📦 What's Included

### FTS5 (Search & Summarize)
```
fts5/fts5/
├── __init__.py              # Main search API
├── llm_summary.py            # LLM + multi-language
├── rate_limiter.py           # 30 calls/min
├── error_handling.py         # 3-layer fallback
├── indexer.py               # Session indexer
├── setup.py                  # Interactive wizard
└── install.py                # Cron hook installer
```

### Self-Improving (Learn & Improve)
```
fts5/self_improving/
├── memory.md                 # Hot layer (always loaded)
├── corrections.md            # Corrections log
├── index.md                  # Auto-generated index
├── heartbeat-state.md        # Heartbeat tracking
├── domains/                 # Topic learnings
│   └── openclaw-fts5.md
└── scripts/                  # Enhancement modules
    ├── context_predictor.py   # P1: Context prediction
    ├── reindex.py            # P1: Auto-index
    ├── exchange_engine.py     # P2: Cold/Hot layers
    └── fts5_integration.py   # P3: Bidirectional sync
```

## 💬 Usage

### FTS5 Search
```python
from skills.fts5 import search, summarize

results = search("上次討論的 FTS5", limit=5)
result = summarize("上次討論的內容")
print(result['summary'])
```

### Self-Improving Integration
```python
# Context-aware memory loading
from skills.fts5.self_improving.scripts.context_predictor import analyze_text
analysis = analyze_text("上次我們談的 FTS5")
# Returns: topics, intents, suggested_memory_load

# Index corrections to FTS5
from skills.fts5.self_improving.scripts.fts5_integration import index_correction
index_correction("User corrected my API key format understanding")
```

## 🔧 Configuration

```bash
# Environment variable (recommended)
export MINIMAX_API_KEY=sk-cp-your-key

# Or config file
echo "MINIMAX_API_KEY=sk-cp-your-key" > ~/.openclaw/fts5.env
```

## 🧠 Self-Improving Features

| Feature | Description |
|---------|-------------|
| **Context Predictor** | Analyzes text, suggests memory files to load |
| **Cold/Hot Exchange** | Auto-promotes/demotes based on activity |
| **FTS5 Integration** | Bidirectional sync - corrections searchable |

### Layer Exchange Rules
| Layer | Location | Trigger |
|-------|----------|---------|
| HOT | memory.md | < 7 days referenced |
| WARM | domains/ | 3+ references, not hot |
| COLD | archive/ | 30+ days unreferenced |

## 📁 Files

- [README_EN.md](README_EN.md) - English documentation
- [README_ZH.md](README_ZH.md) - 繁體中文說明
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [LICENSE](LICENSE) - MIT License

## 🛡️ Security

- ✅ No hardcoded API keys
- ✅ User-provided credentials only
- ✅ Sensitive data auto-masked
- ✅ Private config (600 permissions)

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

**Made by Ophelia Prime**

[GitHub](https://github.com/ZCrystalC33/fts5-openclaw-skill) | [Report Issue](https://github.com/ZCrystalC33/fts5-openclaw-skill/issues)