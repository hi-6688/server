# HiHi 系統觀測計畫：內心世界觀測台 (Harness Telemetry)

## 🎯 總結與動機 (Objective)
為了將 HiHi 從單純的聊天機器人升級為「受控且透明的 Agent」，我們必須實作 Harness（馬具/約束系統）的**全域觀測層**。
根據造物主的決策，我們將採用「Discord 原生頻道」作為遙測儀表板，並將其命名為「內心世界」。這不只是一個數據看板，更是一個**即時的、如同終端機日誌般巨細靡遺的意識流觀測點**。嗨嗨的每一次思考推演、工具選擇與生命狀態，都將化為實體的日誌，毫無保留地展現在造物主面前。

## 📁 影響範圍 (Scope & Context)
*   `.env`：新增觀測頻道的環境變數。
*   `discord_bot/cogs/ai_chat.py`：修改核心 `AIChat` 類別，注入意識流發射器 (Consciousness Emitter)。

## 🛠️ 實作步驟與運作邏輯 (Implementation Steps)

### 階段一：環境配置 (Configuration)
1.  在 `.env` 中新增 `INNER_WORLD_CHANNEL_ID=1497021395861897248` 變數，用於指定造物主專屬的私密頻道（內心世界）。
2.  在 `AIChat.__init__` 中讀取此變數，並透過 Discord API 初始化該頻道的物件快取。

### 階段二：打造分段式意識流發射器 (Two-Stage Consciousness Emitter)
因為系統升級為「全子彈管線 (Two-Stage Pipeline)」，遙測發射器必須支援分段攔截與發送，以真實重現大腦運作過程。
1.  在 `AIChat` 類別中新增獨立的非同步方法 `_emit_telemetry_stage1` 與 `_emit_telemetry_stage2`。
2.  **資料解構與視覺化邏輯 (Data Formatting)**：
    將兩個階段的 JSON 解構，並轉換為終端機日誌風格的 Discord Embed。
    
    **[階段一：LogicRouter 邏輯決策觀測]** (`_emit_telemetry_stage1`)
    *   **🎯 觸發源 (Trigger)**：記錄是誰講了什麼話。
    *   **📝 白板異動 (Scratchpad)**：若有更新目標或實體，顯示 Diff。
    *   **📌 記憶釘選 (Pivot)**：顯示是否鎖定此關鍵轉折點。
    *   **💾 記憶水位與 L2 壓縮**：顯示 L1容量，以及是否觸發背景 L2 壓縮。
    *   **🛑 阻斷器判定**：顯示是否將對話攔截丟棄 (Needs Reply = False)。
    
    **[階段二：ChatGenerator 對話生成觀測]** (`_emit_telemetry_stage2`)
    *   **🧠 內心 OS (Thought)**：直接映射 `internal_thought` 欄位。
    *   **⚡ 生存指標 (Vitals)**：即時讀取今日 Token 消耗與 Request 額度。
    *   **🔧 物理行動 (Actions)**：預備執行的工具名稱，或預備休眠的秒數。

### 階段三：非同步掛載 (Hook into Agentic Pipeline)
這一步是效能的關鍵，必須確保「寫日誌」不會拖慢「回覆對話」的速度：
1.  在管線的**第一階段** (呼叫 Flash Lite 處理記憶) 完成後，利用 `asyncio.create_task(self._emit_telemetry_stage1(...))` 發送前半段日誌。
2.  在管線的**第二階段** (呼叫 Flash Lite 產生發言) 完成後，利用 `asyncio.create_task(self._emit_telemetry_stage2(...))` 發送後半段日誌。這兩個動作都會脫離主執行緒，背景默默傳送，確保 0 延遲體感。

---
*附註：目前的計畫為**「Phase 1：單向觀測 (Observability)」**。先將內心世界可視化，待資料量充足後，未來可擴充「Phase 2：好奇心引擎」，讓背景程式讀取這個頻道的日誌，自主觸發學習任務。*

## 🧪 驗證與測試 (Verification)
1.  重新啟動機器人並在一般頻道發送測試訊息。
2.  確認指定的「內心世界」頻道是否能即時收到排版如日誌般詳細的 Embed 觀測報告。
3.  確認主對話頻道的聊天體驗沒有因遙測系統而產生任何體感延遲。