# 智慧型連線架構規範 (Smart Connection Architecture)

> **版本**: 1.0 (Draft)
> **最後更新**: 2026-03-05
> **定位**: 本文檔定義麥亂伺服器未來升級「按需長連線 (On-Demand WebSocket/SSE)」的設計規範，採用業界最佳實踐以兼顧「0 延遲即時性」與「0 掛機消耗」。

## 1. 核心技術選型 (Industry Standards)

為取代每 5 秒的靜態 HTTP 輪詢 (Polling)，我們將採用業界標準的 **WebSocket** 協議。
- **前端 (React/Vite)**: 使用瀏覽器原生的 `WebSocket` API。不依賴笨重的第三方 Socket.io 函式庫，並透過 React Custom Hook (`useSmartSocket.js`) 封裝生命週期。
- **後端 (Python)**: 使用官方推薦的 `aiohttp` 異步網頁伺服器取代單純的 `websockets` 套件。與現有的 HTTP API (24445 port) 配合，開啟一個專屬的 WebSocket 及內部通訊埠 (防撞設定為 24446)。

## 2. 生命週期與「按需」邏輯 (On-Demand Lifecycle)

這套架構最大的特色在於「**無人觀看時零消耗**」，只有在管理員打開面板時才建立連線。

### 2.1 階段一：建立連線 (Connection Upgrade)
1. 使用者打開網頁，React 的 `Dashboard` 或 `LiveConsole` 元件被掛載 (Mount)。
2. 前端立刻發起 WebSocket 握手請求 `ws://<VM1_IP>:24446/ws?key=<API_KEY>&instance=main`。
3. 後端 (VM1) 驗證通過後，將該客戶端加入廣播清單 (`active_connections += 1`)。
4. **喚醒機制**: 如果這是當前系統的第一個連線 (`active_connections == 1`)，VM1 會主動向 VM2 發起遠端日誌監聽 (Tail Log) 與資源訂閱。

### 2.2 階段二：即時串流 (Real-time Streaming)
1. VM2 將最新的 CPU、RAM 狀態以及伺服器 Console 輸出送達 VM1。
2. VM1 透過 WebSocket 將 JSON 封包廣播給所有目前連線中的前端。
3. **心跳機制 (Heartbeat)**: 為了防止防火牆或 Nginx 自動切斷長連線，前端每 30 秒送出 `ping`，後端回覆 `pong`。若超過 60 秒未收到回覆，前端自動啟動「斷線重連演算法 (Exponential Backoff)」。

### 2.3 階段三：自動降級與資源回收 (Resource Reclaiming)
1. 當使用者關閉網頁、切換分頁導致元件卸載 (Unmount)，或進入螢幕休眠時，前端會主動呼叫 `ws.close()`。
2. 後端捕捉到斷線事件，將該客戶端移出清單 (`active_connections -= 1`)。
3. **休眠機制**: 當清單人數歸零 (`active_connections == 0`)，VM1 將主動切斷與 VM2 之間的效能監聽通道，讓系統重新回歸到「零消耗狀態」。

## 3. 面板各功能的連線策略

為了確保效能，並非所有功能都要硬上 WebSocket：

| 功能區域 | 連線策略 | 原因 |
| :--- | :--- | :--- |
| **頂部狀態燈號** | WebSocket | 需要即時反映伺服器存活與否。 |
| **儀表板 (Dashboard)** | WebSocket | 資源佔用圖表需要流暢更新，避免 5 秒刷新一次的突兀感。 |
| **終端機 (LiveConsole)** | WebSocket (雙向) | 確保指令送出與輸出回傳達到 0.1 秒內的「真．終端機」體驗。 |
| **世界清單/模組/規則** | **HTTP REST API** | 設定檔讀取屬於靜態操作，維持一次性 Fetch 更節省頻寬。 |

## 4. 防呆與降級處理 (Fallback Mechanism)

*   **網路阻擋防禦**: 某些嚴格的企業網路或校園網路會阻擋 `ws://` 協定。在前端的 `useSmartSocket` hook 中，若偵測到連線連續失敗達一定次數或中斷，系統必須**自動降級 (Fallback)** 並觸發 HTTP 拉取，或者透過心跳機制 (`ping`) 確保持續嘗試連線。
