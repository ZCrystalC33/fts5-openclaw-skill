# Agentic Harness Patterns 完整研究報告

> 資料來源：https://github.com/keli-wen/agentic-harness-patterns-skill
> 從 Claude Code 512,000 行原始碼萃取的生產級設計模式
> 閱讀進度：13/13 ✅

---

## 總覽：十二大設計模式

| Pattern | 解決問題 | 核心原則 |
|---------|---------|---------|
| **Memory Persistence** | 代理忘記一切 | 分層持久化、雙步儲存、相互排斥萃取 |
| **Skill Runtime** | 每次都要重新解釋 | Lazy-loaded、預算約束發現 |
| **Tool & Safety** | 工具強大但安全 | Fail-closed、per-call 并發 |
| **Select** | 看到太多/太少 | 三層漸進揭露、Memoization |
| **Compress** | Context 太長 | Truncate + Recovery Pointer |
| **Isolate** | 委託邊界汙染 | Zero-inheritance、單層fork、filesystem isolation |
| **Agent Orchestration** | 多代理協調混亂 | Coordinator 必須綜合、深度有界 |
| **Hook Lifecycle** | 擴展性鉤子失控 | 單一 dispatch、trust 全有全無、deny>ask>allow |
| **Task Decomposition** | 長期工作管理 | Typed IDs、磁盤輸出、兩階段驅逐 |
| **Bootstrap Sequence** | 初始化順序混亂 | 依賴排序、memoized 並發、trust 分割 |
| **Multi-Agent Research** | 從原型到產品 | 評估策略、工程化挑戰、協作哲學 |
| **Long-Running Agents** | Session 斷裂問題 | Initializer + Coding Agent 雙軌、Feature List、Progress Artifacts |

---

## 1. Memory Persistence（記憶持久化）⭐

### 問題
代理每次 fresh start 都忘記一切，無法累积经验。

### 解決方案：四層指令階層 + 雙步儲存

```
Priority 低 → 高：
1. Organization (組織級)  → 全域共享設定
2. User (用戶級)         → 個人偏好
3. Project (專案級)      → 專案上下文
4. Local (本地覆蓋)      → 永不進版控

重要：本地覆蓋永遠贏！
```

### 四型 Auto-Memory

| 類型 | 內容 | 範例 |
|------|------|------|
| `user` | 用戶身份、偏好 | "使用者喜歡用繁體中文" |
| `feedback` | 行為修正 | "糾正：不要用 npm，要用 bun" |
| `project` | 專案上下文 | "這個專案使用 TypeScript" |
| `reference` | 穩定參考事實 | "API 文件在 /docs" |

### 雙步儲存 invariant

```python
# ❌ 錯誤：直接寫入 index
memory_index.append(full_content)

# ✅ 正確：先寫 topic file，再更新 index
write_topic_file(topic_id, content)  # Step 1
append_to_index(topic_id, summary)   # Step 2
```

**為什麼？** 如果在兩個步驟之間崩潰，index 保持一致，只會產生孤立的 topic file（無害）。

### Session Extraction 的相互排斥

```python
# 如果主代理在這個 turn 寫入了記憶，extractor 跳過
if main_agent_wrote_memory(turn):
    extractor.skip()
    advance_cursor()
else:
    extractor.run()
```

---

## 2. Skill Runtime（技能執行期）

### 問題
每次都要重新解釋指令，浪費 token。

### 解決方案：Lazy Loading + 預算約束

```
Discovery: 預算約束
├── 只載入 metadata（cheap）
├── Full body 只在 activation 時載入
└── 總上限 ≈ 1% context window

Loading: Lazy
├── Idle token cost ≈ 0
└── Activation 時才 full load
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

**原因：** 目錄有字數上限，尾巴會被截斷。

---

## 3. Tool & Safety（工具與安全）

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
```

**重點：** 並發分類是針對每次呼叫，不是每個工具。

---

## 4. Select（選擇性載入）⭐

### 問題
看到太多/太少/錯誤的上下文。

### 三層漸進揭露

```
Tier 1 (Always):      Metadata (~100 tokens) → 總是在 context
Tier 2 (Activation):   Instructions (<5000 tokens) → skill 啟動時
Tier 3 (On-demand):   Resources (無上限) → 按需載入
```

### Memoization 要 memoize promise

```python
# ❌ 錯誤：只 memoize 結果
cache = {key: expensive_result}

# ✅ 正確：memoize promise（防止並發 races）
in_flight = {}
if key not in in_flight:
    in_flight[key] = expensive_async_call()
result = await in_flight[key]
```

