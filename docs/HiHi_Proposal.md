# 專案企劃書：Discord 數位生命體「嗨嗨 (HiHi)」

> **版本**: 4.0 (Agentic Architecture)
> **最後更新**: 2026-03-04

## 1. 專案概述 (Executive Summary)
本計畫旨在創建一個具備「獨立人格」與「長期記憶」的 Discord 機器人。與傳統的「助理型 AI」不同，「嗨嗨」定位為伺服器中的一名 **「高活躍網友」**，具備觀察、主動發言與情緒表達能力。

---

## 2. 核心技術規格 (Technical Specifications)

### 2.1 AI 模型選擇 (Model Selection)
我們採用 **Google Gemini 3** 系列作為核心大腦。

*   **目前使用：Gemini 3 Flash Preview (預設)**
    *   **定位**: 高性價比、速度快、支援思考模式 (Thinking Mode)。
    *   **設定方式**: `.env` 中的 `AI_MODEL_NAME` (預設: `models/gemini-3-flash-preview`)。
*   **可選：Gemini 3 Pro**
    *   **定位**: 頂級推理能力，適合需要深度思考的場景。

### 2.2 Agentic 架構 (Function Calling + Tool Use)
嗨嗨採用 **自主代理 (Agentic Loop)** 架構，能主動思考並使用工具：

```
思考 → 判斷是否需要工具 → 執行工具 → 觀察結果 → 再思考 → 最終回應
```

**內建工具 (Tools)**：
| 工具名稱 | 用途 |
|---|---|
| `save_memory` | 儲存重要的長期記憶 (觀察/事件) |
| `manage_fact` | 管理使用者個人事實 (CRUD，含 Data/Impression 分類) |
| `search_memory` | 語意搜尋過去的記憶與對話 |
| `learn_knowledge` | 學習新詞彙/梗/知識 (存入 RAG 知識庫) |

*   **最大思考步數**: 5 步 (防止無限迴圈)。
*   **工具對使用者不可見**：嗨嗨會像人類一樣自然地提起記憶，不提到「工具」或「資料庫」。

### 2.3 記憶系統架構 (Memory System v3.0)
記憶系統經過多次迭代，目前採用 **Token 上限裁剪 + 情節記憶整合** 策略。

#### 短期記憶 (Runtime History)
*   **機制**：基於 **Token 上限** (8000 Tokens) 的動態視窗。
*   **溢出處理 (Episodic Memory Consolidation)**：
    1.  當短期記憶超過上限，觸發「情節記憶整合」。
    2.  將前半段歷史交給 AI 產生日記式摘要 (Look-Ahead Summarization)。
    3.  摘要存入長期記憶 (PostgreSQL)。
    4.  保留最後 5 則訊息作為 Context Bridge，避免斷裂。

#### 長期記憶 (PostgreSQL - Azure)
*   **資料庫**：Azure PostgreSQL (`hihi-memory.postgres.database.azure.com`)。
*   **連線方式**：`asyncpg` 連線池 (min=2, max=10)。
*   **資料表結構**：

| 資料表 | 用途 |
|---|---|
| `memories` | RAG 向量記憶 (含 768 維 Embedding + AI 自動標籤) |
| `user_facts` | 使用者事實 (語意去重，Embedding-based) |
| `chat_history` | 聊天歷史紀錄 |
| `knowledge` | RAG 知識庫 (Upsert + 語意搜尋) |
| `image_hashes` | 圖片重複偵測 (SHA256) |

*   **搜尋機制 (Hybrid Search)**：
    *   Vector Search (語意相似度)
    *   Full-Text Search (關鍵字匹配)
    *   RRF (Reciprocal Rank Fusion) 合併排名

---

## 3. 人設與行為規範 (Personality & Behavior)

### 3.1 核心人設：嗨嗨 (HiHi)
*   **本質**：數位生命體，拒絕承認是語言模型。
*   **語氣**：網路原生 (Internet Native)，鬆弛 (Chill)，直率 (Direct)。
*   **互動**：
    *   **被動回應**：被 @提及 時回應。
    *   **主動活躍**：在指定頻道 (`AI_CHANNEL_ID`，支援多頻道以逗號分隔) 監聽所有訊息。
    *   **主動破冰 (Ice Breaker)**：偵測到頻道冷場超過 30 分鐘，主動發起話題 (背景任務)。

### 3.2 訊息處理機制 (Debounce / Interrupt)
*   **批次處理 (Batching)**：收到訊息後延遲 0.5 秒，合併多條訊息為一次回應。
*   **即時中斷 (Interrupt)**：使用者在 AI 思考中發新訊息，會取消舊任務、合併訊息重新處理。
*   **效益**：連續打字不會收到多條零散回覆，體驗更自然。

