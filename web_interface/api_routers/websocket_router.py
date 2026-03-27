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
import proxy_helpers

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
        try:
            # 開一個線程以避免阻塞主程式
            def do_post():
                try:
                    res = proxy_helpers.proxy_to_agent(action, screen_name="main")
                    if isinstance(res, dict) and res.get("status") == "error":
                        print(f"[WS] Failed to notify VM2 ({action}): {res.get('message')}")
                except Exception as e:
                    print(f"[WS] Failed to notify VM2 ({action}): {e}")
            
            import threading
            threading.Thread(target=do_post, daemon=True).start()
        except:
            pass

manager = ConnectionManager()

async def stats_broadcaster_loop():
    """背景輪詢迴圈：定期取得資源狀態並廣播"""
    while True:
        try:
            if not manager.active_connections:
                # 若無人連線，休息久一點
                await asyncio.sleep(5)
                continue

            bp = proxy_helpers.get_boot_progress()
            vm2_online = await asyncio.to_thread(proxy_helpers.is_vm2_running)

            game_running = False
            active_players = 0
            max_players = 0
            version = ""
            system_stats = {}

            # 只有在 VM2 上線且不在開機中途時才向 Agent 查詢
            if vm2_online and bp in ("online", "offline"):
                # 使用既有的 proxy_to_agent (POST 協定) 查詢系統狀態
                status_res = await asyncio.to_thread(proxy_helpers.proxy_to_agent, "get_system_status")
                stats_res = await asyncio.to_thread(proxy_helpers.proxy_to_agent, "get_stats")

                if isinstance(status_res, dict) and status_res.get("status") == "success":
                    screens = status_res.get("screens", [])
                    # 判斷遊戲是否有在跑：如果有任何 screen 存在即視為運行
                    game_running = len(screens) > 0

                if isinstance(stats_res, dict) and stats_res.get("status") == "success":
                    system_stats = stats_res.get("stats", {})

            # 組裝狀態字串
            status_str = "offline"
            if game_running:
                status_str = "online"
            elif bp not in ("offline", "none", "", None):
                status_str = "starting"

            payload = {
                "type": "server_status",
                "data": {
                    "status": status_str,
                    "vm2_online": vm2_online,
                    "game_running": game_running,
                    "system": system_stats,
                    "activePlayers": active_players,
                    "maxPlayers": max_players,
                    "version": version,
                    "boot_progress": bp
                }
            }

            await manager.broadcast(json.dumps(payload))

        except Exception as e:
            print(f"[StatsBroadcaster] Error: {e}")

        # 固定間隔推播
        await asyncio.sleep(4)


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
