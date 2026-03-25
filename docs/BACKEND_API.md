# 後端 API 與伺服器架構 (Backend Architecture - FastAPI Edition)

本文件定義麥亂伺服器控制面板的 **FastAPI** 後端與相關整合服務的技術準則。

> **狀態**: 已從 `http.server` 遷移至 `FastAPI` (v2.0.0+)
> **主要入口**: `web_interface/main.py`

## 1. 核心技術堆疊 (Tech Stack)
*   **Web 框架**: **FastAPI** (高效能、非同步、自動化文件)
*   **非同步伺服器**: **Uvicorn** (運行於 Port 24445)
*   **資料驗證**: **Pydantic v2** (強型別 Request/Response 模型)
*   **WebSocket**: FastAPI 內建 WebSocket 支援 (與 HTTP 共享 Port)
*   **GCP SDK**: `google-api-python-client` (純 Python 實現，無 `gcloud` 指令依賴)

## 2. 模組化路由架構 (Modular Routers)

為了保持程式碼整潔並符合 Vibe Coding 原則，所有的 API 路由都已模組化：

```
web_interface/
├── main.py              ← 應用程式進入點，掛載所有 Router 與靜態檔案
├── dependencies.py      ← 共享依賴 (InstanceManager 實例與 API Key 驗證)
├── api_routers/         ← API 路由模組化目錄
│   ├── auth.py          ← /login (密碼驗證)
│   ├── server.py        ← 伺服器控制 (/start, /stop, /command, /server_status, /stats)
│   ├── instances.py     ← 實例管理 (/instances/list, /create, /delete, /update)
│   ├── files.py         ← 檔案讀寫 (/read, /write)
│   ├── worlds.py        ← 世界地圖 (/worlds, /switch_world, /upload, /download)
│   ├── addons.py        ← 模組管理 (/addons, /addon/upload, /addon/delete)
│   └── websocket_router.py ← 統一 WebSocket 中心 (/ws, /internal_stream)
├── models.py            ← 核心資料模型 (Instance, InstanceManager)
└── proxy_helpers.py     ← VM1 ↔ VM2 代理通訊封裝
```

## 3. 互動式文件 (Interactive API Docs)

FastAPI 自動生成符合 OpenAPI 規範的文件，這是開發者與 Agent 的**第一參考來源**：
*   **Swagger UI**: `http://<IP>:24445/docs` (視覺化測試介面)
*   **ReDoc**: `http://<IP>:24445/redoc` (詳細文件模式)

## 4. 關鍵機制說明

### 4.1 權限驗證 (Authentication)
*   所有 API 請求（除 `/login` 與靜態檔案外）均需通過 `API_KEY` 驗證。
*   驗證方式：支援 URL Query 參數 `?key=...` 或 JSON Body。
*   實作位於 `dependencies.py` 的 `verify_key()` 函數中。

### 4.2 統一 Port 架構 (Unified Port)
原本分散在 24445 (HTTP) 與 24446 (WS) 的服務已合併：
*   **Port 24445**: 同時處理 REST API 請求、WebSocket 連線以及 React 前端靜態檔案服務。

### 4.3 智慧型 WebSocket 連線
*   **端點**: `ws://<IP>:24445/ws?key=<API_KEY>`
*   **按需啟動**: 只有當有瀏覽器連入 `/ws` 時，VM1 才會通知 VM2 開始推送日誌串流；全員斷連時自動休眠 VM2 推播，以節省資源。

### 4.4 靜態檔案與 SPA Fallback
*   `main.py` 負責將 `/` 根目錄指向 `frontend/dist`。
*   支援 **SPA Fallback**：當請求的路徑不是 API 且不是實體檔案時，自動回傳 `index.html`，交給前端 React Router 處理。

## 5. 🚫 開發禁忌 (Anti-Patterns)
1. **禁止在 Router 中直接操作 `instance_manager`**: 應統一從 `dependencies.py` 引入，以確保全域狀態同步。
2. **禁止手動解析 Multipart**: 檔案上傳應使用 FastAPI 的 `UploadFile` 類型，框架會自動處理臨時檔案與記憶體緩衝。
3. **禁止呼叫 `subprocess.run(['gcloud', ...])`**: 必須使用 `GCPManager` 的 Python SDK 方法，確保 Docker 容器內的穩定性。
