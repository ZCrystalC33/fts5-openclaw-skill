<!-- last_access: 2026-04-16 -->

# OpenClaw FTS5 系統 - 發布版本 v1.2.0

## ✅ 已完成：無 Token + Onboarding 方案

### 安全原則
- ❌ 禁止：Token 寫死在程式碼
- ✅ 允許：使用者自行填入 / 環境變數

### Onboarding 流程

```
1. 安裝
   git clone ... ~/.openclaw/skills/fts5

2. 複製設定檔
   cp config.env.example ~/.openclaw/fts5.env
   # 編輯並填入自己的 API Key

3. 執行安裝精靈
   python3 ~/.openclaw/skills/fts5/setup.py
   # 互動式引導，驗證 API 連線

4. 完成！
```

### API Key 讀取優先級

| 優先級 | 來源 |
|--------|------|
| 1 | `MINIMAX_API_KEY` 環境變數 |
| 2 | `~/.openclaw/fts5.env` |
| 3 | `~/.openclaw/config.json` |

### 發布 GitHub 所需檔案

```
fts5-openclaw-skill/
├── SKILL.md              # 技能說明
├── __init__.py           # 主模組（無 Token）
├── llm_summary.py         # LLM 摘要（無 Token）
├── rate_limiter.py        # 頻率限制
├── error_handling.py      # 錯誤處理
├── indexer.py            # 增量索引器
├── sensitive_filter.py   # 敏感資料過濾
├── setup.py              # Onboarding 精靈 ⭐
├── config.env.example     # 範例設定檔 ⭐
├── README.md             # 完整使用說明
└── LICENSE               # MIT License
```

### 發布檢查清單

- [x] 移除所有 hardcoded API Key
- [x] 建立 setup.py 互動式安裝
- [x] 建立 config.env.example
- [x] 更新 SKILL.md 說明
- [ ] 測試乾淨安裝流程
- [ ] 建立 GitHub Repo
- [ ] 填入真實使用說明

### 版本歷史

- v1.0.0: 基礎 FTS5 搜尋
- v1.1.0: LLM 摘要功能
- v1.2.0: **無 Token + Onboarding** ⭐