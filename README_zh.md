# FTS5 - OpenClaw 對話歷史搜尋系統

SQLite FTS5 全文搜尋 + LLM 智慧摘要，為 OpenClaw AI 助理提供對話歷史檢索能力。

[English](./README.md)

## 🎯 FTS5 是什麼？

FTS5 能讓你的 OpenClaw AI 助理搜尋並摘要過往的對話。它使用 SQLite 的 FTS5（全文搜尋）引擎來索引訊息，並結合 LLM（MiniMax）生成有意義的摘要。

## ✨ 功能特色

| 功能 | 說明 |
|------|------|
| 🔍 **全文搜尋** | 跨越所有對話歷史的即時搜尋 |
| 🤖 **LLM 摘要** | 自動根據你的語言生成摘要 |
| 🌍 **多語言支援** | 繁體中文、簡體中文、英文、日文 |
| 🔒 **敏感資料過濾** | 自動遮罩 API Key、Token、私鑰 |
| ⚡ **頻率限制** | API 保護（每分鐘最多 10 次） |
| 🛡️ **錯誤恢復** | 三層 Fallback 機制 |
| 📊 **智慧上下文** | 根據查詢複雜度自動調整 |
| 🔄 **增量索引** | 只處理有變動的檔案 |

## 📦 安裝方式

### 前置需求

- Python 3.7+
- SQLite3（Python 內建）
- MiniMax API Key（[申請連結](https://platform.minimax.io/)）

### 安裝步驟

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

## ⚙️ 設定方式

### API Key 設定

**方式一：環境變數（推薦）**
```bash
export MINIMAX_API_KEY=sk-cp-your-key-here
```

**方式二：設定檔案**
```bash
# 編輯 ~/.openclaw/fts5.env
MINIMAX_API_KEY=sk-cp-your-key-here
```

### 優先順序
1. `MINIMAX_API_KEY` 環境變數
2. `~/.openclaw/fts5.env` 設定檔
3. `~/.openclaw/config.json` (fts5.api_key)

## 🚀 快速使用

```python
# 簡單搜尋
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

## 🔧 模組函數

| 函數 | 說明 |
|------|------|
| `search(query, limit)` | FTS5 全文搜尋 |
| `summarize(query, limit)` | 搜尋 + LLM 摘要 |
| `add_message(...)` | 新增訊息到索引 |
| `get_recent(limit)` | 取得最近訊息 |
| `get_stats()` | 資料庫統計 |

## 🌐 多語言支援

FTS5 自動偵測你的查詢語言並使用對應的 Prompt：

| 語言 | 代碼 | 偵測方式 |
|------|------|---------|
| 繁體中文 | `zh-TW` | 開/龍/體 等字元 |
| 簡體中文 | `zh-CN` | 开/龙/体 等字元 |
| English | `en` | 預設 |
| 日本語 | `ja` | 平假名/片假名 |

## 🛡️ 錯誤處理

FTS5 有三層錯誤恢復機制：

1. **正常**：嘗試 LLM API 呼叫
2. **重試**：等待 5-10 秒後重試一次
3. **Fallback**：使用模板生成摘要

沒有 API Key？顯示設定說明而不是崩潰。

## 📁 檔案結構

```
fts5/
├── __init__.py           # 主模組
├── llm_summary.py         # LLM + 多語言 Prompt
├── rate_limiter.py        # 每分鐘 10 次限制
├── error_handling.py      # 三層 Fallback
├── indexer.py             # 對話索引器
├── sensitive_filter.py    # 資料遮罩
├── setup.py               # 安裝精靈
├── config.env.example     # 範例設定檔
├── SKILL.md              # OpenClaw 技能檔案
└── README.md             # 英文說明
```

## 🔒 安全性

- **無硬編碼憑證** - 所有 API Key 由使用者提供
- **敏感資料遮罩** - 自動隱藏 API Key、Token、私鑰
- **增量索引** - 只處理新增/修改的檔案

## 📄 授權

MIT License - 詳見 [LICENSE](./LICENSE) 檔案。

## 🐛 疑難排解

**"MINIMAX_API_KEY not found"**
```bash
python3 ~/.openclaw/skills/fts5/setup.py
```

**"API 連線失敗"**
1. 檢查 API Key 是否正確
2. 確認網路連線
3. 執行 setup 測試：`python3 ~/.openclaw/skills/fts5/setup.py`

## 🙏 致謝

- 為 [OpenClaw](https://github.com/openclaw/openclaw) AI 助理框架而建
- 使用 [MiniMax](https://platform.minimax.io/) 提供 LLM 能力
- 基於 SQLite FTS5 全文搜尋引擎

---

**版本：** 1.2.0  
**更新日期：** 2026-04-16