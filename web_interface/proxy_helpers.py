import json
import os
import aiohttp
import asyncio

VM_NAME = "instance-20260220-174959"
AGENT_PORT = 9999
AGENT_SECRET = "hihi_secret_key_2026"
SYNC_DIR = "/home/terraria/servers/web_interface/.sync"
BACKUP_DIR = "/home/terraria/servers/web_interface/.backup_cache"

# Use the GCPManager from discord_bot to keep logic DRY
import sys
sys.path.append("/home/terraria/servers/discord_bot")
from utils.gcp_manager import GCPManager
gcp = GCPManager(project_id="project-ad2eecb1-dd0f-4cf4-b1a", zone="asia-east1-c")

def is_vm2_running():
    return gcp.get_instance_status(VM_NAME) == "RUNNING"

def get_vm2_ip():
    return gcp.get_instance_ip(VM_NAME)

async def _async_proxy(ip, action, kwargs):
    url = f"http://{ip}:{AGENT_PORT}/"
    headers = {"Authorization": f"Bearer {AGENT_SECRET}", "Content-Type": "application/json"}
    payload = {"action": action, **kwargs}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=5) as resp:
            resp.raise_for_status()
            return await resp.json()

def proxy_to_agent(action, **kwargs):
    ip = get_vm2_ip()
    if not ip:
        return {"status": "error", "message": "VM2 offline"}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_proxy(ip, action, kwargs))
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        loop.close()

def save_offline_cache(instance_path, filename, content):
    os.makedirs(SYNC_DIR, exist_ok=True)
    # Use base64 of path to avoid slash issues
    import base64
    safe_path = base64.urlsafe_b64encode(instance_path.encode()).decode()
    cache_file = os.path.join(SYNC_DIR, f"{safe_path}_{filename}")
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(content)

def save_offline_backup(instance_path, filename, content):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    import base64
    safe_path = base64.urlsafe_b64encode(instance_path.encode()).decode()
    cache_file = os.path.join(BACKUP_DIR, f"{safe_path}_{filename}")
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(content)

def read_offline_cache(instance_path, filename):
    import base64
    safe_path = base64.urlsafe_b64encode(instance_path.encode()).decode()
    
    # 使用者修改過的未同步設定 (優先級最高)
    sync_file = os.path.join(SYNC_DIR, f"{safe_path}_{filename}")
    if os.path.exists(sync_file):
        with open(sync_file, 'r', encoding='utf-8') as f:
            return f.read()
            
    # 關機前拉取的唯讀備份 (提供讀取畫面用)
    backup_file = os.path.join(BACKUP_DIR, f"{safe_path}_{filename}")
    if os.path.exists(backup_file):
        with open(backup_file, 'r', encoding='utf-8') as f:
            return f.read()
            
    return None

def clear_offline_backup():
    if os.path.exists(BACKUP_DIR):
        import shutil
        shutil.rmtree(BACKUP_DIR)

def backup_all_instances_to_cache():
    if not is_vm2_running(): return
    import sys
    # 由於在 api.py や minecraft.py 呼叫，必須確保載入 models
    api_path = "/home/terraria/servers/web_interface"
    if api_path not in sys.path: sys.path.append(api_path)
    try:
        from models import InstanceManager
        mgr = InstanceManager()
    except Exception as e:
        print("[ProxyHelper] Cannot load models: ", e)
        return

    allowed_files = ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json']
    for inst in mgr.get_all_instances():
        for fname in allowed_files:
            fpath = os.path.join(inst.path, fname)
            res = proxy_to_agent("read_file", filepath=fpath)
            if isinstance(res, dict) and res.get("status") == "success":
                save_offline_backup(inst.path, fname, res.get("content"))

def flush_offline_cache():
    clear_offline_backup() # 通電開機後備份即無效
    if not is_vm2_running(): return
    if not os.path.exists(SYNC_DIR): return
    
    import base64
    for fname in os.listdir(SYNC_DIR):
        if '_' not in fname: continue
        safe_path, real_filename = fname.split('_', 1)
        instance_path = base64.urlsafe_b64decode(safe_path).decode()
        
        with open(os.path.join(SYNC_DIR, fname), 'r', encoding='utf-8') as f:
            content = f.read()
            
        full_dest = os.path.join(instance_path, real_filename)
        res = proxy_to_agent("write_file", filepath=full_dest, content=content)
        if res.get("status") == "success":
            os.remove(os.path.join(SYNC_DIR, fname))

