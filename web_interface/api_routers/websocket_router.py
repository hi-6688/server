from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, Query
from typing import List, Set
import json
import requests
import asyncio
import os
import sys

# 確保可以 import 上層目錄的模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from dependencies import API_KEY

router = APIRouter(tags=["websocket"])

# 狀態管理類別：用來追蹤所有活躍的 WebSocket 連線
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.is_broadcasting = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")
        
        # 當第一個客戶端連線時，通知 VM2 開始推送資料流
        if len(self.active_connections) == 1 and not self.is_broadcasting:
            print("[WS] First client connected. Waking up VM2 stream...")
            self.is_broadcasting = True
            self.notify_vm2("start_stream")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")
        
        # 當最後一個客戶端離開時，通知 VM2 停止推送以節省資源
        if len(self.active_connections) == 0 and self.is_broadcasting:
            print("[WS] No clients. Putting VM2 stream to sleep...")
            self.is_broadcasting = False
            self.notify_vm2("stop_stream")

    async def broadcast(self, message: str):
        """將訊息廣播給所有連線中的瀏覽器"""
        if not self.active_connections:
            return
        
        # 使用 asyncio.gather 同步發送，效能更好
        tasks = [connection.send_text(message) for connection in self.active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)

    def notify_vm2(self, action: str):
        """發送控制指令給遠端的 VM2 代理"""
        # 注意：這裡的 IP 應與原本 ws_server.py 中的設定一致
        # 在 Vibe Coding 中，我們可以將這些改為環境變數，但現在我們先保留現狀以確保功能正確。
        try:
            # 這裡我們開一個線程或是使用 non-blocking 方式避免阻塞主程式
            def do_post():
                try:
                    requests.post(
                        "http://39.12.35.16:9999/", 
                        json={"action": action, "screen_name": "main"}, 
                        headers={"Authorization": "Bearer hihi_secret_key_2026"}, 
                        timeout=2
                    )
                except Exception as e:
                    print(f"[WS] Failed to notify VM2 ({action}): {e}")
            
            import threading
            threading.Thread(target=do_post, daemon=True).start()
        except:
            pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, key: str = "none"):
    """處理來自網頁前端的 WebSocket 連線"""
    # 驗證 Key (FastAPI WebSocket 支援從 query 取得參數)
    if key != API_KEY:
        print(f"[WS] Auth failed for key: {key}")
        await websocket.close(code=1008) # Policy Violation
        return

    await manager.connect(websocket)
    try:
        while True:
            # 等待接收訊息 (主要用來維持連線與處理 ping)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get('action') == 'ping':
                    await websocket.send_json({"type": "pong"})
                elif msg.get('action') == 'console_command':
                    # 未來可以在這裡直接整合指令發送邏輯
                    cmd = msg.get('command')
                    await websocket.send_json({"type": "console_log", "data": f"Executed: {cmd}\n"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Error: {e}")
        manager.disconnect(websocket)

@router.get("/ws_health")
def ws_health():
    return {"status": "ok"}

@router.post("/internal_stream")
async def internal_stream_handler(request: Request, key: str = Query("none")):
    """處理來自 VM2 remote_api 的即時推播資料 (轉發給所有 WS 用戶)"""
    # 驗證 Key (確保資料來源是正確的 VM2)
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
        await manager.broadcast(json.dumps(data))
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
