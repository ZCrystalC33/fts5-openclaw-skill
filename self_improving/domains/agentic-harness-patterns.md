# Agentic Harness Patterns 研究報告

> 資料來源：https://github.com/keli-wen/agentic-harness-patterns-skill
> 從 Claude Code 512,000 行原始碼萃取的生產級設計模式

---

## 📋 六大設計模式總覽

| Pattern | 解決問題 | 核心原則 |
|---------|---------|---------|
| **Memory** | 代理忘記一切 | 分層持久化、雙步儲存、相互排斥萃取 |
| **Skills** | 每次都要重新解釋 | Lazy-loaded、預算約束發現 |
| **Tools & Safety** | 工具強大但安全 | Fail-closed、per-call 并發 |
| **Context Engineering** | 看到太多/太少/錯誤 | Select/Write/Compress/Isolate |
| **Multi-agent** | 平行但不混亂 | Coordinator 必須綜合，不是委託 |
| **Lifecycle** | Hooks + 背景任務 | 單一 dispatch、依賴排序 |

---

## 1. Memory（記憶模式）⭐ 與我們最相關

### 核心原則

```
Golden Rule: 分離三種記憶

Instruction Memory（人類編寫）
├── 組織級 → 用戶級 → 專案級 → 本地級
└── 穩定、版本控制

Auto-Memory（代理寫入）
├── 四種類型：user / feedback / project / reference
├── 雙步儲存：topic file → index
└── 有上限的 index（防止無限增長）

Session Extraction（背景萃取）
├── 在 session 結束時執行
├── 與主代理相互排斥（同一 turn 不能同時寫）
└── 需要沙箱限制
```

### 四層指令階層（Claude Code 為例）

```
Priority 低 → 高：

1. Organization (組織級)     → CLAUDE.md in managed location
2. User (用戶級)           → ~/.claude/CLAUDE.md
3. Project (專案級)        → ./CLAUDE.md, ./rules/
4. Local (本地覆蓋)        → ./CLAUDE.local.md (永不進版控)
```

**重要：本地覆蓋永遠贏！**

### 雙步儲存 invariant

```python
# ❌ 錯誤：直接寫入 index
memory_index.append(full_content)

# ✅ 正確：先寫 topic file，再更新 index
write_topic_file(topic_id, content)  # Step 1
append_to_index(topic_id, summary)   # Step 2
```

**為什麼？** 如果在兩個步驟之間崩潰：
- index 保持一致（不會指向不存在的內容）
- 只會產生孤立的 topic file（無害）

### Auto-Memory 類型分類

| 類型 | 內容 | 範例 |
|------|------|------|
| `user` | 用戶身份、偏好 | "使用者喜歡用繁體中文" |
| `feedback` | 行為修正 | "糾正：不要用 npm，要用 bun" |
| `project` | 專案上下文 | "這個專案使用 TypeScript" |
| `reference` | 穩定參考事實 | "API 文件在 /docs" |

**排除原則：** 不要儲存可從 codebase 推導的內容（會過期）

### Session Extraction 的相互排斥

```python
# 如果主代理在這個 turn 寫入了記憶
if main_agent_wrote_memory(turn):
    extractor.skip()  # 跳過這個 turn
    advance_cursor()
else:
    extractor.run()   # 執行萃取
```

**原因：** 防止兩個 writer 衝突

---

## 2. Skills（技能模式）

### 核心原則

```
Discovery: 預算約束
├── 只載入 metadata（cheap）
├── Full body 只在 activation 時載入
└── 總上限 ≈ 1% context window

Loading: Lazy
├── Idle token cost ≈ 0
└── Activation 時才 full load

Execution: 可選隔離
├── Inline: 共享 context
└── Forked: 獨立 token budget
```

### 觸發語言要放在前面

```
# ❌ 錯誤：描述在前面
description: "A skill for Python development"
trigger: "python, pip, virtualenv"

# ✅ 正確：觸發關鍵字在前面
trigger: "python, pip, virtualenv"
description: "A skill for Python development"
```

**原因：** 目錄有字數上限，尾巴會被截斷

---

## 3. Tools & Safety（工具與安全）

### Fail-Closed 預設

```
預設行為：
├── 新工具 = 非並發 + 非唯讀
├── 必須明確 opt-in 才能並發
└── 防止意外平行執行狀態改變操作
```

### Per-Call 不是 Per-Tool

