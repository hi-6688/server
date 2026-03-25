from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import subprocess
import time
import re
import os
import sys

# 確保可以 import 上層目錄的模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import proxy_helpers
from dependencies import get_instance_or_404, verify_key

router = APIRouter(tags=["server"])

class CommandRequest(BaseModel):
    cmd: str

# 依賴注入：驗證 Key 並取得當前實例
def get_instance(key: str, instance_id: str = "main"):
    verify_key(key)
    return get_instance_or_404(instance_id)

@router.post("/start")
def start_server_post(instance = Depends(get_instance)):
    """透過 VM2 啟動伺服器"""
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline. Please use /mc開機 to boot the server first.")
    
    proxy_helpers.flush_offline_cache()
    try:
        res = proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="")
        if res.get('status') == 'success':
            proxy_helpers.proxy_to_agent("start_screen", screen_name=instance.screen_name, path=instance.path)
            return {"status": "started"}
        else:
            raise HTTPException(status_code=500, detail=res.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    game_running = instance.is_running() if vm2_online else False
    public_ip = proxy_helpers.get_vm2_public_ip() if vm2_online else None
    
    return {
        "vm2_online": vm2_online,
        "running": game_running,
        "public_ip": public_ip
    }

@router.get("/stats")
def get_stats(instance = Depends(get_instance)):
    """查詢系統資源 (CPU/RAM)"""
    try:
        with open('/proc/loadavg', 'r') as f:
            load = f.read().split()[0]
        with open('/proc/meminfo', 'r') as f:
            m = f.read()
            tot = int(re.search(r'MemTotal:\s+(\d+)', m).group(1))
            av = int(re.search(r'MemAvailable:\s+(\d+)', m).group(1))
            used_gb = round((tot - av) / 1024 / 1024, 2)
            tot_gb = round(tot / 1024 / 1024, 2)
            perc = round(((tot - av) / tot) * 100, 1)

        return {
            "cpu": {"load_1": float(load), "load_5": 0.0},
            "memory": {"percent": perc, "used": f"{used_gb} GB", "total": f"{tot_gb} GB"},
            "disk": {"percent": 0, "used": "0 GB", "total": "0 GB"},
            "network": {"rx_gb": "0", "tx_gb": "0"}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version")
def get_version(instance = Depends(get_instance)):
    """取得伺服器版本"""
    version = 'Unknown'
    try:
        log_file = instance.get_log_file()
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
    return {"version": version}
