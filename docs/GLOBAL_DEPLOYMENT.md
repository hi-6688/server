# 🌐 全域部署架構 (Global Deployment Architecture)

> **版本**: 1.0
> **最後更新**: 2026-03-20

本文件定義了專案在雲端（GCP, Azure）與本地環境的物理佈署狀況，供 AI Agent 與開發者快速定位資源。

---

## 1. 雲端基礎設施 (Cloud Infrastructure)

### 🧠 主控節點：GCP VM1 (The Brain)
*   **規格**: `e2-standard-2` (2 vCPU, 7.8GB RAM) / OS: Ubuntu.
*   **角色**: 對外入口、邏輯中樞、AI 靈魂。
*   **駐留服務**:
    *   **Web Interface**: React 前端 + Python API 後端 (Port 24445, 24446)。
    *   **Discord Bot**: HiHi (AI 模式) & Conch (工具模式)。
*   **部署方式**: **Docker Compose 容器化** (正在遷移中)。
    *   `bot-hihi`: 獨立容器，負責靈魂對話。
    *   `bot-conch`: 獨立容器，負責伺服器指令。
    *   `web-api`: 獨立容器，負責管理介面。

### 💪 運算節點：GCP VM2 (The Muscle)
*   **規格**: 針對遊戲優化之運算機型。
*   **角色**: 遊戲伺服器執行、日誌監控。
*   **駐留服務**:
    *   **Minecraft Bedrock Server**: 執行於 `screen` 實體。
    *   **Terraria Server**: 執行於 `screen` 實體。
    *   **Remote Agent (`remote_api.py`)**: 輕量級監控與指令轉發 API (Port 9999)。
*   **部署方式**: **原生執行 (Native)**，以確保最高效能與對 Screen 的直接控制。

### 🔵 記憶儲存：Azure PostgreSQL
*   **服務**: Azure Database for PostgreSQL (Flexible Server)。
*   **角色**: 存放「嗨嗨 (HiHi)」的長期記憶、RAG 向量庫、使用者事實 (Facts)。
*   **連線協定**: 透過 SSL 安全連線。

---

## 2. 網路與溝通協議 (Network & Protocols)

*   **跨機通訊 (Internal)**: VM1 透過 GCP 內網 IP 呼叫 VM2:9999 API。
*   **外部存取 (Public)**: 
    *   Web 面板: `http://VM1_IP:24445`
    *   Discord: 透過 Discord WebSocket 長連線。
*   **智慧型連線**: Web 面板採用 WebSocket (Port 24446) 實現即時日誌流。

---

## 3. 數據持久化與備份 (Persistence & Backups)

*   **專案備份**: `/home/terraria/servers/backups/` 存放地圖與數據壓縮檔。
*   **Docker 持久化**: 透過 **Bind Mounts** 將宿主機的 `data/` 與 `.env` 掛載進容器。
*   **離線快取**: VM1 保留 VM2 的設定檔快取，確保 VM2 關機時網頁依然可讀。

---

## 4. 開發流程 (Vibe Coding Workflow)

1.  **直接編輯**: 在 VM1 宿主機修改代碼（透過 VS Code Remote）。
2.  **熱重載**: Docker 容器掛載了開發資料夾，修改後直接 `docker compose restart <service>`。
3.  **安全性**: 所有敏感資訊 (Token) 統一存放於根目錄的 `.env` 中，嚴禁進入 Git 追蹤。