```
同一個工具對不同輸入有不同行為：

tool.read("config.json")     → safe for concurrent
tool.write("config.json")    → unsafe for concurrent
tool.delete("config.json")  → unsafe for concurrent
```

**重點：** 並發分類是針對每次呼叫，不是每個工具

---

## 4. Context Engineering（上下文工程）⭐ 與 FTS5 最相關

### 四軸框架

| 操作 | 作用 | 時機 |
|------|------|------|
| **Select** | Just-in-time loading | 需要的時候才載入 |
| **Write** | 寫入持久化存儲 | 學習循環 |
| **Compress** | 摘要舊內容 | session 太長時 |
| **Isolate** | 隔離委託工作 | 防止污染父 context |

### Select：三層漸進揭露

```
Tier 1 (Always):      Metadata (~100 tokens) → 總是在 context
Tier 2 (Activation):   Instructions (<5000 tokens) → skill 啟動時
Tier 3 (On-demand):   Resources (無上限) → 按需載入
```

**關鍵：Discovery cost scales with catalog size, execution cost is constant per activated item**

### Select 的 Memoization 模式

```python
# ❌ 錯誤：只 memoize 結果
cache = {key: expensive_result}

# ✅ 正確：memoize promise（防止並發 races）
in_flight = {}  # promise 本身是 deduplication key
if key not in in_flight:
    in_flight[key] = expensive_async_call()
result = await in_flight[key]
```

### Select 的 Invalidation 原則

```
❌ 不要用 timer 或 reactive subscriptions
✅ 在 mutation site 明確呼叫 invalidation

原因：
- Timer-based: 要嘛 serving stale data，要嘛 rebuild too often
- Manual invalidation: 只在真正改變時 rebuild
```

### Compress：三層機制

| 機制 | 說明 |
|------|------|
| **Truncate + Recovery Pointer** | 截斷內容時附上"如何復原"的具體指示 |
| **Reactive Compaction** | 當 fill ratio 達到門檻時觸發（不是定時）|
| **Snapshot Labeling** | 所有快照都要標記"這是時間 T 的快照" |

### Compress 的 Truncation 黃金法則

```
截斷時必須包含：
1. 具體的工具名稱
2. 具體的參數
3. 明確說明這是截斷的

❌ 錯誤：只說 "output was truncated"
✅ 正確："Run `cat filename` to see full output"
```

### Isolate：委託邊界

```
Coordinator Pattern:
├── Worker 從零 context 開始
├── 只有 explicit prompt 被繼承
└── 不繼承父的完整 context

Fork Pattern:
├── Child 繼承父的全部 context
├── 只能單層（不能遞迴 fork）
└── 防止 context cost 指數增長

Isolate 的前提：
- Filesystem isolation (worktrees)
- Path translation injection
- 工具過濾
```

---

## 5. Multi-agent（多代理協調）

### 三種模式

| 模式 | Context 共享 | 適用場景 |
|------|-------------|---------|
| **Coordinator** | 無（worker 從零開始）| 複雜多階段任務 |
| **Fork** | 完全繼承 | 快速平行分割 |
| **Swarm** | Peer-to-peer（共享 task list）| 長時獨立工作流 |

### Coordinator 的關鍵原則

```
❌ Anti-pattern:
"Based on your findings, fix it"

✅ 正確做法：
Coordinator 必須综合理解，不是只委託
→ 研究結果 → 綜合 → 精確規格 → 派遣實現
```

### 實現檢查清單

```
1. 定義階段工作流：研究 → 綜合 → 實現 → 驗證
2. 每個 worker 的 prompt 必須是自包含文檔
3. 過濾每個 worker 的工具集
4. 決定 continue vs spawn 策略
```

### 深度必須有界

```
❌ 危險：遞迴 delegation
├── Fork children 不能 fork
├── Swarm peers 不能 spawn other peers
└── 防止指數級 fan-out

原因：unbounded depth produces exponential fan-out that is impossible to monitor, cancel, or reason about
```

---

## 6. Lifecycle & Extensibility（生命週期）

### Hook 的六種類型

```
pre-tool-execution
post-tool-execution
pre-prompt-submission
post-prompt-submission
agent-start
agent-end
```

### Trust 是全有或全無

```python
if workspace.untrusted:
    skip_all_hooks()  # 不是只跳過可疑的
```

### Task Eviction：兩階段

