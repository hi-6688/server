from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import subprocess
import time
import re
import os
import sys
import asyncio
import json
import functools

# 確保可以 import 上層目錄的模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import proxy_helpers
from dependencies import get_instance_or_404, verify_key
from api_routers.websocket_router import manager

router = APIRouter(tags=["server"])

class CommandRequest(BaseModel):
    cmd: str

# 依賴注入：驗證 Key 並取得當前實例
def get_instance(key: str, instance_id: str = "main"):
    verify_key(key)
    return get_instance_or_404(instance_id)

class StartSequence:
    @staticmethod
    async def run(instance):
        loop = asyncio.get_running_loop()
        
        proxy_helpers.set_boot_progress("vm_starting")
        await manager.broadcast(json.dumps({"type": "boot_progress", "data": "vm_starting", "message": "正在呼叫 Google Cloud 起床..."}))
        
        started = await loop.run_in_executor(None, proxy_helpers.start_vm2_and_wait)
        if not started:
            proxy_helpers.set_boot_progress("offline")
            await manager.broadcast(json.dumps({"type": "boot_progress", "data": "offline", "message": "嘗試啟動虛擬主機失敗，請稍後再試。"}))
            return
            
        proxy_helpers.set_boot_progress("agent_waiting")
        await manager.broadcast(json.dumps({"type": "boot_progress", "data": "agent_waiting", "message": "等待本機代理程式連線..."}))
        await loop.run_in_executor(None, proxy_helpers.flush_offline_cache)
        
        agent_ready = False
        for i in range(15):
            call_agent = functools.partial(proxy_helpers.proxy_to_agent, "get_system_status")
            try:
                res = await loop.run_in_executor(None, call_agent)
                if isinstance(res, dict) and res.get('status') == 'success':
                    agent_ready = True
                    break
            except Exception:
                pass
            await asyncio.sleep(2)
            
        if not agent_ready:
            proxy_helpers.set_boot_progress("offline")
            await manager.broadcast(json.dumps({"type": "boot_progress", "data": "offline", "message": "無法連線至內部的管理代理程式。"}))
            return
            
        proxy_helpers.set_boot_progress("server_starting")
        await manager.broadcast(json.dumps({"type": "boot_progress", "data": "server_starting", "message": "正在啟動 Minecraft 遊戲伺服器..."}))
        
        call_start = functools.partial(proxy_helpers.proxy_to_agent, "start_server", screen_name=instance.screen_name, path=instance.path)
        try:
            res = await loop.run_in_executor(None, call_start)
            if isinstance(res, dict) and res.get('status') == 'success':
                proxy_helpers.set_boot_progress("online")
                await manager.broadcast(json.dumps({"type": "boot_progress", "data": "online", "message": "伺服器已全面上線！"}))
            else:
                proxy_helpers.set_boot_progress("offline")
                err = res.get("message") if isinstance(res, dict) else "啟動未知錯誤"
                await manager.broadcast(json.dumps({"type": "boot_progress", "data": "offline", "message": err}))
        except Exception as e:
            proxy_helpers.set_boot_progress("offline")
            await manager.broadcast(json.dumps({"type": "boot_progress", "data": "offline", "message": str(e)}))

@router.post("/start")
async def start_server_post(background_tasks: BackgroundTasks, instance = Depends(get_instance)):
    """透過 VM2 啟動伺服器 (背景非同步執行)"""
    prog = proxy_helpers.get_boot_progress()
    if prog != "offline" and prog != "online":
        return {"status": "starting", "message": "開機程序已經在進行中"}
        
    background_tasks.add_task(StartSequence.run, instance)
    return {"status": "starting", "message": "已受理啟動請求，正在背景執行"}

@router.get("/start")
def start_server_get(instance = Depends(get_instance)):
    """本機直接啟動伺服器"""
    if instance.is_running():
        raise HTTPException(status_code=409, detail="Server already running")
    try:
        cmd = 'cd %s && screen -dmS %s -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"' % (instance.path, instance.screen_name)
        subprocess.run(cmd, shell=True, check=True)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
