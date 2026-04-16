# FTS5 - Full-Text Search for OpenClaw / 開放式全文搜尋系統

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.2.0-green.svg)](CHANGELOG.md)

> SQLite FTS5 full-text search with LLM-powered summarization for OpenClaw conversations.
> SQLite FTS5 全文搜尋 + LLM 智慧摘要，為 OpenClaw AI 助理提供對話歷史檢索能力。

[英文說明](#english) / [中文說明](#中文)

---

## English | 英文說明

### 🎯 What is FTS5?

FTS5 enables your OpenClaw AI assistant to search and summarize past conversations. It uses SQLite's FTS5 (Full-Text Search) engine to index messages and combines with LLM (MiniMax) to generate meaningful summaries.

### ✨ Features | 功能特色

| Feature | 功能 | Description | 說明 |
|---------|------|-------------|------|
| 🔍 | 全文字搜尋 | Full-text search across all history | 跨越所有對話歷史的即時搜尋 |
| 🤖 | LLM 摘要 | Automatic summary generation | 自動根據語言生成摘要 |
| 🌍 | 多語言支援 | zh-TW, zh-CN, en, ja | 繁簡中文、英文、日文 |
| 🔒 | 敏感資料過濾 | Auto-masks API keys, tokens | 自動遮罩 API Key、Token |
| ⚡ | 頻率限制 | 10 calls/min max | 每分鐘最多 10 次 |
| 🛡️ | 錯誤恢復 | 3-layer fallback | 三層 Fallback 機制 |
| 📊 | 智慧上下文 | Auto-adjusts by complexity | 根據查詢複雜度調整 |
| 🔄 | 增量索引 | Only processes changed files | 只處理有變動的檔案 |

### 📦 Installation | 安裝方式

**Prerequisites | 前置需求：**
- Python 3.7+
- SQLite3 (built-in | Python 內建)
- MiniMax API Key ([Get one | 申請](https://platform.minimax.io/))

**Steps | 步驟：**

```bash
# 1. Clone the repository | 複製 Repo
git clone https://github.com/kiwi760303/fts5-openclaw-skill.git ~/.openclaw/skills/fts5

# 2. Copy and edit configuration | 複製並編輯設定檔
cp ~/.openclaw/skills/fts5/config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # Add your MINIMAX_API_KEY | 填入你的 API Key

# 3. Run onboarding (recommended) | 執行安裝精靈（建議）
python3 ~/.openclaw/skills/fts5/setup.py

# 4. Index existing conversations (optional) | 索引既有的對話（可選）
python3 ~/.openclaw/skills/fts5/indexer.py
```

### ⚙️ Configuration | 設定方式

**API Key Setup | API Key 設定：**

| Method | 方式 | Command | 指令 |
|--------|------|---------|------|
| Environment Variable | 環境變數（推薦） | `export MINIMAX_API_KEY=sk-cp-your-key` | ✅ Recommended |
| Config File | 設定檔案 | Edit `~/.openclaw/fts5.env` | 編輯設定檔 |

**Priority Order | 優先順序：**
```
1. MINIMAX_API_KEY environment variable | 環境變數
2. ~/.openclaw/fts5.env config file | 設定檔案
3. ~/.openclaw/config.json (fts5.api_key) | JSON 設定
```

### 🚀 Quick Usage | 快速使用

```python
from skills.fts5 import search, summarize, get_stats

# Simple search | 簡單搜尋
results = search("Discord Bot", limit=5)

# LLM-powered summary | LLM 摘要
result = summarize("上次討論的內容")
print(result['summary'])

# Get statistics | 取得統計
stats = get_stats()
print(f"Total messages: {stats['total']}")  # 總訊息數
```

### 🔧 Module Reference | 模組函數

| Function | 函數 | Description | 說明 |
|----------|------|-------------|------|
| `search(query, limit)` | 搜尋 | FTS5 full-text search | FTS5 全文搜尋 |
| `summarize(query, limit)` | 摘要 | Search + LLM summary | 搜尋 + LLM 摘要 |
| `add_message(...)` | 新增 | Add message to index | 新增訊息到索引 |
| `get_recent(limit)` | 最近 | Get recent messages | 取得最近訊息 |
| `get_stats()` | 統計 | Database statistics | 資料庫統計 |

### 🌐 Multi-Language | 多語言支援

FTS5 auto-detects your query language and uses appropriate prompts.

FTS5 自動偵測你的查詢語言並使用對應的 Prompt：

| Language | 語言 | Code | 代碼 | Detection | 偵測方式 |
|----------|------|------|------|-----------|---------|
| English | 英文 | en | - | Default | 預設 |
| 繁體中文 | Traditional Chinese | zh-TW | 繁 | 開/龍/體 chars | 開/龍/體字元 |
| 簡體中文 | Simplified Chinese | zh-CN | 簡 | 开/龙/体 chars | 开/龙/体字元 |
| 日本語 | Japanese | ja | 日 | Hiragana/Katakana | 平假名/片假名 |

### 🛡️ Error Handling | 錯誤處理

FTS5 has 3-layer error recovery | FTS5 有三層錯誤恢復機制：

```
Layer 1: Try normal LLM API call | 嘗試正常 LLM API 呼叫
    ↓ Failed | 失敗
Layer 2: Wait 5-10s, retry once | 等待 5-10 秒後重試一次
    ↓ Failed | 失敗  
Layer 3: Use template-based summary | 使用模板生成摘要
```

No API key? Shows setup instructions instead of crashing.
沒有 API Key？顯示設定說明而不是崩潰。

### 📁 File Structure | 檔案結構

```
fts5/
├── __init__.py           # Main module | 主模組
├── llm_summary.py         # LLM + prompts | LLM + Prompt
├── rate_limiter.py        # Rate limit | 頻率限制
├── error_handling.py      # 3-layer fallback | 三層 Fallback
├── indexer.py             # Session indexer | 對話索引器
├── sensitive_filter.py    # Data masking | 資料遮罩
├── setup.py               # Onboarding wizard | 安裝精靈
├── config.env.example     # Example config | 範例設定檔
├── SKILL.md              # OpenClaw skill | 技能定義
├── README.md             # This file | 本檔案
└── CHANGELOG.md          # Version history | 版本記錄
```

### 🔒 Security | 安全性

- ✅ **No hardcoded credentials** - All API keys are user-provided
  - 無硬編碼憑證 - 所有 API Key 由使用者提供
- ✅ **Sensitive data masking** - Auto-hides API keys, tokens, private keys
  - 敏感資料遮罩 - 自動隱藏 API Key、Token、私鑰
- ✅ **Incremental indexing** - Only processes new/modified files
  - 增量索引 - 只處理新增/修改的檔案

### 📄 License | 授權

MIT License - See [LICENSE](./LICENSE) file | 詳見 LICENSE 檔案。

### 🙏 Acknowledgments | 致謝

- Built for [OpenClaw](https://github.com/openclaw/openclaw) AI assistant framework
- 為 OpenClaw AI 助理框架而建
- Uses [MiniMax](https://platform.minimax.io/) for LLM capabilities
- 使用 MiniMax 提供 LLM 能力
- Powered by SQLite FTS5 full-text search engine
- 基於 SQLite FTS5 全文搜尋引擎

---

## 中文 | Chinese

### 🎯 FTS5 是什麼？

FTS5 能讓你的 OpenClaw AI 助理搜尋並摘要過往的對話。它使用 SQLite 的 FTS5（全文搜尋）引擎來索引訊息，並結合 LLM（MiniMax）生成有意義的摘要。

### ✨ 功能特色

| 功能 | 說明 |
|------|------|
| 🔍 全文字搜尋 | 跨越所有對話歷史的即時搜尋 |
| 🤖 LLM 摘要 | 自動根據你的語言生成摘要 |
| 🌍 多語言支援 | 繁體中文、簡體中文、英文、日文 |
| 🔒 敏感資料過濾 | 自動遮罩 API Key、Token、私鑰 |
| ⚡ 頻率限制 | API 保護（每分鐘最多 10 次） |
| 🛡️ 錯誤恢復 | 三層 Fallback 機制 |
| 📊 智慧上下文 | 根據查詢複雜度自動調整 |
| 🔄 增量索引 | 只處理有變動的檔案 |

### 📦 安裝方式

#### 前置需求
- Python 3.7+
- SQLite3（Python 內建）
- MiniMax API Key（[申請連結](https://platform.minimax.io/)）

#### 安裝步驟

```bash
# 1. 複製 Repo
git clone https://github.com/kiwi760303/fts5-openclaw-skill.git ~/.openclaw/skills/fts5

# 2. 複製並編輯設定檔
cp ~/.openclaw/skills/fts5/config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # 填入你的 MINIMAX_API_KEY

# 3. 執行安裝精靈（建議）
python3 ~/.openclaw/skills/fts5/setup.py

# 4. 索引既有的對話（可選）
python3 ~/.openclaw/skills/fts5/indexer.py
```

### ⚙️ 設定方式

#### API Key 設定

**方式一：環境變數（推薦）**
```bash
export MINIMAX_API_KEY=sk-cp-your-key-here
```

**方式二：設定檔案**
```bash
# 編輯 ~/.openclaw/fts5.env
MINIMAX_API_KEY=sk-cp-your-key-here
```

#### 優先順序
1. `MINIMAX_API_KEY` 環境變數
2. `~/.openclaw/fts5.env` 設定檔
3. `~/.openclaw/config.json` (fts5.api_key)

### 🚀 快速使用

```python
from skills.fts5 import search, summarize

# 搜尋訊息
results = search("Discord Bot", limit=5)

# LLM 摘要
result = summarize("上次討論的內容")
print(result['summary'])

# 取得統計
from skills.fts5 import get_stats
stats = get_stats()
print(f"總訊息數: {stats['total']}")
```

### 🔧 模組函數

| 函數 | 說明 |
|------|------|
| `search(query, limit)` | FTS5 全文搜尋 |
| `summarize(query, limit)` | 搜尋 + LLM 摘要 |
| `add_message(...)` | 新增訊息到索引 |
| `get_recent(limit)` | 取得最近訊息 |
| `get_stats()` | 資料庫統計 |

### 🌐 多語言支援

FTS5 自動偵測你的查詢語言並使用對應的 Prompt：

| 語言 | 代碼 | 偵測方式 |
|------|------|---------|
| 繁體中文 | zh-TW | 開/龍/體 等字元 |
| 簡體中文 | zh-CN | 开/龙/体 等字元 |
| 英文 | en | 預設 |
| 日本語 | ja | 平假名/片假名 |

### 🛡️ 錯誤處理

FTS5 有三層錯誤恢復機制：

1. **正常**：嘗試 LLM API 呼叫
2. **重試**：等待 5-10 秒後重試一次
3. **Fallback**：使用模板生成摘要

沒有 API Key？顯示設定說明而不是崩潰。

### 🐛 疑難排解

**"MINIMAX_API_KEY not found"**
```bash
python3 ~/.openclaw/skills/fts5/setup.py
```

**"API 連線失敗"**
1. 檢查 API Key 是否正確
2. 確認網路連線
3. 執行 setup 測試

---

**Version | 版本：** 1.2.0  
**Last Updated | 更新日期：** 2026-04-16  
**GitHub | GitHub：** https://github.com/kiwi760303/fts5-openclaw-skill