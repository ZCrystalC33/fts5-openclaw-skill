# ARCHITECTURE.md - FTS5 架構文件

> 本文件描述 FTS5 的高層次架構。保持簡短，只記錄不容易變動的部分。
> 不要與程式碼同步，半年檢視一次即可。

---

## 目標與概述

**FTS5** 是一個為 OpenClaw 設計的對話歷史搜尋系統，內建 Self-Improving 智慧學習。

核心功能：
1. SQLite FTS5 全文搜尋
2. LLM 驅動的摘要生成
3. 從修正中自動學習（Self-Improving）

---

## 程式碼結構

```
fts5/
├── __init__.py           # 入口：search(), summarize(), get_stats()
├── llm_summary.py        # LLM + 多語言 Prompt
├── rate_limiter.py       # 30 calls/min
├── error_handling.py     # 三層 Fallback
├── indexer.py            # 對話索引器
├── sensitive_filter.py    # API Key 遮罩
├── linter.py             # 架構強制工具
│
└── self_improving/       # 自我改進整合
    ├── memory.md         # 熱層（≤100 行）
    ├── corrections.md     # 修正日誌
    ├── domains/          # 領域知識
    │   ├── openclaw-fts5.md
    │   └── patterns.md    # 壞味道註冊表
    └── scripts/          # 自動化腳本
        ├── context_predictor.py
        ├── reindex.py
        ├── exchange_engine.py
        └── fts5_integration.py
```

---

## 模組依賴方向

```
Layer 0 (Core):      __init__.py, llm_summary.py
        ↓
Layer 1 (Infra):     indexer.py, error_handling.py, sensitive_filter.py
        ↓
Layer 2 (Scripts):    self_improving/scripts/*.py
```

**重要原則：** Layer 只能往下呼叫，不能往上。

---

## 核心不變量

### 1. 路徑檢測
```python
# 所有腳本必須支援雙位置
_ORIGINAL_DIR = Path.home() / "self-improving"
_MERGED_DIR = _SCRIPT_DIR.parent  # FTS5 repo 內

if _ORIGINAL_DIR.exists():
    USE_ORIGINAL  # 優先保留既有資料
else:
    USE_MERGED
```

### 2. 層級交換規則
| 層級 | 位置 | 觸發條件 |
|------|------|---------|
| HOT | memory.md | 7 天內引用 |
| WARM | domains/ | 3+ 引用 |
| COLD | archive/ | 30+ 天未引用 |

### 3. 錯誤恢復三層
1. **Retry** — 重試一次
2. **Fallback Template** — 使用範本
3. **Raw Results** — 回傳原始結果

### 4. API 導出規則
`__init__.py` 只導出以下公開 API：
- `search()`
- `summarize()`
- `get_stats()`
- `add_message()`

---

## 跨領域關注點

### 驗證
- 所有使用者提供的 API Key 不寫入程式碼
- `sensitive_filter.py` 自動遮罩敏感資料

### 錯誤處理
- `error_handling.py` 提供統一的錯誤類型
- LLM 回應有 3 層 fallback

### 監控
- 頻率限制：30 calls/min
- `get_stats()` 提供索引統計

---

## 設計原則（學自 Harness Engineering）

### 1. Parse, Don't Validate
> 在邊界解析數據，不要在各地重複驗證

FTS5 的 indexer 在入口解析對話，不在每次搜尋時重複驗證。

### 2. AGENTS.md 是目錄，不是百科全書
> 給予 agent 一張地圖，而不是一本 1000 頁的手冊

本專案結構：
- `AGENTS.md` ≈ 100 行，指向各知識庫
- 詳細文件在 `domains/` 和 `docs/`

### 3. 機械化強制 > 文件規定
> 用 linter.py 驗證，不是靠人 review

所有架構規則都在 `linter.py` 中自動化檢測。

### 4. 小檔案，單一職責
> 幫助 agent 載入完整內容

每個模組保持 200 行以內，單一職責。

---

## 擴展指南

### 新增功能
1. 放在對應的 Layer
2. 更新 `linter.py` 新增檢查（如需要）
3. 更新本文件和 `domains/patterns.md`
4. 執行 `linter.py` 確認通過

### 新增領域知識
1. 在 `self_improving/domains/` 建立新檔案
2. 更新 `index.md`（執行 `reindex.py`）
3. 在 `patterns.md` 新增相關的 anti-patterns

---

## 外部依賴

| 依賴 | 用途 | 說明 |
|------|------|------|
| Python 3.7+ | Runtime | 標準庫為主 |
| sqlite3 | 搜尋引擎 | 標準庫 |
| urllib | LLM API | 標準庫 |
| MiniMax API | LLM | 需要 API Key |

---

*最後更新：2026-04-16*
*建議每半年檢視一次*
