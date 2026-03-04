# 麥亂伺服器專案 (Minecraft & Terraria Server Automation)

這是一個整合 Minecraft (Bedrock) 與 Terraria 伺服器的管理專案，包含自動化腳本、Discord 機器人與 Web 管理介面。
本專案採用 **Vibecoding** 架構，並以 `.agent/rules/readrules.md` 作為 AI 核心大腦。

### I. 📁 檔案結構全覽 (Project File Structure)

```text
servers/
├── .agent/                     # Agent 相關設定與自動化工作流
│   ├── rules/                  # 存放 AI 核心大腦原則 (包含 readrules.md)
│   └── workflows/              # 存放 AI 自動化 SOP 腳本 (例如 update_readme.md)
├── backups/                    # 伺服器或專案歷史備份集中區
├── CardGame_Project/           # 卡牌對戰遊戲專案 (Godot 前端 + FastAPI 後端，暫緩開發)
├── configs/                    # 各項微服務與專案共用的設定檔目錄 (預留給 Docker 使用)
├── discord_bot/                # 🤖 Discord 機器人核心目錄 (雙模式：HiHi AI + 神奇嗨螺)
│   ├── main.py                 # 機器人主入口，依 BOT_MODE 載入不同 cogs
│   ├── cogs/                   # 功能模組 (ai_chat, minecraft, terraria, conch_game 等)
│   ├── utils/                  # 工具函式 (memory_manager.py 連接 Azure PostgreSQL)
│   ├── data/                   # 機器人運作資料 (hihi/ 記憶體、emojis 等)
│   ├── scripts/                # 機器人專屬工具腳本
│   ├── discord_bot.service     # HiHi AI 機器人的 systemd 服務檔
│   └── conch_bot.service       # 神奇嗨螺機器人的 systemd 服務檔
├── discord_bot_dev/            # 🧪 測試版 Discord 機器人目錄 (開發用、安全模式)
├── docs/                       # 📚 專案說明與架構手冊存放區
│   ├── FRONTEND_ARCH.md        # 前端架構規範 (React/Vite + Glassmorphism)
│   ├── BACKEND_API.md          # 後端 API 文件
│   ├── VM_ARCHITECTURE.md      # GCP 雙 VM 架構文件
│   └── HiHi_Proposal.md       # HiHi 機器人企劃書 (Azure PostgreSQL 記憶系統)
├── instances/                  # 遊戲伺服器實體或相關檔案存放目錄
├── minecraft/                  # ⛏️ Minecraft Bedrock 伺服器核心
├── oneblock/                   # 測試用：One Block Minecraft 伺服器目錄
├── scripts/                    # 工具箱：收納所有的 Python 腳本 (強制同步、測試連線等)
├── steamcmd/                   # SteamCMD 遊戲伺服器下載與更新工具
├── terraria/                   # 🌳 Terraria 遊戲伺服器核心
├── tmp_oneblock/               # 測試用：One Block Minecraft 伺服器解壓縮暫存目錄
├── web_interface/              # 🌐 網頁管理介面前後端
│   ├── api.py                  # 後端 API 入口 (路由分發器, ~290 行)
│   ├── models.py               # 資料模型 (Instance + InstanceManager)
│   ├── routes/                 # 路由處理模組 (依功能分檔)
│   │   ├── auth.py            # 登入驗證
│   │   ├── server.py           # 開機/關機/指令/狀態
│   │   ├── instances.py        # 多實例管理
│   │   ├── files.py            # 設定檔讀寫
│   │   ├── worlds.py           # 世界地圖管理
│   │   └── addons.py           # 模組管理
│   ├── helpers/                # 工具函式 (pack_installer, level_utils)
│   ├── remote_api.py           # 遠端 VM2 API 代理
│   ├── proxy_helpers.py        # 代理工具函式
│   ├── instances.json          # 伺服器實例設定
│   ├── admin_config.json       # API Key 設定
│   ├── schema.json             # API Schema
│   ├── frontend/               # React + Vite 前端專案
│   │   └── src/
│   │       ├── App.jsx         # 主入口 (頂部導航 + 居中單欄佈局)
│   │       ├── index.css       # 全域 Tailwind + 透明玻璃 CSS
│   │       ├── components/     # React 組件
│   │       │   ├── TopNav.jsx       # 頂部雙層導航列
│   │       │   ├── Dashboard.jsx    # 狀態儀表板 + 資訊卡片
│   │       │   ├── LiveConsole.jsx   # 嵌入式即時終端機
│   │       │   ├── ConsolePage.jsx   # 獨立終端機頁面
│   │       │   ├── PlayersPage.jsx   # 白名單與權限管理
│   │       │   ├── FilesPage.jsx     # 世界與模組管理
│   │       │   └── SettingsPage.jsx  # 伺服器設定編輯
│   │       └── utils/api.js    # 前端 API 通訊層
│   ├── legacy/                 # 舊版 Vanilla HTML/JS 前端 (已廢棄，僅存檔)
│   └── scripts/                # 偵錯與工具腳本
├── mc_agent.service            # Minecraft Agent 的 systemd 服務檔
├── COMMANDS.md                 # 專案常用終端機指令說明文件
├── README.md                   # 專案主要的標準說明書與目錄樹 (本檔案)
└── ROADMAP.md                  # 專案中長期的開發規劃與路線圖
```

