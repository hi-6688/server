# APCPC Godot Project (開發筆記)

專為「多人連線卡牌對戰」設計的遊戲專案。核心特色為即時、前後端分離與高擴展性。

## 🛠️ 技術堆疊 (Tech Stack)

### 1. 前端 (Frontend)
- **Engine**: Godot 4 (使用 Compatibility / OpenGL 3)
- **Language**: GDScript (控制 UI 與遊戲邏輯)
- **Socket**: Native WebSocketPeer (原生 WebSocket)

### 2. 後端 (Backend)
- **Runtime**: Python 3.11 (基於 Docker)
- **Framework**: FastAPI (高效能 Web 框架)
- **Database**: SQLModel (Hybrid: Local=SQLite, Prod=PostgreSQL)
- **Infrastructure**: Docker, Docker Compose, DigitalOcean App Platform

---

## 📁 檔案結構全覽 (Project File Structure)

```
APCPCgodot/
├── .agent/                     # 🤖 [AI 設定] Agent 工作流與規則
│   └── rules/                  #    - 存放自訂 Agent 規則的文字檔
│
├── .vscode/                    # 🛠️ [編輯器] VS Code 專案設定
│
├── backend/                    # 🖥️ [後端] Python FastAPI 伺服器 (Dockerized)
│   ├── app.yaml                # ☁️ [部署] DigitalOcean App Platform 設定檔
│   ├── database.py             # ⚙️ [程式] 資料庫連線 (自動切換 SQLite/Postgres)
│   ├── docker-compose.yml      # 🐳 [容器] 本地開發用 (Local Dev)
│   ├── Dockerfile              # 🐳 [容器] Image 建置檔
│   ├── main.py                 # 🚀 [核心] FastAPI 應用程式入口
│   └── requirements.txt        # 📦 [設定] Python 依賴套件清單 (鎖定版本)
│
├── PVPCgodot/                  # 🎮 [前端] Godot 4.x 遊戲專案
│   ├── NetworkManager.gd       # 📡 [程式] 網路連線管理器
│   ├── project.godot           # ⚙️ [設定] 專案主設定檔
│   └── export_presets.cfg      # 📤 [設定] 匯出範本設定
│
└── README.md                   # 📝 [紀錄] 本核心文件
```

## 🚀 環境與執行 (Quick Start - Docker First)

所有後端開發預設在 **Docker 容器**內進行，請確保已安裝 Docker Desktop。

### 1. 啟動後端 (Backend)
- **指令**:
  ```powershell
  cd backend
  docker-compose up --build
  ```
- **成功訊號**: 看到 `Uvicorn running on http://0.0.0.0:8080`
- **健康檢查**: 瀏覽器開啟 `http://localhost:8080/health` 應顯示 `{"status": "ok"}`

### 2. 啟動前端 (Frontend)
- **操作**: Godot 編輯器內按下 F6 執行場景。

## 📡 通訊協議 (Protocol)

- **連線 (Connect)**: `ws://127.0.0.1:8080/ws?token={PLAYER_TOKEN}`
- **接收 (Receive)**: 
  - Server -> Client: `{"status": "received"}`

## 📝 開發進度 (Dev Log)

### ✅ 已完成功能
- [x] **基礎架構**: Containerized FastAPI Backend (Docker)
- [x] **依賴管理**: 鎖定 requirements.txt 版本
- [x] **部署準備**: DigitalOcean app.yaml 與 Dockerfile 設定
- [x] **強健性**: 實作 Health Check 與 Structured Logging
- [x] **資料庫**: 實作 SQLite/PostgreSQL 混合連線邏輯

### 📋 待辦清單 (Todo)
- [ ] 整合 Discord Bot (Lobby System)
- [ ] 實作多人房間匹配邏輯
