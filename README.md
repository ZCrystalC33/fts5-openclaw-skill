# OpenClaw PFSI

> ⚡ **Proactive Full-text Self-improving Integration** — AI 助理的記憶引擎。
>
> ⚡ Make your AI assistant proactive, contextual, and self-improving.

[![授權：MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![版本](https://img.shields.io/badge/Version-2.0.0-green.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)

---

## PFSI 架構 | Architecture

```
用戶訊息
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Proactivity ──── 觸發條件偵測（上次、之前、繼續）          │
│     │                                                      │
│     ├──► FTS5 ──── 即時搜尋（1.4ms 平均）                  │
│     │                                                      │
│     ├──► Self-Improving ─── 修正模式分析                   │
│     │                     └── 學習寫入 corrections.md       │
│     │                                                      │
│     └──► Action ──── 主動預測 + 回覆                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔰 功能特色 | Features

| 功能 | 說明 |
|------|------|
| **Proactive Engine** | 主動偵測「上次」「之前」等 trigger，自動搜尋歷史 |
| **Full-Text Search** | SQLite FTS5，即時跨所有對話搜尋 |
| **Self-Improving** | 從修正中學習，持續追蹤模式 |
| **LLM Summaries** | 自動生成多語言摘要（繁中/簡中/英文/日文）|
| **Three-Layer Integration** | Proactivity + FTS5 + Self-Improving 閉環 |
| **Auto-Index** | Cron 增量更新，每 5 分鐘 |
| **Rate Limiting** | 每分鐘 30 次（含 sliding window）|
| **Error Recovery** | 三層 fallback 機制 |
| **Two-Step Save** | Topic → Index，崩潰安全 |
| **Mutual Exclusion** | 主代理寫入時萃取跳過 |
| **MCP Server** | 可选的 stdio/HTTP MCP server（技術債）|

---

## 🚀 快速開始 | Quick Start

```bash
# 1. 複製 | Clone
git clone https://github.com/ZCrystalC33/openclaw-pfsi.git ~/.openclaw/skills/pfsi
cd ~/.openclaw/skills/pfsi

# 2. 設定 | Configure

**Standard Location (Recommended):**
```bash
mkdir -p ~/.openclaw/credentials
# 將您的 API Key 寫入標準位置
echo "sk-cp-your-key" > ~/.openclaw/credentials/minimax.key
chmod 600 ~/.openclaw/credentials/minimax.key
```

**Legacy Location (Alternative):**
```bash
cp config.env.example ~/.openclaw/fts5.env
nano ~/.openclaw/fts5.env  # 填入 MINIMAX_API_KEY
```

# 3. 安裝 | Install
python3 setup.py

# 4. 重啟 | Restart
openclaw gateway restart
```

---

## 💬 使用方式 | Usage

### 基本搜尋 | Basic Search

```python
from skills.fts5 import search, summarize, get_stats

# 搜尋對話歷史
results = search("上次 OpenClaw", limit=5)

# LLM 摘要
result = summarize("MCP 伺服器", results)
print(result['summary'])

# 資料庫統計
print(get_stats())
```

### Proactive Integration Engine

```python
from proactive_integration import run_proactive_check

# 當用戶說「上次...」時自動觸發
result = run_proactive_check("上次 OpenClaw")
if result:
    print(result)  # 主動回覆相關歷史
```

### MCP Server（技術債）| MCP Server (Tech Debt)

```bash
# Stdio 模式
python3 mcp_server.py

# HTTP 模式
python3 mcp_http_server.py  # Port 18820
```

---

## 📦 模組結構 | Module Structure

### 核心 | Core

| 檔案 | 功能 |
|------|------|
| `__init__.py` | 主 API: `search()`, `summarize()`, `get_stats()` |
| `proactive_integration.py` | 三位一體整合引擎 |
| `llm_summary.py` | LLM + 多語言 Prompt |
| `indexer.py` | 對話索引器（Checkpoint/Resume）|
| `rate_limiter.py` | 30 calls/min sliding window |
| `error_handling.py` | 三層 fallback |
| `sensitive_filter.py` | 敏感資料遮罩 |
| `mcp_server.py` | MCP Stdio Server（技術債）|
| `mcp_http_server.py` | MCP HTTP Server（技術債）|

### Self-Improving 整合 | Self-Improving Integration

| 檔案 | 功能 |
|------|------|
| `context_predictor.py` | 話題預測 + 相互排斥 |
| `exchange_engine.py` | 冷/熱層交換（雙步儲存）|
| `fts5_integration.py` | 雙向同步 |

---

## 📊 層級規則 | Layer Rules

| 層級 | 位置 | 條件 |
|------|------|------|
| **熱** | `memory.md` | 7 天內引用 |
| **溫** | `topics/` | 3+ 引用 |
| **冷** | `archive/` | 30+ 天未引用 |

---

## 🛡️ 安全 | Security

- ✅ 無硬編碼 API Key
- ✅ 使用者提供憑證
- ✅ 敏感資料自動遮罩
- ✅ 私人設定檔（600 權限）

---

## ⚠️ 技術債 | Tech Debt

| 項目 | 說明 | 狀態 |
|------|------|------|
| MCP Stdio | OpenClaw stdio transport 不穩定 | 已記錄 |
| MCP HTTP | HTTP 版本已預備 | 待整合 |
| Semantic Search | 需要 Honcho | 等 Docker |

---

## 📄 文件 | Documentation

| 檔案 | 說明 |
|------|------|
| `README.md` | 本頁（中文/English）|
| `SKILL.md` | OpenClaw 技能定義 |
| `CHANGELOG.md` | 版本記錄 |

---

## 授權 | License

MIT License — 詳見 [LICENSE](LICENSE)

---

**Made by Ophelia Prime ⚡**

[GitHub](https://github.com/ZCrystalC33/openclaw-pfsi) · [Issues](https://github.com/ZCrystalC33/openclaw-pfsi/issues)