import http.server
import socketserver
import urllib.parse
import os
import json
import subprocess
import socket
import shutil
import time
import struct
import zipfile
import io
import tempfile
import datetime
import uuid
import re

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import proxy_helpers

# Configuration
PORT = 24445
API_KEY = "AdminKey123456"
LOGIN_PASSWORD = "hmpb"

# Multi-Instance Configuration
INSTANCES_FILE = '/home/terraria/servers/web_interface/instances.json'
DEFAULT_SERVER_ROOT = '/home/terraria/servers/minecraft'

class Instance:
    def __init__(self, data):
        self.uuid = data.get('uuid')
        self.name = data.get('name')
        self.path = data.get('path')
        self.port = int(data.get('port', 19132))
        self.screen_name = data.get('screen_name')
        self.discord_channel_id = data.get('discord_channel_id', "") # Optional
        self.created_at = data.get('created_at', time.time())

    def to_dict(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'path': self.path,
            'port': self.port,
            'screen_name': self.screen_name,
            'discord_channel_id': self.discord_channel_id,
            'created_at': self.created_at
        }

    def get_log_file(self):
        return os.path.join(self.path, 'bedrock_screen.log')

    def is_running(self):
        # 1. Check UDP port (If bind fails, it's open/used? No, if bind fails, it IS used)
        # Wait, if bind FAILS, it means port is IN USE (Running).
        # If bind SUCCEEDS, it means port is FREE (Not Running).
        port_open = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', self.port))
            sock.close()
            port_open = True # Bind success = Port Free = Not Running
        except OSError:
            port_open = False # Bind fail = Port Used = Running

        if port_open: return False

        # 2. Check Screen Session
        try:
            cmd = f"screen -ls | grep -q '\\.{self.screen_name}\\s'"
            subprocess.check_call(cmd, shell=True)
            return True
        except subprocess.CalledProcessError:
            return False