### Invalidation 原則

```
❌ 不要用 timer 或 reactive subscriptions
✅ 在 mutation site 明確呼叫 invalidation
```

---

## 5. Compress（壓縮）⭐

### 問題
Session 太長時效能下降。

### 三層機制

| 機制 | 說明 |
|------|------|
| **Truncate + Recovery Pointer** | 截斷內容時附上"如何復原"的具體指示 |
| **Reactive Compaction** | 當 fill ratio 達到門檻時觸發（不是定時）|
| **Snapshot Labeling** | 所有快照都要標記"這是時間 T 的快照" |

### Truncation 黃金法則

```
❌ 錯誤：只說 "output was truncated"
✅ 正確："Run `cat filename` to see full output"
```

截斷時必須包含：
1. 具體的工具名稱
2. 具體的參數
3. 明確說明這是截斷的

---

## 6. Isolate（隔離）⭐⭐⭐

### 問題
委託工作時 shared state 造成碰撞：context 洩漏、檔案競爭、遞迴 fork 指數成本。

### 核心原則

```
Zero-inheritance is the safest default
├── Worker 從零 context 開始
├── 只有 explicit prompt 被繼承
└── 不繼承父的完整 context

Full-inheritance forks must be single-level
├── Child 繼承父的全部 context
├── 只能單層（不能遞迴 fork）
└── 防止 context cost 指數增長
```

### Filesystem Isolation

```
當 sub-agent 修改檔案時：
1. 建立 isolated copy (worktree/temp/cow-clone)
2. 注入 path translations
3. 完工後透過 controlled integration point 合併
```

### 決策框架：Blast Radius

| 隔離層級 | Worker 最多能破壞什麼 |
|---------|---------------------|
| Zero-inheritance | 只有自己的輸出 |
| Full-inheritance fork | 與 parent state 不一致 |
| Shared-filesystem | Parent 的 working directory |

**永遠從最窄的邊界開始，確定需要時才拓寬。**

---

## 7. Agent Orchestration（代理協調）⭐

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

### 深度必須有界

```
❌ 危險：遞迴 delegation
├── Fork children 不能 fork
├── Swarm peers 不能 spawn other peers
└── 防止指數級 fan-out
```

---

## 8. Hook Lifecycle（鉤子生命週期）⭐⭐⭐

### 問題
沒有 centralized hook lifecycle：trust enforcement 不一致、ordering 不確定、blocking 決策傳播混亂。

### 核心原則

```
All hooks flow through a single dispatch point
├── 信任檢查
├── Source 合併
├── Type 路由
└── 結果聚合
```

### Trust 是全有或全無

```python
# 在任何 hook 觸發之前檢查一次
if workspace.untrusted:
    skip_all_hooks()  # 不是只跳過可疑的，全部跳過
```

### Multi-source Merge Priority

```
Priority 高 → 低：
1. Persisted configuration (settings files)
2. SDK-registered callbacks
3. Session-scoped registrations

當 policy 限制時，整層排除而不是個別過濾。
```

### Exit Codes 語義

| Exit Code | 語義 |
|-----------|------|
| 0 | 成功 |
| 特定 blocking code | block + inject error message |
| 其他非零 | warn but don't block |

### Deny > Ask > Allow Precedence

```
當多個 hooks 返回衝突的 permission 決策：
deny > ask > allow > passthrough

單一 security-minded hook 可以否決所有 permissive hooks。
```

### 六種 Hook 類型

| 類型 | 使用時機 |
|------|---------|
| `command` | Shell-level side effects |
| `prompt` | Hook 本身需要 reasoning |
| `agent` | Full sub-agent delegation |
| `http` | External service integration |
| `callback` | Full structured output control |
| `function` | Lightweight boolean gate only |

### Session Hooks 是 Ephemeral

```
Hooks 綁定到特定 session ID，session 結束時自動清理。
不寫入持久化設定。
Parent session 的 hooks 不會在 sub-agent session 觸發。
```

---

## 9. Task Decomposition（任務分解）

### 問題
並發工作造成 shared state 碰撞、輸出腐敗、無法追蹤完成狀態。

### 核心原則

```
Every work unit gets a typed identity
├── Prefix encodes work type (agent/shell/remote/teammate)
├── Collision-resistant random suffix
└── ~2.8 trillion combinations per prefix
```

### State Machine

```
States: pending → running → completed/failed/killed
Terminal states are permanent。
用 canonical check function 而不是 inline 比較。
```

