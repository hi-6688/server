# 智慧型連線架構規範 (Smart Connection Architecture v2.0)

> **版本**: 2.0 (FastAPI Integrated)
> **最後更新**: 2026-03-25
> **定位**: 定義「按需長連線 (On-Demand WebSocket)」在 FastAPI 環境下的實作規範。

## 1. 架構變更 (Architectural Changes)

在 v2.0 中，我們將 WebSocket 從獨立的 `aiohttp` 服務遷移到了 **FastAPI** 核心中。
- **單一埠口 (Single Port)**: 捨棄 24446，統一使用 **24445** 處理所有通訊。
- **共享依賴**: WebSocket 現在能直接存取 FastAPI 的依賴注入系統 (如共享的 `instance_manager`)。

## 2. 運作流程 (Operational Flow)

### 2.1 建立連線 (Connect)
1. 前端 React Hook `useSmartSocket.js` 發起連線：`ws://<IP>:24445/ws?key=<API_KEY>`。
2. `websocket_router.py` 驗證 Key。
3. **ConnectionManager**:
    - 將 WebSocket 加入活躍連線集合。
    - 若為**第一個**連線：透過背景任務通知遠端 VM2 開啟串流 (`start_stream`)。

### 2.2 資料轉發 (Broadcasting)
1. VM2 取得遊戲日誌或效能數據後，向 VM1 的 `POST /internal_stream?key=<API_KEY>` 發送 JSON。
2. `internal_stream_handler` 接收到資料後，呼叫 `manager.broadcast()`。
3. 使用 `asyncio.gather` 將訊息同步推送到所有連線中的瀏覽器。

### 2.3 資源回收 (Disconnect)
1. 當前端斷開連線或網頁關閉。
2. **ConnectionManager**:
    - 移除該連線。
    - 若為**最後一個**連線：通知 VM2 停止推播 (`stop_stream`)，系統回歸零消耗狀態。

## 3. 實作細節

*   **非同步優先**: 所有的廣播與發送皆使用 Python 的 `async/await` 語法，確保不會阻塞 API 請求。
*   **併發處理**: 使用 `threading.Thread` (或 FastAPI 的 `BackgroundTasks`) 處理對遠端 VM2 的控制請求，避免 HTTP 請求等待遠端回覆。
*   **心跳偵測**: 由前端發送 `{"action": "ping"}`，後端回覆 `{"type": "pong"}`，維持連線不被防火牆中斷。

## 4. 前端調用範例 (React)

```javascript
// 使用封裝好的 Hook
const { isConnected, serverState } = useSmartSocket();

useEffect(() => {
    if (serverState?.type === 'console_log') {
        appendLog(serverState.data);
    }
}, [serverState]);
```
