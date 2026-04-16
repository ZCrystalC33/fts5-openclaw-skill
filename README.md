# FTS5 - OpenClaw 對話歷史搜尋系統

> 🤖 讓你的 AI 助理記住一切 — 內建 Self-Improving 智慧學習。
> 
> 🤖 Make your AI assistant remember everything — with built-in Self-Improving intelligence.

[![授權：MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![版本](https://img.shields.io/badge/Version-1.2.0-green.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)

---

## 📌 語言切換 | Language Switch

- [中文說明](#-功能特色)（本頁）
- [English Documentation](#--features)（下方）

---

## 🔰 功能特色 | Features

| 功能 Feature | 說明 Description |
|--------------|-----------------|
| 🔍 **全文搜尋** | 跨所有對話即時搜尋 |
| 🔍 **Full-Text Search** | Instant search across all conversations |
| 🤖 **LLM 摘要** | 自動生成你語言的摘要 |
| 🤖 **LLM Summaries** | Auto-generated in your language |
| 🌐 **多語言** | 支援繁體中文、簡體中文、英文、日文 |
| 🌐 **Multi-Language** | zh-TW, zh-CN, en, ja |
| 🧠 **自我改進** | 從修正中學習，追蹤模式 |
| 🧠 **Self-Improving** | Learn from corrections, track patterns |
| 🔄 **自動索引** | Cron 增量更新 |
| 🔄 **Auto-Index** | Cron-based incremental updates |
| ⚡ **頻率限制** | 每分鐘 30 次 |
| ⚡ **Rate Limiting** | 30 calls/min |
| 🛡️ **錯誤恢復** | 三層 fallback |
| 🛡️ **Error Recovery** | 3-layer fallback |
| 🔒 **安全** | 無硬編碼 Key，資料自動遮罩 |
| 🔒 **Secure** | No hardcoded keys, data auto-masked |

---

## 🚀 快速開始 | Quick Start

```bash
# 1. 複製 | Clone
git clone https://github.com/ZCrystalC33/fts5-openclaw-skill.git ~/.openclaw/skills/fts5

# 2. 設定 | Configure
cp ~/.openclaw/skills/fts5/config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # 填入 MINIMAX_API_KEY | Add your MINIMAX_API_KEY

# 3. 安裝精靈 | Setup Wizard
python3 ~/.openclaw/skills/fts5/setup.py

# 4. 重啟 | Restart
openclaw gateway restart
```

---

## 📦 包含模組 | What's Included

### FTS5 核心 | FTS5 Core

| 檔案 File | 功能 Purpose |
|-----------|-------------|
| `__init__.py` | 主 API | Main API: `search()`, `summarize()`, `get_stats()` |
| `llm_summary.py` | LLM + 多語言 Prompt | LLM + multi-language prompts |
| `rate_limiter.py` | 每分鐘 30 次 | 30 calls/min sliding window |
| `error_handling.py` | 三層 Fallback | 3-layer fallback system |
| `indexer.py` | 對話索引器 | Session indexer with state tracking |
| `sensitive_filter.py` | API Key 遮罩 | API key / token masking |
| `setup.py` | 互動式安裝精靈 | Interactive setup wizard |
| `install.py` | Cron 鉤子安裝 | Cron hook installer |

### Self-Improving 整合 | Self-Improving Integration

| 檔案 File | 等級 Level | 功能 Purpose |
|-----------|------------|--------------|
| `context_predictor.py` | P1 | 分析文字 → 預測話題意圖 | Analyze text → predict topics/intents |
| `reindex.py` | P1 | 自動更新索引 | Auto-update `index.md` |
| `exchange_engine.py` | P2 | 冷/熱層自動交換 | Cold/Hot layer auto-exchange |
| `exchange-cron.sh` | P2 | Cron 鉤子（每天 3 AM）| Cron hook (3 AM daily) |
| `fts5_integration.py` | P3 | 雙向同步 | Bidirectional FTS5 ↔ memory sync |

---

## 💬 使用方式 | Usage

### FTS5 搜尋 | FTS5 Search

```python
from skills.fts5 import search, summarize, get_stats

# 搜尋 | Search
results = search("FTS5", limit=5)

# LLM 摘要 | LLM Summary
result = summarize("上次討論的內容")
print(result['summary'])

# 統計 | Stats
print(get_stats())
```

### 上下文預測 | Context Prediction

```python
from skills.fts5.self_improving.scripts.context_predictor import analyze_text

analysis = analyze_text("上次我們談的 FTS5")
print(analysis['topics'])       # [{'topic': 'fts5', ...}]
print(analysis['suggested_memory_load'])  # ['fts5:recent', 'domains/fts5']
```

---

## 🧠 層級規則 | Layer Rules

| 層級 Layer | 位置 Location | 條件 Trigger |
|------------|---------------|--------------|
| **熱 Hot** | `memory.md` | 7 天內引用 | < 7 days referenced |
| **溫 Warm** | `domains/` | 3+ 引用 | 3+ references |
| **冷 Cold** | `archive/` | 30+ 天未引用 | 30+ days unreferenced |

---

## 📍 安裝位置優先權 | Installation Priority

腳本自動偵測並使用**現有的** Self-Improving 安裝位置。

Scripts automatically detect and use the **existing** Self-Improving installation.

| 優先 Priority | 位置 Location | 情境 When |
|---------------|--------------|-----------|
| 1st | `~/self-improving/` | 已安裝過 | Already installed |
| 2nd | `~/.openclaw/skills/fts5/self_improving/` | 全新安裝 | New installation |

---

## ⚙️ Cron 自動化 | Cron Automation

| 任務 Task | 頻率 Frequency | 指令 Command |
|-----------|----------------|--------------|
| FTS5 索引器 | 每 5 分鐘 | `*/5 * * * * $HOME/.openclaw/scripts/fts5-indexer.sh` |
| Self-Improving 交換 | 每天 3 AM | `0 3 * * * ~/.openclaw/skills/fts5/self_improving/scripts/exchange-cron.sh` |

---

## 🔧 設定 | Configuration

```bash
# 環境變數 | Environment variable
export MINIMAX_API_KEY=sk-cp-your-key-here

# 或設定檔 | Or config file
echo "MINIMAX_API_KEY=sk-cp-your-key-here" > ~/.openclaw/fts5.env
```

---

## 🛡️ 安全 | Security

- ✅ 無硬編碼 API Key | No hardcoded API keys
- ✅ 使用者提供憑證 | User-provided credentials only
- ✅ 敏感資料自動遮罩 | Sensitive data auto-masked
- ✅ 私人設定檔（600 權限）| Private config (600 permissions)

---

## 📄 文件 | Documentation

| 檔案 File | 語言 Language | 說明 Description |
|-----------|---------------|-----------------|
| `README.md` | 中文/English | **本頁 Main** |
| `SKILL.md` | English | OpenClaw 技能定義 |
| `CHANGELOG.md` | English | 版本記錄 |

---

## 📄 授權 | License

MIT License — 詳見 [LICENSE](LICENSE)

---

**由 Ophelia Prime 製作 | Made by Ophelia Prime**

[GitHub](https://github.com/ZCrystalC33/fts5-openclaw-skill) · [回報問題](https://github.com/ZCrystalC33/fts5-openclaw-skill/issues)
