# FTS5 - Full-Text Search for OpenClaw

SQLite FTS5 full-text search with LLM-powered summarization for OpenClaw conversations.

[中文說明](./README_zh.md)

## 🎯 What is FTS5?

FTS5 enables your OpenClaw AI assistant to search and summarize past conversations. It uses SQLite's FTS5 (Full-Text Search) engine to index messages and combines with LLM (MiniMax) to generate meaningful summaries.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Full-Text Search** | Instant search across all conversation history |
| 🤖 **LLM Summarization** | Automatic summary generation in your language |
| 🌍 **Multi-Language** | Supports zh-TW, zh-CN, en, ja |
| 🔒 **Sensitive Data Filter** | Auto-masks API keys, tokens, private keys |
| ⚡ **Rate Limiting** | Protects API (10 calls/min max) |
| 🛡️ **Error Recovery** | 3-layer fallback on API failure |
| 📊 **Smart Context** | Auto-adjusts based on query complexity |
| 🔄 **Incremental Indexing** | Only processes changed session files |

## 📦 Installation

### Prerequisites

- Python 3.7+
- SQLite3 (built into Python)
- MiniMax API Key ([Get one here](https://platform.minimax.io/))

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/kiwi760303/fts5-openclaw-skill.git ~/.openclaw/skills/fts5

# 2. Copy and edit configuration
cp ~/.openclaw/skills/fts5/config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # Add your MINIMAX_API_KEY

# 3. Run onboarding (recommended)
python3 ~/.openclaw/skills/fts5/setup.py

# 4. Index existing conversations (optional)
python3 ~/.openclaw/skills/fts5/indexer.py
```

## ⚙️ Configuration

### API Key Setup

**Option A: Environment Variable (Recommended)**
```bash
export MINIMAX_API_KEY=sk-cp-your-key-here
```

**Option B: Config File**
```bash
# Edit ~/.openclaw/fts5.env
MINIMAX_API_KEY=sk-cp-your-key-here
```

### Priority Order
1. `MINIMAX_API_KEY` environment variable
2. `~/.openclaw/fts5.env` config file  
3. `~/.openclaw/config.json` (fts5.api_key)

## 🚀 Quick Usage

```python
# Simple search
from skills.fts5 import search, summarize

# Search for messages
results = search("Discord Bot", limit=5)

# LLM-powered summary
result = summarize("上次討論的內容")
print(result['summary'])

# Get statistics
from skills.fts5 import get_stats
stats = get_stats()
print(f"Total messages: {stats['total']}")
```

## 🔧 Module Reference

| Function | Description |
|----------|-------------|
| `search(query, limit)` | FTS5 full-text search |
| `summarize(query, limit)` | Search + LLM summary |
| `add_message(...)` | Add message to index |
| `get_recent(limit)` | Get recent messages |
| `get_stats()` | Database statistics |

## 🌐 Multi-Language Support

FTS5 auto-detects your query language and uses appropriate prompts:

| Language | Code | Detection |
|----------|------|-----------|
| 繁體中文 | `zh-TW` | 開/龍/體 characters |
| 簡體中文 | `zh-CN` | 开/龙/体 characters |
| English | `en` | Default |
| 日本語 | `ja` | Hiragana/Katakana |

## 🛡️ Error Handling

FTS5 has 3-layer error recovery:

1. **Normal**: Try LLM API call
2. **Retry**: Wait 5-10s and retry once
3. **Fallback**: Use template-based summary

No API key? Shows setup instructions instead of crashing.

## 📁 File Structure

```
fts5/
├── __init__.py           # Main module
├── llm_summary.py         # LLM + multi-language prompts
├── rate_limiter.py        # 10 calls/min limit
├── error_handling.py      # 3-layer fallback
├── indexer.py             # Session indexer
├── sensitive_filter.py    # Data masking
├── setup.py               # Onboarding wizard
├── config.env.example     # Example config
├── SKILL.md              # OpenClaw skill file
└── README.md             # This file
```

## 🔒 Security

- **No hardcoded credentials** - All API keys are user-provided
- **Sensitive data masking** - Auto-hides API keys, tokens, private keys
- **Incremental indexing** - Only processes new/modified files

## 📄 License

MIT License - See [LICENSE](./LICENSE) file.

## 🐛 Troubleshooting

**"MINIMAX_API_KEY not found"**
```bash
python3 ~/.openclaw/skills/fts5/setup.py
```

**"API connection failed"**
1. Check your API key is correct
2. Verify internet connection
3. Run setup to test: `python3 ~/.openclaw/skills/fts5/setup.py`

## 🙏 Acknowledgments

- Built for [OpenClaw](https://github.com/openclaw/openclaw) AI assistant framework
- Uses [MiniMax](https://platform.minimax.io/) for LLM capabilities
- Powered by SQLite FTS5 full-text search engine

---

**Version:** 1.2.0  
**Last Updated:** 2026-04-16