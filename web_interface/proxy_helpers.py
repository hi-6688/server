import json
import os
import aiohttp
import asyncio

VM_NAME = "instance-20260220-174959"
AGENT_PORT = 9999
AGENT_SECRET = "hihi_secret_key_2026"
SYNC_DIR = "/home/terraria/servers/web_interface/.sync"

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

def read_offline_cache(instance_path, filename):
    import base64
    safe_path = base64.urlsafe_b64encode(instance_path.encode()).decode()
    cache_file = os.path.join(SYNC_DIR, f"{safe_path}_{filename}")
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def flush_offline_cache():
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

