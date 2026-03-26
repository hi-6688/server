# 更新日誌 (CHANGELOG)

本檔案記錄了專案的所有重大更新與架構變動。這對於 Agent (AI 助手) 理解專案演進至關重要。

## [v2.0.2] - 2026-03-26

### ✨ 新增功能 (Features)
- 🚀 **面板一鍵開機**：深度整合 `GCPManager` 至網頁端，不再依賴 Discord 指令。面板現可於 VM2 離線狀態下自動呼叫 GCP 雲端開機並智慧輪詢等待連線，實現真正的獨立管理面板。
- 🚥 **VM2 狀態整合**：於左上角伺服器標誌 (Logo) 動態顯示 VM2 系統燈號，並將原先「Superuser」靜態位址替換為麥塊伺服器的連線狀態 (`線上` / `啟動中` / `離線`)。
- 📊 **真實系統資源監控**：儀表板正式串接 VM2 代理伺服器回傳的真實系統監控數據，支援動態顯示 CPU、記憶體 (RAM)、硬碟 (Disk) 與網路 (Net) 資源使用率。

### 🐛 錯誤修復 (Fixes)
- 🔧 **Deploy 腳本修復**：修正 deploy 腳本目標路徑錯誤，確保 VM2 代理程式能順利更新並穩定回傳真實系統監控數據。

### 🎨 介面與體驗優化 (UI/UX)
- 📱 **手機版導航列革新 (TopNav)**：
  - 移除了原有的橫向捲軸，透過 `flex-wrap` 將選單改為一次展平顯示。
  - 將導航第一層（標題圖示區）修改為手機板「**去字純圖示化**」及滿版排列，避免末端選項破碎破版。
  - 分離並動態推移上下排佈局，徹底解決手機螢幕「Logo、導航列與功能狀態」打架擠壓及卡片覆蓋 (`padding-top` 不足) 的問題。
- 🖥️ **電腦版排版升級 (Dashboard)**：將儀表板的最大切割格數自 `xl:grid-cols-4` 改回穩定的三欄 `lg:grid-cols-3`，避免各資訊卡片內部元件因寬度被過度壓縮而變形。

---

## [v2.0.1] - 2026-03-26
### 🧹 系統最佳化：全面盤點與架構文件同步 (Full Audit)
執行專案全域掃描與核心文件審核，確保文件與實際開發進度（FastAPI 架構與 Docker 部署）完全同步。

#### 清理 (Cleanup)
- **移除舊版腳本**: 徹底刪除已棄用的 HTTP 伺服器 `api.py`、WebSocket 伺服器 `ws_server.py` 及舊版 `routes/` 目錄 (共計移除 1,143 行廢棄程式碼)。
- **清除過期連接埠**: 移除 `docker-compose.yml` 中已不再使用的 `24446` (舊 WebSocket) 映射設定。

#### 文件同步 (Documentation Sync)
- **進度更新**: 修正 `README.md` 與 `ROADMAP.md`，將「Docker 容器化開發」標記完成，並修正對舊版 `api.py` 的過期描述。
- **架構藍圖對齊**: 更新 `docs/FRONTEND_ARCH.md`，反映以 `main.py` 與 `api_routers/` 為核心的全新 FastAPI 目錄樹。
- **企劃書校正**: 移除 `docs/HiHi_Proposal.md` 中實體已不存在的開發版 (`discord_bot_dev/`) 目錄。
- **規則手冊擴充**: 更新 `.agent/rules/readrules.md`，補齊 `GLOBAL_DEPLOYMENT.md` 索引並將舊腳本稱呼修正為 `main.py`。

---

## [v2.0.0] - 2026-03-25
### 🚀 重大更新：FastAPI 遷移與架構統一
這是一次核心層級的重構，將原本鬆散的後端整合為現代化的 API 服務。

#### 後端 (Back-end)
- **FastAPI 遷移**: 移除舊有的 `http.server` (api.py)，改用 **FastAPI** 作為核心框架。
- **路由模組化 (Routers)**: 建立 `web_interface/api_routers/` 目錄，將 API 拆分為 `auth`, `server`, `instances`, `files`, `worlds`, `addons` 等模組。
- **權限與狀態管理**: 建立 `web_interface/dependencies.py`，統一管理 API Key 驗證與 `InstanceManager` 實例。
- **WebSocket 整合**: 將原本獨立的 `ws_server.py` (Port 24446) 正式整合進 FastAPI (Port 24445)，實現**單一 Port 處理所有連線**。
- **GCP 管理優化**: 重寫 `GCPManager`，移除對 `gcloud` CLI 的依賴，改用純 Python **Google API Client Library**，解決 Docker 容器內的依賴問題。

#### 前端 (Front-end)
- **WebSocket 適配**: 更新 `useSmartSocket.js`，將連線 Port 從 `24446` 改為與 API 同步的 `24445`。
- **API 呼叫優化**: 更新 `api.js`，適配新的 RESTful 路由結構與 Query 參數。

#### 部署 (Deployment)
- **Dockerfile 升級**: 修改執行指令為 `uvicorn main:app`，支援非同步高效能運行。
- **Docker Compose 完善**: 成功實現 `web-api` 的獨立容器化部署。

---

## [v1.0.0] - 歷史記錄 (摘要)
- 完成 React + Vite 前端框架遷移。
- 實現 GCP 雙 VM 架構（VM1 腦部，VM2 遊戲伺服器）。
- 建立初版 Docker Compose 部署流程。
