# 後端 API 與伺服器架構 (Backend Architecture)

本文件定義麥亂伺服器控制面板的 Python 後端與相關整合服務的技術準則。

## 1. 核心技術堆疊 (Tech Stack)
*   **主要語言**: Python 3.x
*   **網頁伺服器**: 原生 `http.server` 搭配 `socketserver` (極輕量化，捨棄 FastAPI 等重型框架)。
*   **程序管理**: 透過 Linux `screen` 與 `subprocess` 來控制與互動 Minecraft/Terraria 的主進程。

## 2. 模組化架構 (Modular Structure)

```
web_interface/
├── api.py              ← 路由分發器 (入口, ~290 行)
├── models.py           ← 資料模型 (Instance + InstanceManager)
├── routes/
│   ├── auth.py         ← /login
│   ├── server.py       ← /start, /stop, /command, /exec, /server_status, /stats, /version
│   ├── instances.py    ← /instances/create, /delete, /update, /list
│   ├── files.py        ← /read, /write
│   ├── worlds.py       ← /worlds, /switch_world, /delete_world, /reset_world, /upload, /download
│   └── addons.py       ← /addons, /addon/upload, /addon/delete
├── helpers/
│   ├── pack_installer.py ← Addon 安裝與世界註冊
│   └── level_utils.py    ← level.dat 讀取與 cheats 同步
├── proxy_helpers.py    ← VM1↔VM2 代理通訊
└── remote_api.py       ← VM2 端的 Agent API
```

**路由分發機制**：`api.py` 的 `CustomHandler` 根據 URL path 將請求分派給 `routes/` 下的對應模組，每個 handler 接收 `(handler, params, instance)` 三個參數。

## 3. API 路由與規格 (API Endpoints)
預設監聽埠口：**24445** 或是 **8888**。

### 3.1 驗證與授權 (Authentication)
*   **路由**: `POST /login`
*   **說明**: 使用密碼驗證。成功後回傳 `{"status": "ok", "key": "API_KEY"}`。
*   **授權機制**: 所有其餘請求必須在 Body 中或是 URL Query Parameter 中攜帶 `?key=YOUR_API_KEY`，否則回傳 `403 Forbidden`。

### 3.2 多實例管理 (Instance Management)
支援同時運行多個 Minecraft 世界/伺服器，由 `models.InstanceManager` 管理 (`instances.json`)。
*   `POST /instances/create`: 複製預設伺服器目錄，並指定新的 Port，建立新實例。
*   `POST /instances/update`: 更改實例設定 (如通道 ID、連線 Port)。
*   `POST /instances/delete`: 刪除實例檔案與關閉對應進程 (主伺服器 `main` 無法刪除)。
*   *注意：客戶端呼叫 API 時須提供 `instance_id=UUID` 以判斷要控制哪一個伺服器。*

### 3.3 伺服器操作 (Server Operations)
*   `GET /start`: 透過 `screen -dmS bedrock` 啟動背景伺服器。
*   `GET /stop`: 送出 `stop` 指令優雅關機。
*   `POST /command`: 向伺服器終端機傳送指令。
*   `GET /server_status`: 檢查 UDP Port 佔用狀態與 `screen -ls` 以判定伺服器是否運行中。
*   `GET /stats`: 回傳機器的系統負載狀態 (CPU, RAM, Disk, Net)。

### 3.4 檔案與管理 (File Management)
*   `GET /read?file=...`: 讀取 `server.properties`, `allowlist.json` 等設定檔。
*   `POST /write`: 覆寫設定檔內容。
*   `POST /upload`: 支援 `multipart/form-data` 接收世界地圖包 (`.mcworld` / `.zip`) 並透過 Base64 proxy 至 Agent 端解壓縮。
*   `POST /addon/upload`: 處理 Behavior / Resource packs 的上傳，並自動解析 `manifest.json` 寫入世界設定。

### 3.5 自動關機 Webhook (Auto-Shutdown)
*   `POST /webhook/shutdown_vm2`: 接收 VM2 代理程式的關機請求。收到後執行：
    1.  呼叫 `proxy_helpers.backup_all_instances_to_cache()` 備份所有設定檔至 VM1 離線快取。
    2.  呼叫 `GCPManager.stop_instance()` 切斷 VM2 電源。
    3.  透過 Discord Bot API 發送自動關機通知。
*   **授權**: 必須在 Query 中攜帶 `key=API_KEY`。

## 4. 資料庫與持久化 (Persistence)
*   **狀態與實例紀錄**: 使用本地端 `instances.json` 記錄 UUID。
*   **伺服器設定**: 直接讀寫 Minecraft 目錄下的文本檔案 (`.json`, `.properties`)，不依賴 SQL 資料庫。
*   **離線快取**: `proxy_helpers.py` 管理兩層快取機制：
    *   `.backup_cache/`: 關機前自動拉取的唯讀備份，讓 VM2 離線時網頁仍可讀取設定。
    *   `.sync/`: 使用者在 VM2 離線期間修改的設定，開機時由 `flush_offline_cache()` 自動同步至 VM2。

## 5. 🚫 後端避坑指南 (Anti-Patterns)
1. **禁止寫死伺服器路徑**: 必須透過 `current_instance.path` 來取得路徑，因為現在架構支援多實例 (Multi-instance)，寫死 `/home/terraria/servers/minecraft` 會導致呼叫錯誤的世界。
2. **多重驗證機制注意**: 若要新增路由，務必確保判斷條件放在 Auth checking block 之下，避免產生無驗證即可呼叫的後門 API。
3. **VM2 狀態檢查**: 後端依賴 `proxy_helpers` 來轉發請求，送出耗時/危險指令前，必須先以 `proxy_helpers.is_vm2_running()` 檢查目標主機是否在線。
4. **新增路由時**: 在對應的 `routes/xxx.py` 中新增 handler 函式，然後在 `api.py` 的路由分發表中加入映射，不要直接在 `api.py` 中寫業務邏輯。
