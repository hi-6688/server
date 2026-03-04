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
    *   **自動關機背景線程 (Event-Driven Shutdown)**：Agent 啟動時會掛載一條背景線程，持續以 `tail -F` 監聽 Minecraft 日誌。當偵測到所有玩家離線後，啟動 10 分鐘倒數計時；若無人回來，則自動執行安全存檔（`stop`）、智慧等待進程結束、再通知 VM1 切斷電源。

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

---

## 4. 自動關機與離線快取 (Auto-Shutdown & Offline Cache)

### 4.1 事件驅動自動關機
VM2 的 `remote_api.py` 內建背景線程 (`log_monitor_thread`)，以 `tail -F` 監聽 `bedrock_screen.log`：
1.  偵測到 `Player disconnected` 時，觸發 `list` 指令確認線上人數。
2.  若人數 = 0，啟動 10 分鐘計時器 (`threading.Timer`)。
3.  期間若有 `Player connected`，計時器取消。
4.  計時器到期時，執行「安全關機序列」：
    *   發送 `stop` 指令至所有 screen。
    *   每 2 秒查詢 `screen -ls`，直到所有 screen 消失（確認遊戲引擎已 100% 存檔結束）。
    *   發送 `POST /webhook/shutdown_vm2` 至 VM1，請求切斷 GCP 電源並廣播 Discord 通知。

### 4.2 離線設定快取
VM1 的 `proxy_helpers.py` 管理雙層離線快取：
*   **備份層 (`.backup_cache/`)**：關機前自動拉取 VM2 上的設定檔（`server.properties` 等），供離線時網頁讀取。
*   **修改層 (`.sync/`)**：使用者在離線期間修改的設定暫存於此。
*   **同步機制**：開機時 `flush_offline_cache()` 自動將修改層的內容推送至 VM2，並清除備份層。