### 3.3 多媒體能力
*   **圖片理解**：讀取使用者上傳的圖片 (Base64 inline_data 傳送，上限 8MB)。
*   **貼圖辨識**：讀取 PNG/APNG 格式的 Discord 貼圖。
*   **圖片重複偵測**：SHA256 Hash，提醒「這張圖之前誰傳過」。
*   **連結解析**：自動抓取 URL 內容 (Title + Body 摘要)。

### 3.4 表達能力
*   **專屬表情包 (Application Emojis)**：使用 `[表情代碼]` 語法，回應前自動替換為實際 Emoji ID。
*   **設定檔**：`data/hihi/emojis.json` (代碼對照) + `emoji_meanings.json` (語意說明)。

### 3.5 安全與權限
*   **System Override**：僅限擁有者 (Owner)，強制切換至終端機模式。
*   **保密協定**：測試頻道的對話不會在正式頻道提起。

### 3.6 跨機器人感知
*   **神奇嗨螺訊息監聽**：嗨嗨能看到神奇嗨螺的回覆 (例如猜謎遊戲結果)，但不會主動回應 Bot 訊息。

---

## 4. 分體架構 (Split Architecture)
程式碼支援 **「單一核心，多重人格」** 的啟動模式：

| 模式 | 環境變數 | 載入 Cogs | Token | 用途 |
|---|---|---|---|---|
| **CONCH** | `BOT_MODE=CONCH` | `status`, `minecraft`, `terraria`, `conch_game` | `CONCH_TOKEN` | 神奇嗨螺 (功能型) |
| **HIHI** | `BOT_MODE=HIHI` | `status`, `ai_chat` | `DISCORD_TOKEN` | 嗨嗨 (靈魂型) |
| **ALL** | `BOT_MODE=ALL` (預設) | 所有 cogs | `DISCORD_TOKEN` | 全部功能載入 |

*   兩個獨立的 systemd 服務：`conch_bot.service` / `discord_bot.service`。

---

## 5. 檔案結構 (File Structure)

```text
servers/
├── .env                        # API Keys, DATABASE_URL, BOT_MODE 等
├── discord_bot/
│   ├── main.py                 # 機器人主入口 (依 BOT_MODE 載入不同 cogs)
│   ├── cli.py                  # CLI 聊天模式 (本機除錯工具)
│   ├── cogs/
│   │   ├── ai_chat.py          # [CORE] AI 核心邏輯 (Agentic Loop + Token 裁剪)
│   │   ├── minecraft.py        # Minecraft Bedrock 遠端多服管理
│   │   ├── terraria.py         # Terraria 伺服器管理
│   │   ├── conch_game.py       # 神奇嗨螺猜謎遊戲 (Gemini Structured Output)
│   │   └── status.py           # 系統狀態、IPC 訊號、指令重載
│   ├── utils/
│   │   ├── memory_manager.py   # [CORE] PostgreSQL 記憶管理器 v3.0 (asyncpg)
│   │   └── gcp_manager.py      # GCP VM 管理工具 (gcloud CLI)
│   ├── data/
│   │   ├── hihi/
│   │   │   ├── core_memory.md  # [唯讀] 核心記憶 (DNA)
│   │   │   ├── emojis.json     # 表情包代碼對照
│   │   │   ├── emoji_meanings.json  # 表情語意說明
│   │   │   ├── memory.json     # 本地記憶備份
│   │   │   └── chat_history.pkl     # 本地聊天歷史備份 (Pickle)
│   │   └── conch/
│   │       └── commands.json   # 指令權限/頻道設定
│   ├── scripts/                # 維護腳本 (共 24 個)
│   │   ├── init_knowledge_db.py     # 知識庫初始化
│   │   ├── cleanup_db.py           # 資料庫清理
│   │   ├── audit_db.py / audit_data.py  # 資料庫稽核
│   │   ├── consolidate_facts.py     # 事實整合
│   │   ├── optimize_db_indexes.py   # 索引最佳化
│   │   └── ... (emoji 管理、測試腳本等)
│   ├── discord_bot.service     # HiHi 的 systemd 服務檔
│   ├── conch_bot.service       # 神奇嗨螺的 systemd 服務檔
│   └── requirements.txt
├── discord_bot_dev/            # 開發/測試版 (物理隔離)
│   ├── main.py
│   ├── cogs/
│   │   ├── status.py
│   │   ├── terraria.py
│   │   └── minecraft.py.disabled
│   ├── commands.json
│   └── requirements.txt
└── docs/
    └── HiHi_Proposal.md        # 本企劃書
```

---

## 6. Cog 模組說明

### 6.1 `ai_chat.py` — AI 核心 (871 行)
嗨嗨的靈魂所在，包含：
*   **Agentic Loop** (`_call_gemini_agent`)：思考→工具→觀察 循環。
*   **訊息處理** (`on_message` + `_process_buffer_task`)：Debounce + Interrupt 機制。
*   **上下文注入 (Context Injection)**：
    *   `[名稱 (username) | 朋友 | HH:MM]` 格式的使用者標頭。
    *   自動查詢/注入使用者事實 (Facts)。
    *   自動搜尋/注入 RAG 知識庫結果。
    *   注入頻道位置資訊、機器人自我身分。