```
Phase 1: 磁盤輸出在 terminal state 時 eager 清理
Phase 2: 記憶體記錄在 parent 收到通知後 lazy 清理

重要：eviction 必須在 notification 之後，否則 race condition
```

### Bootstrap 依賴排序

```
信任邊界是關鍵轉折點：
- 安全敏感的子系統（telemetry, secret env vars）
- 必須在信任建立之前不能激活
```

---

## 對 FTS5 的啟示

### 我們現有的

| 組件 | 對應 Pattern |
|------|-------------|
| FTS5 DB | Memory（持久化）|
| Self-Improving domains | Auto-Memory（領域知識）|
| corrections.md | Feedback（修正日誌）|
| exchange_engine.py | Session Extraction（自動分層）|

### 我們欠缺的

| Pattern | 我們沒有 | 建議 |
|---------|---------|------|
| Memory 分層 | 只有兩層（memory.md + domains/）| 參考四層結構 |
| 雙步儲存 | 直接寫入 | 重構為 topic file → index |
| 相互排斥萃取 | 無 | 加入檢查 |
| Lazy-loaded Skills | 無 | 研究 OpenClaw skills 機制 |
| Coordinator | 無 | 先專注單代理 |
| Hooks | 無 | Lifecycle 前期規劃 |
| Compress (Truncation + Recovery) | 無 | 考慮在 FTS5 搜尋結果應用 |

### 立即可行動的改進

```
1. 重構 exchange_engine.py：
   - 加入雙步儲存 invariant
   - 加入相互排斥檢查

2. 考慮 memory.md 的雙層結構：
   - Layer 1: memory.md（精簡 index）
   - Layer 2: domains/*.md（詳細內容）

3. 加入斷言和驗證：
   - INDEX_IS_CONSISTENT
   - MUTUAL_EXCLUSION_CHECK

4. 考慮在搜尋結果應用 Compression 模式：
   - 大結果截斷 + Recovery Pointer
   - Snapshot Labeling
```

---

## Gotchas（常見陷阱）

| # | 陷阱 | 說明 |
|---|------|------|
| 1 | Index truncation 是靜默的 | 達到上限時才警告 |
| 2 | Priority ordering 是反直覺的 | 本地覆蓋永遠贏 |
| 3 | 萃取時機造成 race window | 需要 mutual exclusion |
| 4 | 可推導內容不該進記憶 | 會浪費空間且過期 |
| 5 | 記憶不用於 session 內狀態 | session state 應分開處理 |
| 6 | Fork children 不能 fork | 設計時就要規劃好深度 |
| 7 | 驗證 worker 必須從零開始 | 否則會有假設盲點 |
| 8 | Truncation 必須有 recovery pointer | 否則是死路 |
| 9 | Snapshot labeling 防止過期推理 | git status 等必須標記時間點 |
| 10 | Tool filtering 有多層 | 不同 agent type 有不同限制 |

---

## Claude Code 具體實現細節

### Memory
- 四層指令階層（ORG → USER → PROJECT → LOCAL）
- 四型 Auto-Memory（user/feedback/project/reference）
- Index cap: 200 lines, 25,000 bytes
- Session extraction: 5 turn cap, mutual exclusion

### Skills
- Discovery budget: ~1% context window
- Per-entry cap: ~250 characters
- Trigger language front-loaded
- Lazy body loading on activation

### Context Engineering
- Fill-ratio monitor triggers compaction at ~80%
- Git status: 2000-char threshold with recovery pointer
- Variable-length blocks all have hard caps
- Snapshot labeling with timestamp

### Multi-agent
- 三種模式 mutual exclusion（同時間只能一種）
- Coordinator: phased workflow
- Fork: single-level, cache-aligned shared prefix
- Swarm: flat roster, shared task list

---

## 參考文檔

- [Agentic Harness Patterns Repo](https://github.com/keli-wen/agentic-harness-patterns-skill)
- [Memory Persistence Pattern](references/memory-persistence-pattern.md)
- [Skill Runtime Pattern](references/skill-runtime-pattern.md)
- [Context Engineering Pattern](references/context-engineering-pattern.md)
  - [Select Pattern](references/context-engineering/select-pattern.md)
  - [Compress Pattern](references/context-engineering/compress-pattern.md)
  - [Isolate Pattern](references/context-engineering/isolate-pattern.md)
- [Agent Orchestration Pattern](references/agent-orchestration-pattern.md)

---

*研究日期：2026-04-16*
