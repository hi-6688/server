# HiHi Project - 專案檔案架構指南

本文件記錄了 Discord 數位生命體「嗨嗨 (HiHi)」與「神奇嗨螺 (Conch)」專案的整體檔案目錄與模組架構，以便開發者日後維護與擴充。

---

## 📂 檔案目錄樹 (Project File Tree)

```text
servers/ (專案根目錄)
├── .vscode/                 # VS Code 工作區與調試設定
├── configs/                 # 系統全域設定檔目錄
├── discord_bot/             # Discord Bot 機器人主程式
│   ├── cogs/                # Bot 的功能模組 (Cogs)
│   │   ├── ai_chat.py       # AI 核心聊天人格 (HiHi) - 包含與 Gemini 互動的 Agent 邏輯
│   │   ├── conch_game.py    # 神奇嗨螺趣味猜謎遊戲 (Conch)
│   │   ├── minecraft.py     # Minecraft 伺服器狀態監控與通知 (Conch)
│   │   ├── status.py        # VM/Bot 系統資源狀態監控
│   │   ├── terraria.py      # Terraria 伺服器狀態監控 (Conch)
│   │   └── vm_admin.py      # GCP VM 雲端主機管理與控制 (Test)
│   ├── data/                # Bot 的本地資料暫存 (Emoji 對照、每日配額 Ledger 等)
│   ├── utils/               # 共用工具程式
│   │   ├── bds_updater.py   # Minecraft Bedrock 伺服器更新工具
│   │   ├── gcp_manager.py   # GCP 虛擬主機控制 SDK 封裝
│   │   └── memory_manager.py# 記憶管理器 (PostgreSQL 連結池, Hybrid RAG, Facts)
│   ├── cli.py               # 本地控制台命令行工具
│   ├── main.py              # Discord Bot 啟動主入口 (處理分體架構 Split Architecture)
│   └── requirements.txt     # Python 依賴套件清單
├── docs/                    # 專案企劃書與架構設計文檔
│   ├── BACKEND_API.md       # 後端 API 說明
│   ├── FRONTEND_ARCH.md     # 前端架構說明
│   ├── GLOBAL_DEPLOYMENT.md # 部署手冊
│   ├── HiHi_Proposal.md     # 專案核心企劃書
│   ├── HiHi_Proposal.mmd    # 企劃架構圖 (Mermaid)
│   └── PROJECT_STRUCTURE.md # 本專案檔案架構指南 (NEW)
├── scripts/                 # 資料庫維護、遷移與系統測試腳本
├── web_interface/           # Web 管理後台 (部分功能已關閉，轉移至 Discord/CLI 處理)
├── .env.example             # 環境變數範本檔
├── docker-compose.yml       # Docker 容器化配置
└── README.md                # 專案快速入門與開發須知
```

---

## ⚙️ 核心模組職責說明 (Module Responsibilities)

### 1. [main.py](file:///home/hi6688/servers/discord_bot/main.py)
*   **職責**：專案啟動入口。
*   **關鍵邏輯**：
    *   根據環境變數 `BOT_MODE`（CONCH / HIHI / TEST / ALL）動態加載對應的 Cogs，落實「分體架構（Split Architecture）」，使同一套程式碼可以跑不同人格的機器人。
    *   負責 Discord Slash Commands 的註冊與清理（先複製到 Guild 再清理全域，加速測試同步）。

### 2. [cogs/ai_chat.py](file:///home/hi6688/servers/discord_bot/cogs/ai_chat.py)
*   **職責**：AI 嗨嗨的人格與對話引擎。
*   **關鍵邏輯**：
    *   使用 Google GenAI SDK 與 `gemini-3.1-flash-lite` 互動。
    *   定義 `AgentResponse` 的 Pydantic Schema，引導 AI 輸出包含「心理 OS、情況分析、呼叫工具、休眠秒數與最終發言」的 JSON 資料。
    *   處理 Discord 訊息的批次與即時中斷 (Debounce / Interrupt)。
    *   負責內心世界觀測台（Telemetry Channel）的字卡推送。

### 3. [utils/memory_manager.py](file:///home/hi6688/servers/discord_bot/utils/memory_manager.py)
*   **職責**：HiHi 的三層式記憶中樞。
*   **關鍵邏輯**：
    *   管理 PostgreSQL (`asyncpg`) 連線池。
    *   **L3 長期記憶 (Memories)**：使用 `pgvector` 與 RRF 混合檢索（Hybrid Search）實現語意搜尋，並帶有時光機上下文回歸（Context Retrieval）。
    *   **核心事實 (Facts)**：對特定使用者進行語意去重 (Semantic Dedup) 及模糊刪除。
    *   **知識庫 (Knowledge)**：管理/ Upsert 對話中的特定詞彙與梗。
    *   **重複圖片偵測**：記錄 SHA256 圖片雜湊。