class InstanceManager:
    def __init__(self):
        self.instances = {}
        self.load_instances()

    def load_instances(self):
        if os.path.exists(INSTANCES_FILE):
            try:
                with open(INSTANCES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for inst_data in data.get('instances', []):
                        instance = Instance(inst_data)
                        self.instances[instance.uuid] = instance
            except Exception as e:
                print(f"Error loading instances: {e}")
        
        # Ensure 'main' instance always exists
        if 'main' not in self.instances:
            print("Initializing default 'main' instance...")
            main_instance = Instance({
                'uuid': 'main',
                'name': '主伺服器 (Main)',
                'path': DEFAULT_SERVER_ROOT,
                'port': 19132,
                'screen_name': 'bedrock',
                'discord_channel_id': ""
            })
            self.instances['main'] = main_instance
            self.save_instances()

    def save_instances(self):
        data = {'instances': [inst.to_dict() for inst in self.instances.values()]}
        try:
            with open(INSTANCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving instances: {e}")

    def get_instance(self, uuid):
        return self.instances.get(uuid)

    def get_all_instances(self):
        return list(self.instances.values())

    def create_instance(self, name, port, discord_channel_id=""):
        # Validate Port
        for inst in self.instances.values():
            if int(inst.port) == int(port):
                raise ValueError(f"Port {port} is already in use by {inst.name}")

        new_uuid = str(uuid.uuid4())
        new_path = f"/home/terraria/servers/instances/{new_uuid}"
        
        # 1. Copy Server Files
        if not os.path.exists(DEFAULT_SERVER_ROOT):
             raise FileNotFoundError("Default server root not found, cannot clone.")

        print(f"Cloning server to {new_path}...")
        try:
            def ignore_patterns(path, names):
                return ['worlds', 'backups', 'bedrock_screen.log', 'bedrock_input', 'server.properties', 'server.properties.bak', 'white-list.txt', 'whitelist.json', 'permissions.json']

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.copytree(DEFAULT_SERVER_ROOT, new_path, ignore=ignore_patterns, dirs_exist_ok=True)
            os.makedirs(os.path.join(new_path, 'worlds'), exist_ok=True)

        except Exception as e:
            if os.path.exists(new_path):
                shutil.rmtree(new_path)
            raise e

        # 2. Configure server.properties
        props_path = os.path.join(new_path, 'server.properties')
        content = "server-name=Dedicated Server\ngamerule-keepinventory=true\n"
        src_props = os.path.join(DEFAULT_SERVER_ROOT, 'server.properties')
        if os.path.exists(src_props):
            with open(src_props, 'r', encoding='utf-8') as f:
                content = f.read()
        
        new_content = ""
        found_port, found_portv6, found_name, found_level = False, False, False, False
        for line in content.splitlines():
            if line.strip().startswith('server-port='):
                new_content += f"server-port={port}\n"
                found_port = True
            elif line.strip().startswith('server-portv6='):
                new_content += f"server-portv6={int(port)+1}\n"
                found_portv6 = True
            elif line.strip().startswith('server-name='):
                new_content += f"server-name={name}\n"
                found_name = True
            elif line.strip().startswith('level-name='):
                # 為新實例設定獨立的世界名稱
                new_content += f"level-name={name}\n"
                found_level = True
            else:
                new_content += line + "\n"
        
        if not found_port: new_content += f"server-port={port}\n"
        if not found_portv6: new_content += f"server-portv6={int(port)+1}\n"
        if not found_name: new_content += f"server-name={name}\n"
        if not found_level: new_content += f"level-name={name}\n"

        with open(props_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # 2.5 自動為新世界啟用 ChatLogger
        # 找出 level-name 以建立對應的世界資料夾
        level_name = name  # 預設用實例名稱
        for line in new_content.splitlines():
            if line.strip().startswith('level-name='):
                level_name = line.strip().split('=', 1)[1]
                break
        world_dir = os.path.join(new_path, 'worlds', level_name)
        os.makedirs(world_dir, exist_ok=True)
        # 寫入 world_behavior_packs.json 啟用 ChatLogger
        chatlogger_manifest = [{"pack_id": "e4b3e6d2-1234-4567-8901-abcdef123456", "version": [1, 0, 0]}]
        with open(os.path.join(world_dir, 'world_behavior_packs.json'), 'w') as f:
            json.dump(chatlogger_manifest, f, indent=2)
        print(f"ChatLogger auto-enabled for world '{level_name}'")

        # 2.6 複製 config/default/permissions.json（Script API 模組權限）
        src_perms = os.path.join(DEFAULT_SERVER_ROOT, 'config', 'default', 'permissions.json')
        if os.path.exists(src_perms):
            dst_perms_dir = os.path.join(new_path, 'config', 'default')
            os.makedirs(dst_perms_dir, exist_ok=True)
            shutil.copy2(src_perms, os.path.join(dst_perms_dir, 'permissions.json'))
            print(f"Script API permissions copied for instance '{name}'")

        # 3. Create Instance Object
        new_instance = Instance({
            'uuid': new_uuid,
            'name': name,
            'path': new_path,
            'port': int(port),
            'screen_name': f"bedrock_{port}",
            'discord_channel_id': discord_channel_id
        })
        
        self.instances[new_uuid] = new_instance
        self.save_instances()
        return new_instance

    def delete_instance(self, uuid):
        if uuid == 'main':
            raise ValueError("Cannot delete main instance.")
        
        inst = self.get_instance(uuid)
        if not inst:
            raise ValueError("Instance not found")
            
        if inst.is_running():
            subprocess.run(['screen', '-S', inst.screen_name, '-X', 'quit'])
            time.sleep(2)
        
        del self.instances[uuid]
        self.save_instances()
        
        if os.path.exists(inst.path) and "/instances/" in inst.path and len(inst.path) > 20: 
            shutil.rmtree(inst.path)

    def update_instance(self, uuid, name=None, port=None, discord_channel_id=None):
        inst = self.get_instance(uuid)
        if not inst:
            raise ValueError("Instance not found")
        
        if name: inst.name = name
        if discord_channel_id is not None: inst.discord_channel_id = discord_channel_id
        
        if port and int(port) != inst.port:
            # Check port conflict
            for other in self.instances.values():
                if other.uuid != uuid and int(other.port) == int(port):
                    raise ValueError(f"Port {port} is already in use by {other.name}")
            inst.port = int(port)
            inst.screen_name = f"bedrock_{port}" if uuid != 'main' else inst.screen_name
            # Update server.properties
            props_path = os.path.join(inst.path, 'server.properties')
            if os.path.exists(props_path):
                with open(props_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = ''
                for line in content.splitlines():
                    if line.strip().startswith('server-port='): new_content += f"server-port={port}\n"
                    elif line.strip().startswith('server-portv6='): new_content += f"server-portv6={int(port)+1}\n"
                    elif line.strip().startswith('server-name=') and name: new_content += f"server-name={name}\n"
                    else: new_content += line + '\n'
                with open(props_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        
        self.save_instances()
        return inst

instance_manager = InstanceManager()

class ReuseAddrTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def _set_headers(self, code=200, content_type='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def _read_level_name(self, level_dat_path):
        try:
            with open(level_dat_path, 'rb') as f:
                data = f.read()
            search_pattern = b'\x08\x09\x00LevelName'
            idx = data.find(search_pattern)
            if idx == -1: return None
            val_len_idx = idx + len(search_pattern)
            if val_len_idx + 2 > len(data): return None
            name_len = struct.unpack('<H', data[val_len_idx:val_len_idx+2])[0]
            name_start = val_len_idx + 2
            if name_start + name_len > len(data): return None
            return data[name_start:name_start+name_len].decode('utf-8', errors='ignore')
        except:
            return None

    def _install_single_pack(self, zf, filename, instance_path, forced_type=''):
        """從 zip 中讀取 manifest.json，判斷類型並安裝到正確目錄"""
        # 統一將反斜線轉為正斜線（Windows 建立的 zip 可能用反斜線）
        raw_names = zf.namelist()
        names = [n.replace('\\', '/') for n in raw_names]
        # 建立原始名稱對照表（讀取 zip 內容時需要用原始名稱）
        name_map = dict(zip(names, raw_names))
        
        # 找到 manifest.json
        manifest_path = None
        for n in names:
            if n.endswith('manifest.json') and n.count('/') <= 1:
                manifest_path = n
                break
        
        if not manifest_path:
            return None
        
        try:
            raw = zf.read(name_map[manifest_path])
            # 處理 BOM（UTF-8 with BOM）
            manifest = json.loads(raw.decode('utf-8-sig'))
        except:
            return None
        
        header = manifest.get('header', {})
        pack_uuid = header.get('uuid', '')
        pack_version = header.get('version', [1, 0, 0])
        pack_name = header.get('name', os.path.splitext(filename)[0])
        
        # 從 modules 判斷 pack 類型
        modules = manifest.get('modules', [])
        detected_type = 'behavior_packs'  # 預設
        for mod in modules:
            mod_type = mod.get('type', '').lower()
            if mod_type in ('resources', 'resource'):
                detected_type = 'resource_packs'
                break
            elif mod_type in ('data', 'script', 'javascript'):
                detected_type = 'behavior_packs'
                break
        
        # 如果使用者指定了類型，優先使用
        pack_type = forced_type if forced_type else detected_type
        
        # 安裝到對應目錄（用安全的資料夾名稱）
        addon_dir = os.path.join(instance_path, pack_type)
        os.makedirs(addon_dir, exist_ok=True)
        
        # 用 pack 名稱作為資料夾名稱（更易識別），保留英文安全字元
        safe_name = re.sub(r'[^\w\-.]', '_', pack_name) if re.search(r'[a-zA-Z]', pack_name) else pack_uuid
        target_dir = os.path.join(addon_dir, safe_name)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)  # 覆蓋舊版本
        os.makedirs(target_dir, exist_ok=True)
        
        # 如果 manifest 在子目錄中，需要調整解壓路徑
        prefix = os.path.dirname(manifest_path)
        for name in names:
            if prefix and name.startswith(prefix):
                rel_path = name[len(prefix):].lstrip('/')
            else:
                rel_path = name
            if not rel_path or name.endswith('/'):
                continue
            target_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'wb') as out:
                out.write(zf.read(name_map[name]))
        
        print(f"Pack installed: {pack_name} ({pack_uuid}) -> {pack_type}/{safe_name}")
        return {
            'uuid': pack_uuid,
            'version': pack_version,
            'name': pack_name,
            'type': pack_type
        }

    def _register_packs_to_world(self, instance, packs):
        """將安裝的 pack 自動註冊到世界的 packs JSON"""
        # 讀取 level-name
        active_world = ''
        props_path = os.path.join(instance.path, 'server.properties')
        if os.path.exists(props_path):
            with open(props_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('level-name='):
                        active_world = line.strip().split('=', 1)[1]
                        break
        if not active_world:
            return
        
        world_path = os.path.join(instance.path, 'worlds', active_world)
        os.makedirs(world_path, exist_ok=True)
        
        for pack in packs:
            if pack['type'] == 'resource_packs':
                json_file = os.path.join(world_path, 'world_resource_packs.json')
            else:
                json_file = os.path.join(world_path, 'world_behavior_packs.json')
            
            # 讀取現有清單
            existing = []
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except: existing = []
            
            # 檢查是否已存在（避免重複）
            already_exists = any(p.get('pack_id') == pack['uuid'] for p in existing)
            if not already_exists:
                existing.append({
                    'pack_id': pack['uuid'],
                    'version': pack['version']
                })
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, indent=2)
                print(f"Registered pack {pack['name']} to {os.path.basename(json_file)}")

    def _sync_cheats_enabled(self, instance):
        """同步 level.dat 的 cheatsEnabled 與 server.properties 的 allow-cheats"""
        try:
            # 讀取 server.properties 的 allow-cheats
            allow_cheats = False
            props_path = os.path.join(instance.path, 'server.properties')
            if os.path.exists(props_path):
                with open(props_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('allow-cheats='):
                            allow_cheats = line.strip().split('=', 1)[1].lower() == 'true'
                            break
            
            # 讀取 level-name
            active_world = ''
            with open(props_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('level-name='):
                        active_world = line.strip().split('=', 1)[1]
                        break
            if not active_world:
                return
            
            # 修改 level.dat
            dat_path = os.path.join(instance.path, 'worlds', active_world, 'level.dat')
            if not os.path.exists(dat_path):
                return
            
            with open(dat_path, 'rb') as f:
                data = bytearray(f.read())
            
            tag_name = b'cheatsEnabled'
            search = b'\x01' + struct.pack('<H', len(tag_name)) + tag_name
            idx = data.find(search)
            if idx == -1:
                return
            
            val_idx = idx + len(search)
            target_val = 1 if allow_cheats else 0
            if data[val_idx] != target_val:
                data[val_idx] = target_val
                with open(dat_path, 'wb') as f:
                    f.write(data)
                print(f"Synced cheatsEnabled = {target_val} for world '{active_world}'")
        except Exception as e:
            print(f"Warning: Failed to sync cheatsEnabled: {e}")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        
        # 跳過 multipart 檔案上傳路由的 body 預讀（避免消耗 rfile）
        skip_body_paths = ['/upload', '/addon/upload']
        params = {}
        if parsed.path not in skip_body_paths:
            if content_length > 0:
                try:
                    params = json.loads(self.rfile.read(content_length).decode('utf-8'))
                except: params = {}

        # Auth
        if parsed.path != '/login':
            key_in_query = urllib.parse.parse_qs(parsed.query).get('key', [''])[0]
            if params.get('key') != API_KEY and key_in_query != API_KEY:
                 self._set_headers(403); self.wfile.write(b'{"error":"Forbidden"}'); return

        # Instance Context
        instance_id = params.get('instance_id')
        if not instance_id: instance_id = urllib.parse.parse_qs(parsed.query).get('instance_id', ['main'])[0]
        current_instance = instance_manager.get_instance(instance_id)

        if not current_instance and not (parsed.path in ['/instances/create', '/login', '/save_config']):
            self._set_headers(404); self.wfile.write(b'{"error":"Instance not found"}'); return

        if parsed.path == '/login':
            if params.get('password') == LOGIN_PASSWORD:
                 self._set_headers(); self.wfile.write(json.dumps({"status":"ok", "key": API_KEY}).encode('utf-8'))
            else:
                 self._set_headers(401); self.wfile.write(b'{"error":"Invalid password"}')

        elif parsed.path == '/instances/create':
            try:
                new_inst = instance_manager.create_instance(params.get('name'), params.get('port'), params.get('discord_channel_id', ""))
                self._set_headers(); self.wfile.write(json.dumps({"status": "ok", "instance": new_inst.to_dict()}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/instances/delete':
            try:
                instance_manager.delete_instance(params.get('uuid'))
                self._set_headers(); self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/instances/update':
            try:
                updated = instance_manager.update_instance(
                    params.get('uuid'), params.get('name'), params.get('port'), params.get('discord_channel_id'))
                self._set_headers(); self.wfile.write(json.dumps({"status": "ok", "instance": updated.to_dict()}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/start':
            # Check if VM2 is running
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409)
                self.wfile.write(b'{"error":"VM2 is offline. Please use /mc\u958b\u6a5f to boot the server first."}')
                return
                
            # Sync offline cache first
            proxy_helpers.flush_offline_cache()
            
            try:
                res = proxy_helpers.proxy_to_agent("execute_command", screen_name=current_instance.screen_name, command="")
                if res.get('status') == 'success':
                    # Instead of running screen here, agent should ideally start it if not running
                    # Let's send a custom 'start_server' action
                    start_cmd = f"cd {current_instance.path} && screen -dmS {current_instance.screen_name} -L -Logfile bedrock_screen.log bash -c 'LD_LIBRARY_PATH=. ./bedrock_server; exec bash'"
                    res_start = proxy_helpers.proxy_to_agent("start_screen", screen_name=current_instance.screen_name, path=current_instance.path)
                    
                    self._set_headers(); self.wfile.write(b'{"status":"started"}')
                else:
                    self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/stop':
            try:
                if proxy_helpers.is_vm2_running():
                    proxy_helpers.proxy_to_agent("execute_command", screen_name=current_instance.screen_name, command="stop")
                    time.sleep(3)
                    proxy_helpers.proxy_to_agent("execute_command", screen_name=current_instance.screen_name, command='\x03') # Ctrl+C just in case
                self._set_headers(); self.wfile.write(b'{"status":"stopped"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/command':
            cmd = params.get('cmd', '')
            if not cmd: self._set_headers(400); return
            try:
                if proxy_helpers.is_vm2_running():
                    proxy_helpers.proxy_to_agent("execute_command", screen_name=current_instance.screen_name, command=cmd)
                    if cmd.strip() in ['list', 'gamerule ']: time.sleep(1.0)
                self._set_headers(); self.wfile.write(json.dumps({"result": "sent"}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/write':
            filename = params.get('file')
            if filename not in ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json']:
                self._set_headers(403); self.wfile.write(b'{"error":"File not allowed"}'); return
            
            content = params.get('content')
            full_dest = os.path.join(current_instance.path, filename)
            
            try:
                if proxy_helpers.is_vm2_running():
                    # Sync to remote
                    res = proxy_helpers.proxy_to_agent("write_file", filepath=full_dest, content=content)
                    if res.get('status') == 'success':
                        self._set_headers(); self.wfile.write(b'{"status":"saved"}')
                    else:
                        self._set_headers(500); self.wfile.write(json.dumps({"error": res.get('message')}).encode('utf-8'))
                else:
                    # Offline Cache
                    proxy_helpers.save_offline_cache(current_instance.path, filename, content)
                    self._set_headers(); self.wfile.write(b'{"status":"saved_offline"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        elif parsed.path == '/update':
            try:
                url = urllib.parse.parse_qs(parsed.query).get('url', [''])[0]
                if not url: url = params.get('url')
                if not url: raise ValueError("No URL provided")
                
                if not proxy_helpers.is_vm2_running():
                    self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
                
                res = proxy_helpers.proxy_to_agent("update_server", path=current_instance.path, url=url, screen_name=current_instance.screen_name)
                if res.get('status') == 'success':
                    self._set_headers(); self.wfile.write(b'{"status":"updated"}')
                else:
                    self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/save_config':
            self._set_headers(); self.wfile.write(b'{"status":"saved"}')

        elif parsed.path == '/delete_world':
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
                
            world = params.get('world')
            if world:
                res = proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(current_instance.path, 'worlds', world))
                self._set_headers(); self.wfile.write(b'{"status":"deleted"}')

        elif parsed.path == '/reset_world':
            # 重置世界地形，但保留設定（level.dat）和模組（world_*_packs.json）
            try:
                if not proxy_helpers.is_vm2_running():
                    self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
                
                # 讀取目前使用的世界名稱
                active_world = ''
                props_path = os.path.join(current_instance.path, 'server.properties')
                
                # Call agent to read the file
                res_props = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)
                if res_props.get('status') == 'success':
                    content = res_props.get('content', '')
                    for line in content.splitlines():
                        if line.strip().startswith('level-name='):
                            active_world = line.strip().split('=', 1)[1]
                            break
                            
                if not active_world:
                    self._set_headers(400); self.wfile.write(b'{"error":"Cannot determine active world"}'); return

                # Ask agent to reset it
                res = proxy_helpers.proxy_to_agent("reset_world", path=os.path.join(current_instance.path, 'worlds', active_world), screen_name=current_instance.screen_name)
                
                if res.get('status') == 'success':
                    self._set_headers(); self.wfile.write(json.dumps({
                        "status": "ok", 
                        "world": active_world,
                        "message": "地形資料已重置，設定與模組已保留"
                    }).encode('utf-8'))
                else:
                    self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/upload':
            # 處理 multipart FormData 上傳的世界檔案
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
            try:
                data_len = int(self.headers.get('Content-Length', 0))
                raw_data = self.rfile.read(data_len)
                
                content_type = self.headers.get('Content-Type', '')
                file_data = raw_data
                
                if 'boundary=' in content_type:
                    boundary = content_type.split('boundary=')[1].strip()
                    if boundary.startswith('"') and boundary.endswith('"'): boundary = boundary[1:-1]
                    parts = raw_data.split(('--' + boundary).encode())
                    for part in parts:
                        if b'filename=' in part:
                            header_end = part.find(b'\r\n\r\n')
                            if header_end == -1: header_end = part.find(b'\n\n')
                            if header_end != -1:
                                file_data = part[header_end+4:].rstrip(b'\r\n--')
                            break
                
                import base64
                encoded_data = base64.b64encode(file_data).decode('utf-8')
                res = proxy_helpers.proxy_to_agent("upload_zip", path=os.path.join(current_instance.path, 'worlds'), file_data_base64=encoded_data)
                
                if res.get('status') == 'success':
                    self._set_headers(); self.wfile.write(b'{"status":"ok", "message":"Uploaded"}')
                else:
                    self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
            except Exception as e:
                import traceback; traceback.print_exc()
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/switch_world':
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
            world = params.get('world')
            if not world:
                self._set_headers(400); self.wfile.write(b'{"error":"No world name"}'); return
            try:
                props_path = os.path.join(current_instance.path, 'server.properties')
                res = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)
                
                if res.get('status') == 'success':
                    content = res.get('content', '')
                    new_content = ''
                    found = False
                    for line in content.splitlines():
                        if line.strip().startswith('level-name='):
                            new_content += f"level-name={world}\n"
                            found = True
                        else:
                            new_content += line + '\n'
                    if not found:
                        new_content += f"level-name={world}\n"
                        
                    proxy_helpers.proxy_to_agent("write_file", filepath=props_path, content=new_content)
                
                self._set_headers(); self.wfile.write(b'{"status":"switched"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/exec':
            # 執行伺服器指令並回傳 log 尾部
            cmd = params.get('cmd', '')
            if not cmd:
                self._set_headers(400); self.wfile.write(b'{"error":"No command"}'); return
            try:
                subprocess.run(['screen', '-S', current_instance.screen_name, '-p', '0', '-X', 'stuff', f'{cmd}\\n'])
                time.sleep(1.5)
                log_file = current_instance.get_log_file()
                output = ''
                if os.path.exists(log_file):
                    output = subprocess.check_output(['tail', '-n', '20', log_file]).decode('utf-8', errors='replace')
                self._set_headers(); self.wfile.write(json.dumps({"result": output}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/addon/upload':
            # 處理 multipart FormData 上傳的模組檔案
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
            try:
                data_len = int(self.headers.get('Content-Length', 0))
                raw_data = self.rfile.read(data_len)
                
                content_type = self.headers.get('Content-Type', '')
                file_data = raw_data
                original_filename = 'addon.zip'
                
                if 'boundary=' in content_type:
                    boundary = content_type.split('boundary=')[1].strip()
                    if boundary.startswith('"') and boundary.endswith('"'): boundary = boundary[1:-1]
                    parts = raw_data.split(('--' + boundary).encode())
                    for part in parts:
                        if b'filename=' in part:
                            header_end = part.find(b'\r\n\r\n')
                            if header_end == -1: header_end = part.find(b'\n\n')
                            if header_end != -1:
                                file_data = part[header_end+4:].rstrip(b'\r\n--')
                                header_str = part[:header_end].decode('utf-8', errors='replace')
                                fn_match = re.search(r'filename="([^"]+)"', header_str)
                                if fn_match: original_filename = fn_match.group(1)
                            break
                            
                addon_type = urllib.parse.parse_qs(parsed.query).get('type', [''])[0]
                import base64
                encoded_data = base64.b64encode(file_data).decode('utf-8')
                
                res = proxy_helpers.proxy_to_agent("upload_addon", path=current_instance.path, addon_type=addon_type, original_filename=original_filename, file_data_base64=encoded_data)
                
                if res.get('status') == 'success':
                    self._set_headers(); self.wfile.write(json.dumps({
                        "status": "ok", 
                        "message": res.get("message", "Uploaded"),
                        "packs": res.get("packs", [])
                    }).encode('utf-8'))
                else:
                    self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
            except Exception as e:
                import traceback; traceback.print_exc()
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/addon/delete':
            if not proxy_helpers.is_vm2_running():
                # Cannot delete addons if offline
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
            addon_name = params.get('name', '')
            addon_type = params.get('type', 'behavior_packs')
            if not addon_name:
                self._set_headers(400); self.wfile.write(b'{"error":"No addon name"}'); return
            try:
                res = proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(current_instance.path, addon_type, addon_name))
                self._set_headers(); self.wfile.write(b'{"status":"deleted"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self._set_headers(404); self.wfile.write(b'{"error":"Not Found"}')


    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        get_param = lambda k: params.get(k, [''])[0]

        # Auth
        # Only enforce Auth for API endpoints, allow static files (admin.html, etc)
        api_endpoints = ['/instances/list', '/server_status', '/stats', '/read', '/worlds', '/addons', '/version', '/start', '/stop']
        if parsed.path in api_endpoints and get_param('key') != API_KEY:
             self._set_headers(403); self.wfile.write(b'{"error":"Forbidden"}'); return

        # Instance
        instance_id = get_param('instance_id') or 'main'
        current_instance = instance_manager.get_instance(instance_id)

        if not current_instance and parsed.path != '/instances/list':
            self._set_headers(404); self.wfile.write(b'{"error":"Instance not found"}'); return

        if parsed.path == '/instances/list':
            insts = []
            for i in instance_manager.get_all_instances():
                d = i.to_dict(); d['is_running'] = i.is_running(); insts.append(d)
            self._set_headers(); self.wfile.write(json.dumps({"instances": insts}).encode('utf-8'))

        elif parsed.path == '/server_status':
            self._set_headers()
            self.wfile.write(json.dumps({"running": current_instance.is_running()}).encode('utf-8'))

        elif parsed.path == '/start':
            if current_instance.is_running():
                self._set_headers(409); self.wfile.write(b'{"error":"Server already running"}'); return
            try:
                cmd = f'cd {current_instance.path} && screen -dmS {current_instance.screen_name} -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"'
                subprocess.run(cmd, shell=True, check=True)
                self._set_headers(); self.wfile.write(b'{"status":"started"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/stop':
            try:
                # 先發送 stop 指令讓伺服器優雅關閉
                subprocess.run(['screen', '-S', current_instance.screen_name, '-p', '0', '-X', 'stuff', 'stop\n'])
                time.sleep(3)
                # 如果還沒關閉，強制結束 screen
                subprocess.run(['screen', '-S', current_instance.screen_name, '-X', 'quit'], stderr=subprocess.DEVNULL)
                self._set_headers(); self.wfile.write(b'{"status":"stopped"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/version':
            version = 'Unknown'
            try:
                # 從 bedrock_screen.log 讀取版本（最可靠）
                log_file = current_instance.get_log_file()
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        for line in f:
                            if 'Version:' in line:
                                match = re.search(r'Version:\s*(\S+)', line)
                                if match:
                                    version = match.group(1)
                                break  # 版本通常在前幾行
            except: pass
            self._set_headers()
            self.wfile.write(json.dumps({"version": version}).encode('utf-8'))

        elif parsed.path == '/stats':
            # CPU/RAM
            try:
                with open('/proc/loadavg', 'r') as f: load = f.read().split()[0]
                with open('/proc/meminfo', 'r') as f:
                    m = f.read(); 
                    tot = int(re.search(r'MemTotal:\s+(\d+)', m).group(1))
                    av = int(re.search(r'MemAvailable:\s+(\d+)', m).group(1))
                    used_gb = round((tot-av)/1024/1024, 2); tot_gb = round(tot/1024/1024, 2)
                    perc = round(((tot-av)/tot)*100, 1)
                
                resp = {
                    "cpu": {"load_1": float(load), "load_5": 0.0},
                    "memory": {"percent": perc, "used": f"{used_gb} GB", "total": f"{tot_gb} GB"},
                    "disk": {"percent": 0, "used": "0 GB", "total": "0 GB"},
                    "network": {"rx_gb": "0", "tx_gb": "0"}
                }
                self._set_headers(); self.wfile.write(json.dumps(resp).encode('utf-8'))
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error":str(e)}).encode('utf-8'))

        elif parsed.path == '/read':
            fpath = os.path.join(current_instance.path, get_param('file'))
            if get_param('file') in ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json', 'bedrock_screen.log']:
                
                # Check offline cache first
                cached_content = proxy_helpers.read_offline_cache(current_instance.path, get_param('file'))
                if cached_content is not None:
                     self._set_headers(); self.wfile.write(json.dumps({"content": cached_content, "source": "offline_cache"}).encode('utf-8'))
                     return
                     
                if proxy_helpers.is_vm2_running():
                     lines = get_param('lines')
                     if lines:
                          res = proxy_helpers.proxy_to_agent("read_log_tail", filepath=fpath, lines=int(lines))
                     else:
                          res = proxy_helpers.proxy_to_agent("read_file", filepath=fpath)
                          
                     if res.get('status') == 'success':
                          content = res.get('content', '')
                          self._set_headers(); self.wfile.write(json.dumps({"content": content}).encode('utf-8'))
                     else:
                          self._set_headers(404); self.wfile.write(b'{"content":""}')
                else:
                    self._set_headers(404); self.wfile.write(b'{"content":""}')
            else:
                 self._set_headers(404); self.wfile.write(b'{"content":""}')
        
        elif parsed.path == '/worlds':
            if not proxy_helpers.is_vm2_running():
                # Cannot fetch worlds if offline
                self._set_headers(); self.wfile.write(json.dumps({"worlds": [], "active": "Offline"}).encode('utf-8'))
                return
                
            res = proxy_helpers.proxy_to_agent("list_worlds", path=current_instance.path)
            if res.get('status') == 'success':
                self._set_headers()
                self.wfile.write(json.dumps({"worlds": res.get("worlds", []), "active": res.get("active", "")}).encode('utf-8'))
            else:
                self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))

        elif parsed.path == '/addons':
            if not proxy_helpers.is_vm2_running():
                # Cannot fetch addons if offline
                self._set_headers(); self.wfile.write(json.dumps({"addons": []}).encode('utf-8'))
                return
                
            res = proxy_helpers.proxy_to_agent("list_addons", path=current_instance.path)
            if res.get('status') == 'success':
                self._set_headers()
                self.wfile.write(json.dumps({"addons": res.get("addons", [])}).encode('utf-8'))
            else:
                self._set_headers(500); self.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))

        elif parsed.path == '/download':
            if not proxy_helpers.is_vm2_running():
                self._set_headers(409); self.wfile.write(b'{"error":"VM2 is offline"}'); return
                
            world = get_param('world')
            if not world:
                self._set_headers(400); self.wfile.write(b'{"error":"No world specified"}'); return
                
            try:
                res = proxy_helpers.proxy_to_agent("download_world", path=os.path.join(current_instance.path, 'worlds', world))
                if res.get('status') == 'success' and 'base64_data' in res:
                    import base64
                    data = base64.b64decode(res['base64_data'])
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/zip')
                    self.send_header('Content-Disposition', f'attachment; filename="{world}.zip"')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self._set_headers(404); self.wfile.write(b'{"error":"World folder not found or zip failed"}')
            except Exception as e:
                self._set_headers(500); self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/public_config':
            # 回傳當前實例的公開資訊
            config = {
                'server_title': current_instance.name,
                'port': current_instance.port,
                'ip': '39.12.35.16'
            }
            # 如果有所有實例清單，提供選擇
            instances_public = []
            for inst in instance_manager.get_all_instances():
                instances_public.append({'name': inst.name, 'port': inst.port, 'uuid': inst.uuid})
            config['instances'] = instances_public
            self._set_headers(); self.wfile.write(json.dumps(config).encode('utf-8'))

        else:
            # File Server
            requested_path = parsed.path.lstrip('/')
            if not requested_path: requested_path = 'index.html'
            
            # 優先讀取 React build 目錄
            dist_path = os.path.join('frontend', 'dist', requested_path)
            if os.path.exists(dist_path) and os.path.isfile(dist_path):
                 if requested_path.endswith('.html'): ctype = 'text/html'
                 elif requested_path.endswith('.js'): ctype = 'application/javascript'
                 elif requested_path.endswith('.css'): ctype = 'text/css'
                 elif requested_path.endswith('.svg'): ctype = 'image/svg+xml'
                 elif requested_path.endswith('.png'): ctype = 'image/png'
                 elif requested_path.endswith('.jpg') or requested_path.endswith('.jpeg'): ctype = 'image/jpeg'
                 else: ctype = 'application/octet-stream'
                 self._set_headers(200, ctype)
                 with open(dist_path, 'rb') as f: self.wfile.write(f.read())
                 return

            # 如果 React 裡沒有，則退回原版系統
            if requested_path == 'index.html': requested_path = 'admin.html'

            if os.path.exists(requested_path) and os.path.isfile(requested_path):
                 ctype = 'text/html' if requested_path.endswith('.html') else 'application/javascript' if requested_path.endswith('.js') else 'text/css'
                 self._set_headers(200, ctype)
                 with open(requested_path, 'rb') as f: self.wfile.write(f.read())
            else:
                 self._set_headers(404); self.wfile.write(b'Not Found')

with ReuseAddrTCPServer(("", PORT), CustomHandler) as httpd:
    httpd.serve_forever()
