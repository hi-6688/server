# 嗨嗨 (HiHi) - Discord 數位生命體專案 v6.0

這是一個具備「長期記憶」與「主觀意識」的 Discord 數位生命體專案。
本專案已全面進化為基於 **「雙階段認知管線 (Two-Stage Pipeline)」** 與 **「無狀態記憶 (Stateless)」** 的原生 SDK 架構。

本專案採用 **Vibecoding** 開發模式，並以 `docs/ai_rules/workflow.md` 作為 AI 協作最高指導原則。

---

### 🧠 核心認知架構 (Cognitive Architecture)

HiHi v6.0 採用目前業界最前沿的 Agent 設計模式，實現高效率與低延遲的數位靈魂：

1.  **兩階段認知管線 (Two-Stage Pipeline)**：使用 `google-genai` SDK 原生 `tools` 自動執行。將思考解耦為階段一 `LogicRouter` (邏輯與工具決策，輸出 `MemoryState`) 與階段二 `ChatGenerator` (擬態角色扮演，輸出 `PersonaResponse`)。
2.  **無狀態記憶引擎 (Stateless Runtime)**：捨棄易失憶且耗能的 RAM 變數。每次對話皆即時從資料庫撈取最新的客觀對話紀錄。
3.  **調閱原文檢索 (Reference-based RAG)**：當命中記憶時，系統會透過時間戳記自動調閱當時的「原始對話現場」上下文給 AI 參考，大幅提升回憶精度。
4.  **非同步與向量 L2 歸一化**：AI 對話、Embedding 向量化與 PostgreSQL 讀寫全面非同步化。針對 768 維截斷向量實作 L2 歸一化，防止檢索精度失真。