### 磁盤輸出 + 偏移量

```
記憶體只存 read offset。
輸出寫到 per-work-unit 檔案。
poll 時讀取 delta 並 atomically advance offset。
→ 記憶體佔用恆定，與工作時長無關
```

### 兩階段 Eviction

```
Phase 1 (Eager):  Terminal state 時磁盤檔案刪除
Phase 2 (Lazy):   Parent 收到通知後記憶體記錄才刪除

通知閘門是關鍵：否則 race condition。
```

---

## 10. Bootstrap Sequence（引導序列）

### 問題
安全關鍵初始化步驟執行順序錯誤：TLS 在第一個連接後才載入、proxy 在第一個 TCP 連接後才配置、trust-gated 子系統在同意之前就激活。

### 四層初始化順序

```
1. Config parsing（最先）
2. Safe env vars（無 secrets）
3. TLS CA certificates（任何網絡連接之前）
4. Graceful shutdown registration
5. mTLS configuration
6. Global HTTP agent
7. API preconnection
```

### Trust Boundary 是關鍵轉折點

```
安全敏感的子系統（telemetry, secret env vars）
必須在 trust 建立之後才能激活。
```

### Memoized Init

```python
# 併發 callers 共享同一個 promise，不會 double-init
init_promise = memoized_async_init()
# 而不是：
if not initialized:
    initialize()  # 可能並發執行兩次
```

### Trivial Commands Fast-path

```
在任何 dynamic import 之前檢查：
version, help, schema dump → 立即返回，零模組載入
```

### Cleanup 在 Init 註冊

```
所有 cleanup handlers 在初始化時註冊，不是分散在 usage sites。
確保所有 exit paths 都會執行清理。
```

---

## 11. Anthropic Multi-Agent Research（多智能體研究系統）⭐⭐⭐

> 資料來源：Anthropic 《How we built our multi-agent research system》
> + keli-wen 《Multi-Agent System，一篇就够了》解讀

### 核心發現

```
Claude Opus 4 (主) + Sonnet 4 (子) 多智能體系統
比單一 Opus 4 高出 90.2%

BrowseComp 評估：Token 使用量解釋 80% 的性能差異
```

### Why Multi-Agent：三大理由

| 理由 | 說明 |
|------|------|
| **非線性與湧現** | 單智能體有「隧道視野」，多智能體有「上帝視角」 |
| **Inference Compute Scaling** | 多智能體幾乎無上限的 token 容量 |
| **搜索即壓縮** | 「搜索即智能，從龐大語料庫中提取洞見」— Ilya |

**搜索即壓縮的本質：**
```
Sub-agents = 智能過濾器
↓ 消化大量原始資訊
↓ 提煉壓縮後的洞見（most important tokens）
Lead Agent 專注戰略規劃、邏輯推理、綜合決策
```

### Anthropic Research 架構

```
User Query
    ↓
Lead Researcher（規劃 + 記憶）+ Interleaved Thinking
    ↓ 委派（並行）
Subagents（各自獨立探索）
    ↓ 壓縮結果
Lead Researcher（綜合判斷）
    ↓ 是否繼續探索
CitationAgent（引用 + 輸出）
```

**Interleaved Thinking：** 在兩次工具呼叫之間插入思考步驟，評估上一步結果品質、識別資訊差距、動態調整下一步行動。

### 八條最佳實踐

#### 管理層面（主智能體）

| 原則 | 說明 |
|------|------|
| **有效授權** | Teach the orchestrator how to delegate。為 Sub-agent 提供明確的目標、格式、工具、邊界。避免模糊指令導致重複工作。 |
| **資源分配** | Scale effort to query complexity。簡單查詢用 1 個 agent + 3-10 次工具呼叫；複雜研究用 10+ subagents。 |

#### 執行層面（子智能體）

| 原則 | 說明 |
|------|------|
| **先廣後窄** | Start wide, then narrow down。模仿人類專家研究：先探索整體概况，再深入具體細節。避免默認過長、過於具體的查詢。 |
| **引導思考過程** | Guide the thinking process。使用擴展思考為智能體提供「草稿紙」，引入 Interleaved Thinking 動態調整。 |
| **並行工具呼叫** | Parallel tool calling。兩種並行化：(1) 主智能體並行啟動 3-5 個子智能體；(2) 子智能體並行使用 3+ 工具。複雜查詢研究時間減少 **90%**。 |

#### 細節層面（系統構建）

