# 練習全端開發用專案

這是一個整合 Minecraft (Bedrock) 與 Terraria 伺服器的管理專案，包含自動化腳本、Discord 機器人與 Web 管理介面。這一切是我用來練習開發的專案。
本專案採用 **Vibecoding** 架構，並以 `.agent/rules/readrules.md` 作為 AI 核心大腦。

---

### 🌐 雲端架構圖 (Hybrid Cloud Architecture)

本專案採用跨雲端協作架構，實現運算與邏輯的分離：

*   **🧠 GCP VM1 (The Brain)**: 執行 Web 面板、Discord 機器人 (HiHi / Conch)。[Docker 部署]
*   **💪 GCP VM2 (The Muscle)**: 執行遊戲伺服器 (MC/TR)、Remote Agent。[原生部署]
*   **🔵 Azure PostgreSQL**: 存放「嗨嗨」AI 的長期記憶與 RAG 向量數據。

---

### I. 📁 檔案結構全覽 (Project File Structure)

```text
servers/
├── .agent/                     # Agent 相關設定與自動化工作流
├── backups/                    # 伺服器或專案歷史備份集中區
├── configs/                    # 各項微服務與專案共用的設定檔目錄 (預留給 Docker 使用)
├── discord_bot/                # 🤖 Discord 機器人核心 (HiHi AI + 神奇嗨螺)
├── docs/                       # 📚 專案說明與架構手冊存放區
│   ├── GLOBAL_DEPLOYMENT.md    # [NEW] 雲端與本地全域部署圖
│   ├── VM_ARCHITECTURE.md      # GCP 雙 VM 溝通協議
│   └── HiHi_Proposal.md       # HiHi 機器人 AI 核心企劃書
├── instances/                  # 遊戲伺服器實體或相關檔案存放目錄
├── minecraft/                  # ⛏️ Minecraft Bedrock 伺服器核心
├── scripts/                    # 工具箱：收納所有的 Python 維護腳本
├── terraria/                   # 🌳 Terraria 遊戲伺服器核心
├── web_interface/              # 🌐 網頁管理介面前後端 (React + Python API)
├── docker-compose.yml          # [IN PROGRESS] 容器化調度清單
└── README.md                   # 專案主要的標準說明書
```

### II. 🚀 環境與執行 (Deployment Strategy)

本專案強烈推崇使用 **Docker Compose** 進行環境隔離，特別是 VM1 的邏輯層。

#### 1. 啟動容器化服務 (VM1)
```bash
# 啟動 Web 面板、HiHi AI 與 神奇嗨螺
docker compose up --build -d
```
> **分體式架構**：系統將自動拆分為 `web-api`、`bot-hihi`、`bot-conch` 三個獨立容器。

#### 2. 啟動遊戲伺服器 (VM2)
遊戲伺服器目前維持原生啟動，由 VM1 透過內網 API 遠端控制。

#### 3. 前端開發模式
```bash
cd web_interface/frontend
npm install
npm run dev -- --host
```

### III. 📝 開發進度 (Dev Log)

- [x] 導入 Vibecoding 架構，建立 `.agent/` 與 `docs/` 雙層大腦。
- [x] Web 前端從 Vanilla HTML/JS 轉型為 **React + Vite** 架構。
- [x] 後端 `api.py` 從單體重構為模組化架構 (`routes/` + `models.py`)。
- [x] **GCP 雙 VM 架構遷移**：Minecraft 遷至 VM2，VM1 轉型為主控台。
- [x] **事件驅動自動安全關機**：實作零空轉的精準關機系統。
- [x] **嗨嗨 AI 模型升級**：完成 Gemini 2.5 Flash + Agentic Loop。
- [x] **全域架構手冊建檔**：建立 `docs/GLOBAL_DEPLOYMENT.md`。
- [⏳] **Docker 分體式遷移**：
    - [x] 撰寫 `web_interface/requirements.txt`。
    - [x] 撰寫 `discord_bot/requirements.txt`。
    - [ ] 撰寫 `docker-compose.yml` 統籌 `web-api` 與 `bot-hihi`。
    - [ ] 實作 Docker Volume 掛載以支援 Vibe Coding 代碼即時生效。
