# 麥亂伺服器專案 (Minecraft & Terraria Server Automation)

這是一個整合 Minecraft (Bedrock) 與 Terraria 伺服器的管理專案，包含自動化腳本、Discord 機器人與 Web 管理介面。
本專案採用 **Vibecoding** 架構，並以 `.agent/rules/readrules.md` 作為 AI 核心大腦。

### I. 📁 檔案結構全覽 (Project File Structure)

```text
servers/
├── .agent/                 # Agent 相關設定與自動化工作流
│   ├── rules/              # 存放 AI 核心大腦原則 (包含 readrules.md)
│   └── workflows/          # 存放 AI 自動化 SOP 腳本 (例如 update_readme.md)
├── backups/                # 伺服器或專案歷史備份集中區
├── CardGame_Project/       # 卡牌對戰遊戲專案 (Godot 前端 + FastAPI 後端)
├── COMMANDS.md             # 記錄專案常用終端機指令的說明文件
├── configs/                # 各項微服務與專案共用的設定檔目錄
├── discord_bot/            # 🤖 正式版 Discord 機器人核心目錄 (穩定、嚴格權限)
├── discord_bot_dev/        # 🧪 測試版 Discord 機器人目錄 (開發用、安全模式)
├── docs/                   # 專案說明與架構手冊存放區 (FRONTEND_ARCH, BACKEND_API 等)
├── instances/              # 遊戲伺服器實體或相關檔案存放目錄
├── minecraft/              # ⛏️ Minecraft Bedrock 伺服器核心
├── oneblock/               # 測試用：One Block Minecraft 伺服器目錄
├── scripts/                # 工具箱：收納所有的 Python 腳本 (強制同步、測試連線等)
├── steamcmd/               # SteamCMD 遊戲伺服器下載與更新工具
├── terraria/               # 🌳 Terraria 遊戲伺服器核心
├── tmp_oneblock/           # 測試用：One Block Minecraft 伺服器解壓縮暫存目錄
├── web_interface/          # 🌐 網頁管理介面前後端 (Python FastAPI + HTML/JS，Vite)
├── README.md               # 專案主要的標準說明書與目錄樹 (本檔案)
└── ROADMAP.md              # 專案中長期的開發規劃與路線圖
```
*(已清理：舊版的日誌、殘留的 SQL Session 與備份檔皆已移至適當位置或刪除)*

### II. 🚀 環境與執行 (Quick Start - Docker First)

本專案強烈推崇使用 Docker 進行環境隔離與開發。
如果您已有對應的 `docker-compose.yml`，可以直接使用以下指令啟動：

```bash
docker-compose up --build -d
```
> **成功訊號**：容器啟動後，使用 `docker ps` 確認狀態。網頁介面通常在 `http://<IP>:24445` (或 8888) 運行，Discord 機器人將在背景連線。

*(若尚未撰寫 docker-compose，原生的啟動方式為 `nohup python3 web_interface/api.py &` 與 `python3 discord_bot/main.py`)*

### III. 📝 開發進度 (Dev Log)

- [x] 導入 Vibecoding 架構，建立 `.agent/` 與 `docs/` 雙層大腦。
- [x] 將散落於根目錄的測試腳本 (`hihi.sh`, `force_sync.py` 等) 乾淨收納至 `scripts/`。
- [x] 將備份地圖檔與大型壓縮檔轉移至 `backups/` 或外部雲端空間以免佔用 Git 追蹤。
- [ ] 撰寫 Dockerfile 與 docker-compose.yml 實作容器化目標。
- [ ] 統一管理所有的連線與 Secret variables 到 `.env` 當中，確保資安安全。