| 原則 | 說明 |
|------|------|
| **像智能體一樣思考** | Think like your agents。逐步觀察智能體工作，發現它在哪個環節出問題（過早停止、過於冗長搜索、選錯工具）。 |
| **工具設計至關重要** | Tool design and selection are critical。糟糕的工具描述會讓智能體走上完全錯誤的道路。明確的啟發式規則：先檢查所有可用工具、偏好專用工具而非通用工具。 |
| **賦予自我進化能力** | Let agents improve themselves。給定 Prompt 和失敗場景，模型能診斷失敗原因並提出改進建議。 |

### Prompt 啟示錄

```
核心原則：啟發式 > Hardcode

❌ 錯誤：將步驟 hardcode 成 if-else
✅ 正確：灌輸良好的啟發式方法（如何分解問題、如何解決）

複雜查詢的本質是動態的，無法用固定流程圖規劃所有步驟。
```

### 原型 → 產品：兩大挑戰

#### 評估（Evaluation）

```
不要等大型評估集才開始，立即用小樣本（~20 queries）開始。
任何 prompt 調整可能將成功率從 30% 提高到 80%。

LLM 作為評估者：事實準確性、引用準確性、完整性、來源質量、工具效率。
單一 LLM prompt 輸出一個評分結果，與人類判斷最接近。

必要時人工介入（如發現智能體傾向選擇 SEO 優化內容而非權威來源）。
```

#### 工程化（Engineering）

| 挑戰 | 對策 |
|------|------|
| **Stateful & Errors** | 斷點恢復系統、結合模型智能（告知工具失效）+ 工程確定性（重試邏輯、檢查點）|
| **Debugging** | 全鏈路追蹤（Full Production Tracing）：記錄每一步決策、工具呼叫、返回結果 |
| **Deployment** | 彩虹部署（Rainbow Deployments）：新舊版本並行，逐步切換流量 |
| **Bottlenecks** | 異步執行（未來方向）：當前同步模式被最慢的子智能體拖累 |

### 與 Agentic Harness Patterns 的對應

| Anthropic 概念 | Harness Pattern |
|---------------|----------------|
| 壓縮後提交 | Coordinator 必須綜合，不是委託 |
| Sub-agent 獨立上下文 | Isolate Pattern |
| Interleaved Thinking | Hook Lifecycle (pre/post tool hooks) |
| 斷點恢復 | Task Decomposition (disk-backed output, two-phase eviction) |
| 全鏈路追蹤 | Hook Lifecycle (logging hooks) |
| 資源分配 | Task Decomposition (typed IDs, effort scaling) |

## 12. Long-Running Agents（長運行代理）⭐⭐⭐

> 資料來源：Anthropic《Effective harnesses for long-running agents》

### 問題診斷

```
每個 session 都是 fresh start，沒有記憶。
代理兩大失敗模式：
1. 一次做太多（one-shot）→ 半成品堆積
2. 過早宣稱完成 → 功能未實現就結束
```

### 雙軌解決方案

| 角色 | 職責 |
|------|------|
| **Initializer Agent** | 首次運行建立 scaffold：feature_list.json、claude-progress.txt、init.sh、initial git commit |
| **Coding Agent** | 每個 session 只做一件事，完成後留乾淨的環境 |

### Feature List 設計

```json
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": ["Navigate to main interface", "Click the 'New Chat' button", ...],
  "passes": false
}
```

**關鍵原則：**
- JSON 格式（防止模型破壞結構）
- 永遠只改 `passes` field，不刪除或編輯測試
- 所有功能一開始標為 `failing`，完成後才改 `true`

### Coding Agent 標準流程

```
1. pwd（確認目錄）
2. 讀 git log + progress.txt（了解進度）
3. 讀 feature_list.json（選最高優先級未完成的）
4. 讀 init.sh（啟動開發伺服器）
5. End-to-end 測試（確保沒留下 bug）
6. 實現一個 feature
7. Git commit + 更新 progress
```

### 四大失敗模式對照表

| 問題 | Initializer 解法 | Coding Agent 解法 |
|------|-----------------|------------------|
| 過早宣稱完成 | 建立 feature list JSON | 每次只做一個，讀 list 選下一個 |
| 留下 bug 環境 | 建立 git + progress 機制 | 開始前先跑基本測試 |
| 測試不足就標 pass | 建立 feature list | 自我驗證後才改 passes |
| 花時間研究怎麼跑 app | 寫 init.sh | 每次從 init.sh 開始 |

### 測試關鍵

