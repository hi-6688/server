import json
import os
import aiohttp
import asyncio

VM_NAME = "instance-20260220-174959"
AGENT_PORT = 9999
AGENT_SECRET = "hihi_secret_key_2026"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYNC_DIR = os.path.join(BASE_DIR, ".sync")
BACKUP_DIR = os.path.join(BASE_DIR, ".backup_cache")

# Use the GCPManager from discord_bot to keep logic DRY
import sys
_parent_dir = os.path.dirname(BASE_DIR)
if os.path.exists(os.path.join(_parent_dir, "discord_bot")):
    sys.path.append(os.path.join(_parent_dir, "discord_bot"))
# 在 Docker 環境中，utils 已直接掛載到 /app/utils，所以直接 import 即可
try:
    from utils.gcp_manager import GCPManager
    gcp = GCPManager(project_id="project-ad2eecb1-dd0f-4cf4-b1a", zone="asia-east1-c")
except Exception as e:
    print(f"Warning: Failed to initialize GCPManager. Using mock. Error: {e}")
    class MockGCPManager:
        def get_instance_status(self, name): return "RUNNING"
        def get_instance_ip(self, name): return "127.0.0.1"
        def get_instance_public_ip(self, name): return "127.0.0.1"
        def start_instance(self, name): return True
    gcp = MockGCPManager()

import time

_vm_cache = {
    'status': None, 'status_time': 0,
    'ip': None, 'ip_time': 0,
    'public_ip': None, 'public_ip_time': 0
}
CACHE_TTL = 10  # 快取 10 秒

def is_vm2_running():
    global _vm_cache
    if time.time() - _vm_cache['status_time'] > CACHE_TTL:
        _vm_cache['status'] = gcp.get_instance_status(VM_NAME) == "RUNNING"
        _vm_cache['status_time'] = time.time()
    return _vm_cache['status']

def get_vm2_ip():
    global _vm_cache
    if time.time() - _vm_cache['ip_time'] > CACHE_TTL:
        _vm_cache['ip'] = gcp.get_instance_ip(VM_NAME)
        _vm_cache['ip_time'] = time.time()
    return _vm_cache['ip']

def get_vm2_public_ip():
    global _vm_cache
    if time.time() - _vm_cache['public_ip_time'] > CACHE_TTL:
        _vm_cache['public_ip'] = gcp.get_instance_public_ip(VM_NAME)
        _vm_cache['public_ip_time'] = time.time()
    return _vm_cache['public_ip']

def start_vm2_and_wait():
    """發送開機指令並等待 VM 進入 RUNNING 狀態"""
    global _vm_cache
    if is_vm2_running(): return True
    
    # 送出開機請求
    success = gcp.start_instance(VM_NAME)
    if not success: return False
    
    # 輪詢等待 30 秒
    for _ in range(15):
        time.sleep(2)
        status = gcp.get_instance_status(VM_NAME)
        if status == "RUNNING":
            # 強制清除快取，以取得新 IP
            _vm_cache['status_time'] = 0
            _vm_cache['ip_time'] = 0
            _vm_cache['public_ip_time'] = 0
            return True
            
    return False

import requests

def proxy_to_agent(action, **kwargs):
    ip = get_vm2_ip()
    if not ip:
        return {"status": "error", "message": "VM2 offline"}
    
    url = f"http://{ip}:{AGENT_PORT}/"
    headers = {"Authorization": f"Bearer {AGENT_SECRET}", "Content-Type": "application/json"}
    payload = {"action": action, **kwargs}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
    if BASE_DIR not in sys.path: sys.path.append(BASE_DIR)
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

