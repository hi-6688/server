# 後端 API 與伺服器架構 (Backend Architecture)

本文件定義麥亂伺服器控制面板的 Python 後端 (`api.py`) 與相關整合服務的技術準則。

## 1. 核心技術堆疊 (Tech Stack)
*   **主要語言**: Python 3.x
*   **網頁伺服器**: 原生 `http.server` 搭配 `socketserver` (極輕量化，捨棄 FastAPI 等重型框架)。
*   **程序管理**: 透過 Linux `screen` 與 `subprocess` 來控制與互動 Minecraft/Terraria 的主進程。

## 2. API 路由與規格 (API Endpoints)
預設監聽埠口：**24445** 或是 **8888**。

### 2.1 驗證與授權 (Authentication)
*   **路由**: `POST /login`
*   **說明**: 使用密碼驗證。成功後回傳 `{"status": "ok", "key": "API_KEY"}`。
*   **授權機制**: 所有其餘請求必須在 Body 中或是 URL Query Parameter 中攜帶 `?key=YOUR_API_KEY`，否則回傳 `403 Forbidden`。

### 2.2 多實例管理 (Instance Management)
支援同時運行多個 Minecraft 世界/伺服器，由 `InstanceManager` 管理 (`instances.json`)。
*   `POST /instances/create`: 複製預設伺服器目錄，並指定新的 Port，建立新實例。
*   `POST /instances/update`: 更改實例設定 (如通道 ID、連線 Port)。
*   `POST /instances/delete`: 刪除實例檔案與關閉對應進程 (主伺服器 `main` 無法刪除)。
*   *注意：客戶端呼叫 API 時須提供 `instance_id=UUID` 以判斷要控制哪一個伺服器。*

### 2.3 伺服器操作 (Server Operations)
*   `GET /start`: 透過 `screen -dmS bedrock` 啟動背景伺服器。
*   `GET /stop`: 送出 `stop` 指令優雅關機。
*   `GET /command?cmd=<CMD>`: 向 `screen` 會話內傳送 RCON 或伺服器終端機指令。
*   `GET /server_status`: 檢查 UDP Port 佔用狀態與 `screen -ls` 以判定伺服器是否運行中。
*   `GET /stats`: 回傳機器的系統負載狀態 (CPU, RAM, Disk, Net)。

### 2.4 檔案與管理 (File Management)
*   `GET /read?file=...`: 讀取 `server.properties`, `allowlist.json` 等設定檔。
*   `POST /write`: 覆寫設定檔內容。
*   `POST /upload`: 支援 `multipart/form-data` 接收世界地圖包 (`.mcworld` / `.zip`) 並透過 Base64 proxy 至 Agent 端解壓縮。
*   `POST /addon/upload`: 處理 Behavior / Resource packs 的上傳，並自動解析 `manifest.json` 寫入世界設定。

## 3. 資料庫與持久化 (Persistence)
*   **狀態與實例紀錄**: 使用本地端 `instances.json` 記錄 UUID。
*   **伺服器設定**: 直接讀寫 Minecraft 目錄下的文本檔案 (`.json`, `.properties`)，不依賴 SQL 資料庫。

## 4. 🚫 後端避坑指南 (Anti-Patterns)
1. **禁止寫死伺服器路徑**: 必須透過 `current_instance.path` 來取得路徑，因為現在架構支援多實例 (Multi-instance)，寫死 `/home/terraria/servers/minecraft` 會導致呼叫錯誤的世界。
2. **多重驗證機制注意**: 若要在 Python 中新增路由，務必確保判斷條件放在 Auth checking block 之下，避免產生無驗證即可呼叫的後門 API。
3. **VM2 狀態檢查**: 後端依賴 `proxy_helpers` 來轉發請求，送出耗時/危險指令前，必須先以 `proxy_helpers.is_vm2_running()` 檢查目標主機是否在線。
