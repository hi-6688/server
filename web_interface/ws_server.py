import asyncio
from aiohttp import web
import json
import os
import requests

# 使用與 api.py 相同的靜態或環境變數 Token (簡化實作避免出錯)
API_KEY = "AdminKey123456"

# 活躍的 WebSocket 連線
connected_clients = set()
is_broadcasting = False

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

async def websocket_handler(request):
    """處理來自網頁前端的 WebSocket 連線"""
    global is_broadcasting
    
    # Auth
    req_key = request.query.get('key', '')
    if req_key != API_KEY:
        return web.Response(status=401, text="Unauthorized")

    ws = web.WebSocketResponse(heartbeat=30.0)
    await ws.prepare(request)
    
    connected_clients.add(ws)
    print(f"[WS] Client connected. Total: {len(connected_clients)}")

    if len(connected_clients) > 0 and not is_broadcasting:
        print("[WS] First client connected. Waking up VM2 stream...")
        is_broadcasting = True
        try:
            requests.post(
                "http://39.12.35.16:9999/", 
                json={"action": "start_stream", "screen_name": "main"}, 
                headers={"Authorization": "Bearer hihi_secret_key_2026"}, 
                timeout=2
            )
        except Exception as e:
            print(f"[WS] Failed to wake up VM2: {e}")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get('action') == 'ping':
                        await ws.send_json({"type": "pong"})
                    elif data.get('action') == 'console_command':
                        # TODO: call remote_api execute_command
                        cmd = data.get('command')
                        await ws.send_str(json.dumps({"type": "console_log", "data": f"Executed: {cmd}\n"}))
                except:
                    pass
    finally:
        connected_clients.remove(ws)
        print(f"[WS] Client disconnected. Total: {len(connected_clients)}")
        if len(connected_clients) == 0:
            print("[WS] No clients. Putting VM2 stream to sleep...")
            is_broadcasting = False
            try:
                requests.post(
                    "http://39.12.35.16:9999/", 
                    json={"action": "stop_stream"}, 
                    headers={"Authorization": "Bearer hihi_secret_key_2026"}, 
                    timeout=2
                )
            except:
                pass

    return ws

async def internal_stream_handler(request):
    """處理來自 VM2 remote_api 的即時推播資料"""
    # Auth
    req_key = request.query.get('key', '')
    if req_key != API_KEY:
        return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
        
        # 將收到的效能或日誌資料，轉發給所有活躍的 WebSocket clients
        if connected_clients:
            message = json.dumps(data)
            # asyncio.gather concurrently sends to all clients
            await asyncio.gather(
                *[client.send_str(message) for client in connected_clients],
                return_exceptions=True
            )
        
        return add_cors_headers(web.json_response({"status": "success"}))
    except json.JSONDecodeError:
        return add_cors_headers(web.Response(status=400, text="Invalid JSON"))

async def options_handler(request):
    """處理 CORS OPTIONS 請求"""
    return add_cors_headers(web.Response(status=200))

def start_ws_server():
    print("[WS] Starting Smart Connection server on port 24446...")
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    app.router.add_post('/internal_stream', internal_stream_handler)
    app.router.add_options('/internal_stream', options_handler)
    
    # Runner 機制以配合 threading
    runner = web.AppRunner(app)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', 24446)
    loop.run_until_complete(site.start())
    loop.run_forever()

if __name__ == '__main__':
    start_ws_server()
