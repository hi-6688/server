# 雙機協作架構 (Cross-VM Architecture)

這份文件定義了本專案如何在主節點 (VM1) 與運算節點 (VM2) 之間進行溝通與職責分配，這是將 Minecraft 伺服器移轉至 VM2 的核心設計圖。

## 1. 職責分配 (Role Delegation)

### 🧠 主節點 VM1 (The Brain)
*   **功能定位**：對外介面與指揮中心。
*   **駐留服務**：
    *   `web_interface/`: 網頁控制面板 (UI)。不負責直接讀寫地圖檔，而是負責「轉發」使用者的請求給 VM2。
    *   `discord_bot/`:  Discord 機器人。
*   **關鍵機制**：透過 `proxy_helpers.py` 工具包，將所有涉及「伺服器操作」的 API 請求，轉換成 HTTP Request 打給 VM2。

### 💪 運算節點 VM2 (The Muscle)
*   **功能定位**：純粹的苦力伺服器，不對外開放 Web UI。
*   **駐留服務**：
    *   `instances/`: 所有的 Minecraft 地圖實體與 `bedrock_server` 執行檔。
    *   `remote_api.py` (The Agent): 一支輕量級的 Python HTTP Server (跑在 port 9999)。它負責在被叫喚時去下達 `screen` 或 `tail` 指令。

---

## 2. API 通訊協議 (Communication Protocol)

VM1 與 VM2 之間的對話標準被定義在 `web_interface/remote_api.py` 中。

### 2.1 連線與授權
*   **傳輸協定**：HTTP POST
*   **認證方式**：Bearer Token (寫死在 `remote_api.py` 中的 `API_KEY` 與 `proxy_helpers.py` 中的 `AGENT_SECRET`)。
*   **預設 Port**：9999

### 2.2 支援的動作 (Actions)
所有請求 Body 都必須是 JSON 格式，並包含 `action` 欄位：

1.  **`execute_command`**: 在指定的 `screen` 內注入指令。
    *   參數: `screen_name` (string), `command` (string)
2.  **`get_system_status`**: 查詢 VM2 上所有活躍的 `screen` 列表。
    *   參數: 無
3.  **`read_file`** 與 **`write_file`**: 讀寫 VM2 上的設定檔 (如 `server.properties`)。
    *   參數: `filepath` (絕對路徑), `content` (寫入時必備)
4.  **`read_log_tail`**: 取得日誌檔案最後Ｎ行。
    *   參數: `filepath` (絕對路徑), `lines` (數字)

---

## 3. 「物理大搬家」實作計畫 (Migration Steps)

若要完成 Minecraft 伺服器的轉移，請依序執行下列步驟：

1.  **轉移 Agent**：將 VM1 的 `web_interface/remote_api.py` 傳送到 VM2 並設定為 Systemd 背景服務。
2.  **打包世界**：在 VM1 根目錄將 `minecraft/`, `oneblock/`, 加上 `instances/` 打包成壓縮檔 (`.tar.gz`)。
3.  **上傳世界**：將壓縮檔送到 VM2 的根目錄並解壓縮。此時 VM2 正式接管所有世界存檔。
4.  **切換大腦**：修改 VM1 上的 `web_interface/instances.json`，將所有 `path` 欄位更新為 VM2 上的絕對路徑。
5.  **測試連線**：使用 VM1 的網頁或 Discord 機器人嘗試啟動伺服器，測試指令是否成功被 `proxy_helpers.py` 拋諸腦後給 VM2 執行。
6.  **善後清理**：連線測試成功後，即可安全刪除 VM1 上的超大型世界地圖資料夾，釋放空間。