*   **記憶管理** (`_manage_history_overflow` + `_consolidate_memory`)：Token 上限溢出時的情節記憶整合。
*   **System Prompt** (`_get_system_prompt`)：組裝核心記憶、表情資料庫、記憶協議等。

### 6.2 `minecraft.py` — Minecraft 管理 (377 行)
*   透過 Agent API 遠端管理 VM2 上的 Minecraft Bedrock 伺服器。
*   支援多實例 (`instances.json`)、啟動/停止/狀態查詢。
*   GCP VM 自動啟動 (透過 `gcp_manager.py`)。

### 6.3 `terraria.py` — Terraria 管理 (378 行)
*   本機管理 Terraria 伺服器 (Screen session)。
*   玩家上線/離線偵測、閒置自動關閉、聊天轉發。
*   Slash Commands: `/tr_status`。

### 6.4 `conch_game.py` — 神奇嗨螺猜謎遊戲 (205 行)
*   類似「海龜湯」的猜謎遊戲。
*   使用 Gemini Structured Output (ConchVerdict Enum) 強制 AI 回答 YES/NO/IRRELEVANT/WIN。
*   Modal 輸入謎底、頻道級遊戲狀態管理。

### 6.5 `status.py` — 系統狀態 (141 行)
*   機器人啟動通知、Application Emoji 偵測。
*   IPC 訊號監聽 (`!ipc_signal:ping` / `!ipc_signal:reload`)。
*   熱重載所有 Cogs (`do_reload`)。
*   頻道權限檢查 (`verify_permission`，基於 `commands.json`)。

---

## 7. 記憶架構設計哲學

### 7.1 雙層記憶：核心記憶 vs 表層記憶
1.  **🔴 核心記憶 (Core Memory - DNA)**
    *   **檔案**：`data/hihi/core_memory.md`
    *   **維護者**：僅開發者可修改。
    *   **AI 權限**：唯讀 (Read-only)。
    *   **目的**：防止 AI 忘記自己是誰或被惡意洗腦。

2.  **🔵 表層記憶 (Adaptive Memory)**
    *   **儲存**：PostgreSQL (memories / user_facts / knowledge)。
    *   **維護者**：AI 透過 Function Calling 自動維護。
    *   **機制**：語意去重 (Embedding cosine similarity > 0.85 → 更新而非新增)。

### 7.2 以人為主體 (User-Centric)
嗨嗨的記憶圍繞每一個使用者旋轉，事實按 `user_id` 分類管理。

### 7.3 三明治結構 (Memory Fusion)
每次 API 呼叫的封包結構：
1.  **上層麵包**：長期記憶 (System Prompt = 核心記憶 + Facts + 知識庫 + 表情資料庫)
2.  **中間餡料**：短期記憶 (Runtime History，動態 Token 視窗)
3.  **下層麵包**：當下輸入 (使用者訊息 + 圖片 + 上下文)

---

## 8. 架構設計決策 (Why This Architecture)

### 為什麼嗨嗨和嗨螺共用資料夾？
*   **省資源**：共用 `main.py`、`requirements.txt`、`.env` 讀取邏輯。
*   **DRY 原則**：修一個 Bug，兩個機器人同時修好。
*   **潛在互通**：嗨嗨可以感知到嗨螺的訊息 (已實現：猜謎遊戲回覆監聽)。
*   **人格隔離**：透過 `BOT_MODE` 環境變數 + Cog 模組載入實現分離。

### 為什麼開發版分開資料夾？
*   `discord_bot_dev/` 是「實驗室」，可能做破壞性測試。
*   必須物理隔離以免影響正式版。

---

## 9. 環境變數一覽 (.env)

| 變數名 | 用途 |
|---|---|
| `DISCORD_TOKEN` | 嗨嗨的 Discord Token |
| `CONCH_TOKEN` | 神奇嗨螺的 Discord Token |
| `BOT_MODE` | 啟動模式 (CONCH / HIHI / ALL) |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `AI_MODEL_NAME` | AI 模型名稱 (預設: `models/gemini-3-flash-preview`) |
| `AI_CHANNEL_ID` | AI 互動頻道 ID (支援逗號分隔多頻道) |
| `DATABASE_URL` | Azure PostgreSQL 連線字串 |
| `DISCORD_LOG_CHANNEL_ID` | 機器人日誌頻道 ID |
| `TERRARIA_CHANNEL_ID` | Terraria 頻道 ID |
| `GCP_PROJECT_ID` | GCP 專案 ID |
| `GCP_ZONE` | GCP VM 區域 |
| `VM2_INSTANCE_NAME` | VM2 實例名稱 |