```
使用瀏覽器自動化工具（Puppeteer MCP）：
- 否則 Claude 無法識別「功能看起來正常但實際壞了」
- 必須像人類用戶一樣操作
```

### 與其他 Patterns 的對應

| 概念 | 對應 Pattern |
|------|-------------|
| Feature list = 外部化記憶 | Memory Persistence |
| 每次只做一件 | Task Decomposition |
| 乾淨的環境 | Isolate Pattern |
| init.sh 腳本 | Bootstrap Sequence |
| 測試驗證 | Tool & Safety (fail-closed) |

## 跨模式：共同主題

### 1. 枚舉勝過魔法
```
Typed IDs > string IDs
State machine > ad-hoc status
Canonical check function > inline comparisons
```

### 2. 兩階段勝過單階段
```
雙步儲存：topic file → index
兩階段 eviction：磁盤 → 記憶體
Bootstrap：config → trust → subsystems
```

### 3. 窄邊界是預設
```
Zero-inheritance > Full-inheritance
Local cleanup > Global GC
Fail-closed > Fail-open
```

### 4. 明確勝過隱式
```
Path translations must cover ALL file-operation tools
Memoize promises, not results
Trust is all-or-nothing, not gradual
```

---

## 對實際系統的啟示

### 設計檢查清單

```
□ 所有初始化步驟有明確的依賴順序嗎？
□ 並發 callers 會不會造成 double-init？
□ 環境變數有沒有 security implications？
□ Sub-agents 的 blast radius 受限嗎？
□ Hooks 有沒有 single dispatch point？
□ 長期工作有沒有 disk-backed output？
□ Eviction 有沒有 notification gate？
□ Cleanup handlers 在 init 註冊了嗎？
□ Local 覆蓋能勝過 organization 設定嗎？
□ 雙步儲存 invariant 成立了嗎？
```

---

## Gotchas 快速參考

| Pattern | Trap |
|---------|------|
| Memory | Index truncation is silent |
| Memory | Local overrides always win |
| Memory | Extraction timing creates race window |
| Memory | Don't store derivable content |
| Skills | Trigger language must be front-loaded |
| Select | Memoize promises, not results |
| Select | Invalidate at mutation site |
| Compress | Truncation needs recovery pointer |
| Isolate | Recursive forks = exponential cost |
| Isolate | Path translations must cover ALL tools |
| Isolate | Zero-inheritance prompts must be self-contained |
| Isolate | Merging isolated agents can conflict |
| Orchestration | Fork children cannot fork |
| Hooks | Trust gate blocks ALL hook types |
| Hooks | Missing script = same exit as intentional block |
| Hooks | Policy-restricted modes drop session hooks silently |
| Task | Don't evict before parent is notified |
| Task | Retained work units are never auto-evicted |
| Task | Update functions must not mutate existing state |
| Bootstrap | Memoization hides retry failures |
| Bootstrap | TLS cert store cached at boot |

---

## 參考文檔

- [Agentic Harness Patterns Repo](https://github.com/keli-wen/agentic-harness-patterns-skill)
- [Memory Persistence Pattern](references/memory-persistence-pattern.md) ✅
- [Skill Runtime Pattern](references/skill-runtime-pattern.md) ✅
- [Tool Registry Pattern](references/tool-registry-pattern.md) ✅
- [Permission Gate Pattern](references/permission-gate-pattern.md) ✅
- [Context Engineering Pattern](references/context-engineering-pattern.md) ✅
  - [Select Pattern](references/context-engineing/select-pattern.md) ✅
  - [Compress Pattern](references/context-engineing/compress-pattern.md) ✅
  - [Isolate Pattern](references/context-engineering/isolate-pattern.md) ✅
- [Agent Orchestration Pattern](references/agent-orchestration-pattern.md) ✅
- [Hook Lifecycle Pattern](references/hook-lifecycle-pattern.md) ✅
- [Task Decomposition Pattern](references/task-decomposition-pattern.md) ✅
- [Bootstrap Sequence Pattern](references/bootstrap-sequence-pattern.md) ✅
- [Isolate Pattern (context-engineering)](references/context-engineering/isolate-pattern.md) ✅
- [Anthropic Multi-Agent Research System](https://www.anthropic.com/engineering/built-multi-agent-research-system) ✅
- [Multi-Agent System 解讀（keli-wen）](https://keli-wen.github.io/One-Poem-Suffices/one-poem-suffices/multi-agent-system/) ✅
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) ✅

---

*研究日期：2026-04-17 | 閱讀進度：13/13 + Anthropic Multi-Agent + Long-Running ✅*
