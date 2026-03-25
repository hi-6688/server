import os
import sys
import threading
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 初始化環境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dependencies import instance_manager

# 建立 FastAPI 實例
app = FastAPI(title="Control Panel API", description="伺服器控制面板後端 API")

# 設定 CORS (跨來源資源共用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 先掛載所有 API 路由 (高優先級) ===
from api_routers import server as server_router
from api_routers import instances as instances_router
from api_routers import auth as auth_router
from api_routers import files as files_router
from api_routers import worlds as worlds_router
from api_routers import addons as addons_router
from api_routers import websocket_router

# 掛載 API Router
app.include_router(websocket_router.router)
app.include_router(server_router.router)

@app.get("/debug_ping")
def debug_ping():
    return {"status": "ok_from_main"}

@app.post("/debug_stream")
def debug_stream(key: str = "none"):
    return {"status": "success_from_main", "key": key}
app.include_router(instances_router.router)
app.include_router(auth_router.router)
app.include_router(files_router.router)
app.include_router(worlds_router.router)
app.include_router(addons_router.router)

# === 靜態檔案伺服器與 SPA Fallback (低優先級) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'frontend', 'dist')
LEGACY_DIR = os.path.join(BASE_DIR, 'legacy')

@app.get("/admin.html", include_in_schema=False)
async def redirect_admin():
    return RedirectResponse(url="/")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    # 如果請求路徑在 API 路由中，則不應該進入這裡 (理論上 FastAPI 路由優先級會處理)
    # 但為了保險，我們手動排除根目錄或特定靜態路徑
    
    # 預防路徑穿越
    if ".." in full_path:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    # 1. 處理根目錄
    if not full_path or full_path == "/":
        index_path = os.path.join(DIST_DIR, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse(status_code=404, detail="Frontend not built")

    # 2. 嘗試尋找靜態檔案 (dist)
    dist_path = os.path.join(DIST_DIR, full_path)
    if os.path.exists(dist_path) and os.path.isfile(dist_path):
        return FileResponse(dist_path)

    # 3. 嘗試尋找舊版資源 (legacy)
    legacy_path = os.path.join(LEGACY_DIR, full_path)
    if os.path.exists(legacy_path) and os.path.isfile(legacy_path):
        return FileResponse(legacy_path)

    # 4. SPA Fallback (只針對 HTML 請求或無副檔名的請求)
    if "." not in full_path or full_path.endswith(".html"):
        index_path = os.path.join(DIST_DIR, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)

    return JSONResponse(status_code=404, detail="Not Found")
