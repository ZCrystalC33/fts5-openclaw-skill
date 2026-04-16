# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.4.0] - 2026-04-16

### 🎉 Agentic Harness Patterns 重構

基於 Claude Code 512,000 行原始碼萃取的生產級設計模式。

#### 雙步儲存 invariant (Two-Step Save Invariant)
- **核心原則**：寫入 topic file → 再更新 index
- **原因**：確保崩潰時 index 一致，孤立檔案無害
- **應用於**：`exchange_engine.py`, `fts5_integration.py`

#### 相互排斥 (Mutual Exclusion)
- **核心原則**：主代理寫入時，萃取代理跳過
- **實現**：`ExchangeLock` class，使用 `fcntl` 原子鎖
- **應用於**：`exchange_engine.py`, `context_predictor.py`

### ✅ 新增功能

#### exchange_engine.py 重構
- `ExchangeLock` class - 相互排斥鎖
- `two_step_save()` - 雙步儲存實現
- `topics/` 目錄 - 存放完整內容（溫層）
- `memory.md` 緊湊 - 超過 25KB 時自動壓縮
- `_append_to_memory_index()` - 安全的 index 更新
- `_compact_memory_index()` -  index 緊湊維護

#### fts5_integration.py 重構
- `main_agent_lock()` - 主代理寫入鎖
- `is_main_agent_active()` - 活性檢查
- `index_correction/preference/learning()` - 現在使用雙步儲存
- FTS5 logging = Step 1（權威記錄）
- File update = Step 2（衍生）

#### context_predictor.py 重構
- `is_main_agent_writing()` - 相互排斥檢查
- `should_defer` flag - 主代理忙碌時延遲記憶操作
- Just-in-time context loading（不 eager）
- 重構後避免在主代理寫入時執行heavy記憶操作

### 📚 知識庫更新

- `domains/harness-engineering.md` - 完整的 Harness Engineering 文章彙整
- `domains/agentic-harness-patterns.md` - Claude Code 模式深度研究
- 6 大設計模式：Memory, Skills, Tools, Context Engineering, Multi-agent, Lifecycle
- 11 個 Deep-dive References 摘要

### 🔧 Technical Details

#### ExchangeLock 實現
```python
class ExchangeLock:
    def __enter__(self):
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Returns False if lock held by main agent
        return acquired
```

#### Two-Step Save 實現
```python
# Step 1: 寫入 topic file
write_topic_file(topic_id, content)
# Step 2: 更新 index
append_to_memory_index(topic_id, summary)
```

## [1.3.0] - 2026-04-16

### 🎉 Major Improvements

#### Self-Improving Integration (Merged)
- **Combined installation** - FTS5 + Self-Improving in one repo
- **Automatic path detection** - Scripts detect existing ~/self-improving/ and preserve data
- **Bidirectional sync** - FTS5 ↔ memory synchronization

#### Harness Engineering Principles
- **FTS5 Linter** - Mechanical architectural enforcement (7 checks)
- **Pattern Registry** - Anti-patterns documented for automatic detection
- **Simplified AGENTS.md** - ~100 lines as table of contents

### ✅ Added

- `linter.py` - Architectural enforcement tool
  - Export validation
  - Hardcoded path detection
  - Script permission checks (755)
  - Path detection consistency
  - Layer dependencies check
  - Exchange engine rules validation
  - YOLO anti-pattern detection
- `self_improving/domains/patterns.md` - Pattern registry
- Bilingual README (Chinese primary, English secondary)

### 🔧 Improved

- **install.py** - Handles existing Self-Improving gracefully
- **exchange-cron.sh** - Proper permissions (755)
- **Path detection** - Consistent across all scripts
- **Documentation** - SKILL.md updated with full structure

## [1.2.0] - 2026-04-16

### 🎉 Major Improvements

#### Onboarding System
- **No hardcoded API keys** - All credentials are user-provided
- Interactive `setup.py` onboarding wizard
- `config.env.example` template for easy setup
- API key validation and connectivity test

#### Multi-Language Support
- Automatic language detection (zh-TW, zh-CN, en, ja)
- Language-specific prompts for LLM summarization
- Traditional vs Simplified Chinese differentiation

### ✅ Added

- `setup.py` - Interactive onboarding wizard
- `config.env.example` - Example configuration file
- `README_zh.md` - Traditional Chinese documentation
- `_get_api_key()` / `load_api_key()` - Centralized API key loading
- Sensitive data filter with masking
- 3-layer error recovery with fallback
- Rate limiting (10 calls/min)
- Incremental indexing with state tracking

### 🔒 Security

- Removed all hardcoded API keys
- All API keys user-provided via environment or config file
- Sensitive data auto-masking (API keys, tokens, private keys)

## [1.1.0] - 2026-04-15

### 🎉 Major Features

#### LLM Summarization
- MiniMax M2.7 integration
- Automatic summary generation
- Query-type detection (technical, status, preference, default)

#### Smart Prompts
- Technical query prompts (English terms preserved)
- Status query prompts (project progress)
- Preference query prompts (user preferences)
- Default prompts (general topics)

### ✅ Added

- `llm_summary.py` - LLM summarization module
- `rate_limiter.py` - Sliding window rate limiter
- Context length management based on query complexity

## [1.0.0] - 2026-04-14

### 🎉 Initial Release

#### Core Features
- SQLite FTS5 full-text search
- Conversation history indexing
- Basic search functionality
- Session file parsing (JSONL)

### ✅ Added

- `__init__.py` - Main module with search/summarize
- `indexer.py` - Session file indexer
- `SKILL.md` - OpenClaw skill definition
- Database schema with FTS5 virtual table

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 1.4.0 | 2026-04-16 | ✅ Current |
| 1.3.0 | 2026-04-16 | ✅ Previous |
| 1.2.0 | 2026-04-16 | ✅ Previous |
| 1.1.0 | 2026-04-15 | ✅ Previous |
| 1.0.0 | 2026-04-14 | ✅ Initial |

## Upgrade Notes

### Upgrading from v1.1.0 to v1.2.0

1. **API Key Required** - v1.2.0 requires user-provided API key
   - Set `MINIMAX_API_KEY` environment variable, or
   - Create `~/.openclaw/fts5.env` with your key

2. **Run setup** - Recommended after upgrade:
   ```bash
   python3 ~/.openclaw/skills/fts5/setup.py
   ```

### Upgrading from v1.0.0 to v1.1.0

- No special upgrade steps needed
- Just `git pull` and enjoy LLM summarization

---

## Statistics (as of v1.4.0)

- **Files**: 17+
- **Lines of Code**: ~4,500
- **Dependencies**: Python stdlib only (urllib, sqlite3, json, re, fcntl)
- **Supported Languages**: 4 (zh-TW, zh-CN, en, ja)
- **Error Recovery Layers**: 3
- **Linter Checks**: 7 (all passing)
- **Self-Improving Scripts**: 5
- **Design Patterns**: 6 (from Agentic Harness Patterns)
- **Knowledge Domains**: 3 (openclaw-fts5, patterns, harness-engineering)

## Future Plans

- [ ] ClawHub integration for one-command install
- [ ] Web dashboard for search analytics
- [ ] Additional LLM provider support (OpenAI, Anthropic)
- [ ] Conversation threading for context continuity
- [ ] Scheduled summarization reports