### II. 🚀 環境與執行 (Quick Start - Docker First)

本專案強烈推崇使用 Docker 進行環境隔離與開發。
如果您已有對應的 `docker-compose.yml`，可以直接使用以下指令啟動：

```bash
docker-compose up --build -d
```
> **成功訊號**：容器啟動後，使用 `docker ps` 確認狀態。網頁介面通常在 `http://<IP>:24445` (或 8888) 運行，Discord 機器人將在背景連線。

*(若尚未撰寫 docker-compose，原生的啟動方式為 `nohup python3 web_interface/api.py &` 與 `python3 discord_bot/main.py`)*

**前端開發模式：**
```bash
cd web_interface/frontend
npm install
npm run dev -- --host
```
> 開發伺服器啟動於 `http://localhost:5173`，支援 Hot Reload。

### III. 📝 開發進度 (Dev Log)

- [x] 導入 Vibecoding 架構，建立 `.agent/` 與 `docs/` 雙層大腦。
- [x] 將散落於根目錄的測試腳本 (`hihi.sh`, `force_sync.py` 等) 乾淨收納至 `scripts/`。
- [x] 將備份地圖檔與大型壓縮檔轉移至 `backups/` 或外部雲端空間以免佔用 Git 追蹤。
- [x] 統一管理所有的連線與 Secret variables 到 `.env` 當中，確保資安安全。
- [x] Web 前端從 Vanilla HTML/JS 轉型為 **React + Vite** 架構。
- [x] 拆分 `App.jsx` 為獨立組件 (TopNav, Dashboard, LiveConsole 等 7 個組件)。
- [x] 建立 API 通訊層 (`src/utils/api.js`) 連接後端。
- [x] 清理 `web_interface/` 目錄：舊版歸檔至 `legacy/`、腳本歸類至 `scripts/`。
- [x] 後端 `api.py` 從 1012 行單體重構為模組化架構 (`models.py` + `routes/` + `helpers/`)。
- [x] 完善 Web 介面：Players (白名單) / Files (世界管理) / Settings (設定編輯) 頁面。
- [x] UI 重新設計：從側邊欄改為頂部導航、透明玻璃風格、Noto Sans TC 字體。
- [x] GCP 雙 VM 架構遷移：Minecraft 伺服器遷至 VM2、VM1 保留控制面板與 Bot。
- [x] 頂部導航 Logo 狀態指示燈綁定 VM2 即時線上/離線狀態。
- [x] 事件驅動自動安全關機：VM2 無人在線 10 分鐘後自動存檔並斷電（背景線程監聽日誌 + 智慧進程監控）。
- [x] 離線設定備份：關機前自動備份設定檔至 VM1 快取，離線時網頁仍可讀取與編輯設定。
- [ ] 撰寫 Dockerfile 與 docker-compose.yml 實作容器化目標。
- [ ] 將前端假資料逐步替換為真實後端 API。