def stop_server_post(instance = Depends(get_instance)):
    """透過 VM2 關閉伺服器並標記準備斷電"""
    try:
        if proxy_helpers.is_vm2_running():
            # 寫入狀態標記
            pending_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../.pending_vm_shutdown')
            with open(pending_file, 'w') as f:
                f.write('manual_web')
                
            try:
                proxy_helpers.backup_all_instances_to_cache()
            except Exception as e:
                print(f"[Web Shutdown] Backup failed: {e}")
            
            proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="say 網頁面板發起安全關機指令，系統執行存檔並準備斷電...\r")
            time.sleep(1)
            proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="stop\r")
            
        return {"status": "stopping_and_powering_off"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stop")
def stop_server_get(instance = Depends(get_instance)):
    """本機直接關閉伺服器"""
    try:
        subprocess.run(['screen', '-S', instance.screen_name, '-p', '0', '-X', 'stuff', 'stop\n'])
        time.sleep(3)
        subprocess.run(['screen', '-S', instance.screen_name, '-X', 'quit'], stderr=subprocess.DEVNULL)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/command")
def send_command(req: CommandRequest, instance = Depends(get_instance)):
    """發送指令到伺服器"""
    cmd = req.cmd
    if not cmd:
        raise HTTPException(status_code=400, detail="No command provided")
    try:
        if proxy_helpers.is_vm2_running():
            proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command=cmd)
            if cmd.strip() in ['list', 'gamerule ']:
                time.sleep(1.0)
        return {"result": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exec")
def exec_command(req: CommandRequest, instance = Depends(get_instance)):
    """執行指令並回傳 log 尾部"""
    cmd = req.cmd
    if not cmd:
        raise HTTPException(status_code=400, detail="No command")
    try:
        subprocess.run(['screen', '-S', instance.screen_name, '-p', '0', '-X', 'stuff', '%s\\n' % cmd])
        time.sleep(1.5)
        log_file = instance.get_log_file()
        output = ''
        if os.path.exists(log_file):
            output = subprocess.check_output(['tail', '-n', '20', log_file]).decode('utf-8', errors='replace')
        return {"result": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/server_status")
def get_server_status(instance = Depends(get_instance)):
    """查詢 VM2 虛擬機與遊戲伺服器的運行狀態"""
    vm2_online = proxy_helpers.is_vm2_running()
    
    # 如果 vm2_online 是 False，但 _boot_progress 不是 offline（代表剛開機還沒抓到狀態）
    # 或是雖然 vm2 上線了，但還在 agent_waiting 階段，此時向 agent 查詢運行狀態會超時
    boot_progress = proxy_helpers.get_boot_progress()
    game_running = False
    
    if vm2_online and boot_progress in ['online', 'offline']:
        game_running = instance.is_running()
        
    public_ip = proxy_helpers.get_vm2_public_ip() if vm2_online else None
    
    return {
        "vm2_online": vm2_online,
        "running": game_running,
        "public_ip": public_ip,
        "boot_progress": boot_progress
    }

@router.get("/stats")
def get_stats(instance = Depends(get_instance)):
    """查詢系統資源 (CPU/RAM/Disk/Network)"""
    # 預設空值 (VM2 離線時的回傳)
    default_stats = {
        "cpu_percent": 0.0,
        "ram_used_mb": 0,
        "ram_total_mb": 0,
        "ram_percent": 0.0,
        "disk_used_gb": 0.0,
        "disk_total_gb": 0.0,
        "disk_percent": 0.0,
        "net_rx_mb": 0.0,
        "net_tx_mb": 0.0
    }

    try:
        if proxy_helpers.is_vm2_running():
            res = proxy_helpers.proxy_to_agent("get_stats")
            if res.get("status") == "success" and "stats" in res:
                return res["stats"]
            
        return default_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

last_known_version = "Unknown"

@router.get("/version")
def get_version(instance = Depends(get_instance)):
    """取得伺服器版本"""
    global last_known_version
    version = 'Unknown'
    try:
        log_file = instance.get_log_file()
        if proxy_helpers.is_vm2_running():
            res = proxy_helpers.proxy_to_agent("get_version", {"filepath": log_file})
            if res and res.get("status") == "success":
                version = res.get("version", "Unknown")
        else:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        if 'Version:' in line:
                            match = re.search(r'Version:\s*(\S+)', line)
                            if match:
                                version = match.group(1)
                            break
    except:
        pass
        
    if version != "Unknown":
        last_known_version = version
    elif last_known_version != "Unknown":
        version = last_known_version
        
    return {"status": "success", "version": version}