> 💡 關於詳細的 Pydantic Schema、RAG 向量數學與心跳機制規格，請參閱單一事實來源：[TECHNICAL_SPEC.md](file:///home/hi6688/servers/docs/TECHNICAL_SPEC.md)。

---

### 🌐 分體架構 (Split Architecture)

為了實現人格隔離與資源優化，專案採用「單一核心，多重人格」的架構。
透過 `.env` 中的 `BOT_MODE` 切換，同一個 codebase 可啟動三種完全獨立的 Systemd 守護進程：

| 模式 | 環境變數 | 對應服務 | 載入 Cogs | 用途 |
|---|---|---|---|---|
| **HIHI** | `BOT_MODE=HIHI` | `discord_bot.service` | `status`, `ai_chat` | **嗨嗨** (具備靈魂的數位生命體) |
| **CONCH** | `BOT_MODE=CONCH` | `conch_bot.service` | `status`, `minecraft`, `terraria`, `conch_game` | **神奇嗨螺** (功能與遊戲指令型) |
| **TEST** | `BOT_MODE=TEST` | `test_bot.service` | `status`, `vm_admin` | **測試雞** (全域 VM 後台直控管理) |

---

### 💾 記憶器官與底層技術 (Memory & Tech Stack)

*   **大腦皮層**: Google `gemini-3.1-flash-lite` (兼具速度與推理能力的主模型)
*   **記憶編碼器**: Google `gemini-embedding-2` (正式版，輸出 768 維 L2 歸一化向量)
*   **深層記憶庫**: Azure PostgreSQL
    *   **海馬迴**: `pgvector` 擴充套件 + `HNSW` 高速向量索引
    *   **混合檢索**: Cosine Similarity (向量) + BM25 (全文) + `RRF` 倒數排名融合演算法

---

### 📁 檔案架構 (Active File Architecture)

為了符合輕量化策略，以下僅列出**目前正在運行與維護中**的核心檔案。

```text
servers/
├── ROADMAP.md                   # P0~P3 開發藍圖與任務追蹤
├── CHANGELOG.md                 # 專案版本更新日誌
├── README.md                    # 本標準說明書
├── docs/                        # 專案說明與架構手冊
│   ├── HiHi_Proposal.md         # HiHi 機器人 AI 核心企劃書 (哲學與願景)
│   ├── TECHNICAL_SPEC.md        # [SSOT] 嗨嗨技術規格書 (Pydantic, 向量, 生理時鐘)
│   ├── COMMANDS.md              # 系統指令使用手冊
│   ├── ai_rules/
│   │   └── workflow.md          # AI 開發與工作流守則
│   └── archive/                 # 封存/停用模組之歷史文檔
├── discord_bot/                 # 🤖 Discord 機器人核心 (HiHi AI 專區)
│   ├── main.py                  # Bot 程式進入點 (分體架構啟動器)
│   ├── cogs/                    # 功能模組 (Cogs)
│   │   ├── ai_chat.py           # [核心] 嗨嗨的大腦 (雙階段管線, 心跳, 思考迴圈)
│   │   ├── status.py            # 基礎狀態回報
│   │   └── vm_admin.py          # [測試雞] 全域 VM 遙控器
│   ├── utils/                   # 共用工具
│   │   ├── memory_manager.py    # [核心] RAG 記憶器官 (PostgreSQL, Embedding)
│   │   └── gcp_manager.py       # GCP 雙 VM 架構底層控制 API
│   ├── data/                    # 靜態資料 (表情字典、憲法)
│   │   └── hihi/
│   │       ├── emojis.json          # Discord 自訂表情 ID 對照表
│   │       ├── emoji_meanings.json  # [義眼] 表情符號的語意翻譯字典
│   │       └── core_memory.md       # 嗨嗨的核心靈魂設定 (不可篡改)
│   └── scripts/                 # 維護工具箱 (資料庫稽核、Embedding 補齊)
└── plans/                       # 臨時計畫目錄 (過往計畫歸檔於 docs/archive/plans/)
```

---

### 🚀 環境與執行 (Deployment)

⚠️ **【硬體限制與營運現況聲明】**
由於目前硬體資源限制（VM1 降頻至 4GB RAM），且尚未租用新的 VPS，**本專案已拔除並關閉所有資源密集的 Web 管理介面與 Docker 容器**。
與遊戲伺服器相關的 **GCP VM2 (Minecraft)** 目前處於**無限期暫停營運與關機狀態**。全案資源目前完全專注於「嗨嗨機器人」核心 AI 的輕量化原生開發。

專案目前直接在虛擬機環境原生執行（Systemd），以達到最低的資源消耗 (RAM < 150MB)。

#### 1. 重新啟動機器人 (根據需要重啟特定人格)
```bash
sudo systemctl restart discord_bot.service   # 嗨嗨
sudo systemctl restart conch_bot.service     # 嗨螺
sudo systemctl restart test_bot.service      # 測試雞
```

#### 2. 檢視運行日誌與狀態
```bash
# 檢查狀態
systemctl status discord_bot.service

# 即時追蹤 AI 內心獨白與運作日誌
journalctl -u discord_bot.service -f
```

---

### 📝 開發進度與未來展望 (Roadmap)

詳細的技術指標與任務請參考 `ROADMAP.md` 以及 `docs/HiHi_Proposal.md`。

**近期已完成之重大革命 (v6.0)**:
- [x] **雙階段 Pydantic 認知管線**: 移除了自製 JSON 模擬，利用最新 SDK 原生 `tools` 自動執行管線。
- [x] **無狀態歷史轉型**: 拔除 `self.history` 狀態變數，歷史與 RAG 即時查詢。
- [x] **Embedding L2 歸一化修正**: 修正 768 維度截斷向量在 pgvector 中的檢索精度失真問題。
- [x] **非同步心跳引擎與遙測儀表板**: 背景生命迴圈與內心世界 Discord Embed 觀測台分段發射。

**下一步 (Next Steps)**:
- [ ] **全域 VM 管理資安優化**: 移除 `vm_admin.py` 的明文密碼，強化 GCP API 錯誤處理與防呆。
- [x] **文檔架構重構與 SSOT 整合**: 抽離重複描述，建立專屬技術規格書並防呆歸檔過期文檔。