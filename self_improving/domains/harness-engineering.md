# Harness Engineering - 智慧體優先的軟體工程

## 核心理念

**人掌舵，代理執行。**

人類的職責：
- 設計環境
- 明確意圖
- 建立回饋迴路

---

## 關鍵文章

### 1. Ralph Wiggum Loop
**URL:** https://ghuntley.com/loop/

**核心概念：**
> "Software is now clay on the pottery wheel"

- 傳統：磚塊式建築（Jenga）
- 新做法：Loop — 不斷循環，失敗了就丟回輪上重做

---

### 2. ARCHITECTURE.md 指南
**URL:** https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html

**核心概念：** 高層次文件，只記錄不容易變動的部分

---

### 3. Parse, Don't Validate
**URL:** https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/

**核心概念：** 在邊界解析數據，不要在各地重複驗證

---

### 4. AI Is Forcing Us To Write Good Code
**URL:** https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code

**核心概念：** 100% 覆蓋率、目录结构 = 介面、快速 guardrails

---

## ⭐ Agentic Harness Patterns（重要！）

**URL:** https://github.com/keli-wen/agentic-harness-patterns-skill

從 Claude Code 512,000 行原始碼分析萃取的生產級設計模式。

### 6 大設計模式章節

| # | Pattern | 解決的問題 |
|---|---------|-----------|
| 1 | **Memory** | 「代理每個 session 都忘記一切」 |
| 2 | **Skills** | 「每個對話都要重新解釋工作流程」 |
| 3 | **Tools & Safety** | 「我想要強大但安全的工具」 |
| 4 | **Context Engineering** | 「代理看到太多/太少/錯誤的內容」 |
| 5 | **Multi-agent** | 「我需要平行但不混亂」 |
| 6 | **Lifecycle** | 「我需要 hooks、背景任務、啟動順序」 |

### 11 深度參考文檔

| Reference | 內容 |
|----------|------|
| `memory-persistence-pattern` | 四層指令階層、背景萃取 with mutual exclusion |
| `skill-runtime-pattern` | 四源發現、YAML frontmatter contract |
| `tool-registry-pattern` | Fail-closed builder、per-call concurrency |
| `permission-gate-pattern` | 單一 gate、三種行為 |
| `agent-orchestration-pattern` | Coordinator/Fork/Swarm 三模式 |
| `context-engineering` | Index → select/compress/isolate |
| `select-pattern` | 三層漸進揭露、手動快取失效 |
| `compress-pattern` | Truncation + recovery pointers |
| `isolate-pattern` | Zero-inheritance、worktree-based 隔離 |
| `hook-lifecycle-pattern` | 單一 dispatch、六種 hook 類型 |
| `task-decomposition-pattern` | Typed prefixed IDs、嚴格狀態機 |

### 安裝方式

```bash
npx skills add github:keli-wen/agentic-harness-patterns-skill
```

---

## Context Engineering 四大操作

| 操作 | 說明 |
|------|------|
| **Select** | Just-in-time loading，延遲載入 |
| **Write** | 學習循環，寫入記憶 |
| **Compress** | 反應式壓縮 |
| **Isolate** | 委託邊界 |

---

## Multi-Agent 三種模式

| 模式 | 特性 |
|------|------|
| **Coordinator** | 零繼承、必須綜合理解，不是只委託 |
| **Fork** | 完全繼承、單層 |
| **Swarm** | 平面 peer roster |

---

## 我們的差距

| 原則 | 現狀 | 目標 |
|------|------|------|
| Memory 持久化 | ✅ FTS5 DB | 四層階層 |
| Skills 發現 | ❌ 需手動 | Lazy-loaded |
| Context Engineering | ✅ 基本 | Select/Compress/Isolate |
| Multi-Agent | ❌ | Coordinator/Fork/Swarm |
| Lifecycle Hooks | ❌ | 六種 hook 類型 |
| 100% 覆蓋率 | 0% | 有單元測試 |

---

## 參考連結

### Harness Engineering
1. [Ralph Wiggum Loop](https://ghuntley.com/loop/)
2. [ARCHITECTURE.md Guide](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html)
3. [Parse, Don't Validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
4. [AI Is Forcing Us To Write Good Code](https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code)

### Agentic Harness Patterns（⭐）
5. [Agentic Harness Patterns Repo](https://github.com/keli-wen/agentic-harness-patterns-skill)
6. [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
7. [Claude Code Source](https://github.com/anthropics/claude-code)

### Context Engineering
8. [One Poem Suffices - Context Engineering](https://keli-wen.github.io/One-Poem-Suffices/one-poem-suffices/context-engineering/)
9. [Just-in-Time Context](https://keli-wen.github.io/One-Poem-Suffices/one-poem-suffices/just-in-time-context/)

---

*最後更新：2026-04-16*
