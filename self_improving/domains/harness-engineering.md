# Harness Engineering - 智慧體優先的軟體工程

## 核心理念

**人掌舵，代理執行。**

人類的職責：
- 設計環境
- 明確意圖
- 建立回饋迴路

不是：
- 親自寫程式碼

---

## 關鍵文章

### 1. Ralph Wiggum Loop
**URL:** https://ghuntley.com/loop/

**核心概念：**
> "Software is now clay on the pottery wheel"

- 傳統：磚塊式建築（Jenga）
- 新做法：Loop — 不斷循環，失敗了就丟回輪上重做
- 工程師的角色變成「設計循環」而不是「寫 code」

**對我們的啟示：**
- FTS5 的 exchange_engine.py 就是這種概念的體現
- 壞味道 → 自動修復 → 再驗證

---

### 2. ARCHITECTURE.md 指南
**URL:** https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html

**核心概念：**
- 讓新進者快速理解架構的高層次文件
- 不要太詳細，只記錄不容易變動的部分
- 回答：「哪裡有這個功能？」+ 「這個程式在做什麼？」

**對我們的啟示：**
- FTS5 已有 `ARCHITECTURE.md`
- 保持簡短，半年檢視一次

---

### 3. Parse, Don't Validate
**URL:** https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/

**核心概念：**
> 在邊界解析數據，不要在各地重複驗證

**例子：**
```python
# ❌ 傳統做法
def get_head(lst):
    if not lst:
        raise ValueError("empty")
    return lst[0]

# 在 main 裡還要再檢查一次

# ✅ 使用強類型，類型系統保證不可能為空
# NonEmpty type 只在 construction 時驗證一次
```

**對我們的啟示：**
- 在 indexer 入口做一次驗證
- 之後的處理不需要重複檢查

---

### 4. AI Is Forcing Us To Write Good Code
**URL:** https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code

**核心概念：**

| 傳統做法 | Agent 時代做法 |
|---------|--------------|
| 測試可選 | **100% 覆蓋率** |
| 大檔案 | **多個小檔案** |
| 慢品質檢查 | **快速 guardrails** |
| 手動重啟環境 | **自動化 worktree** |

**關鍵洞察：**
- 95% 覆蓋率 vs **100% 覆蓋率** — 到 100% 有相位變化
- 覆蓋率報告變成簡單的 TODO 列表
- **目錄結構 = 介面** — 幫 AI 理解你的程式碼

---

## Harness Engineering 實踐清單

### 環境設計
- [x] 明確的目錄結構
- [x] 單一職責的檔案
- [x] 清晰的命名
- [ ] 自動化環境設定腳本

### 回饋迴路
- [x] linter.py 強制架構
- [x] exchange_engine.py 持續維護
- [ ] doc-gardening agent（自動更新文件）

### 驗證與品質
- [x] 路徑檢測一致性
- [x] 層級依賴檢查
- [x] Script 權限檢查
- [ ] 單元測試覆蓋

### 知識管理
- [x] AGENTS.md 是目錄
- [x] 領域知識在 domains/
- [x] Pattern Registry 壞味道集中管理

---

## 我們的差距

| 原則 | 現狀 | 目標 |
|------|------|------|
| 100% 覆蓋率 | 0% | 有單元測試 |
| 快速 guardrails | linter OK | < 5 秒執行 |
| doc-gardening | 手動 | 自動化 |
| 自動化環境 | 需手動 | `setup.py` |

---

## 參考連結

1. [Ralph Wiggum Loop](https://ghuntley.com/loop/)
2. [ARCHITECTURE.md Guide](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html)
3. [Parse, Don't Validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
4. [AI Is Forcing Us To Write Good Code](https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code)
5. [Cookbook - Codex Exec Plans](https://cookbook.openai.com/articles/codex_exec_plans)

---

*最後更新：2026-04-16*
