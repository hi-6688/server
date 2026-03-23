# models.py — 伺服器實例資料模型
import os
import json
import socket
import subprocess
import time
import uuid as uuid_module
import shutil
import re

# 設定常數
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_FILE = os.path.join(BASE_DIR, 'instances.json')
DEFAULT_SERVER_ROOT = '/home/terraria/servers/minecraft'


class Instance:
    """代表一個 Minecraft Bedrock 伺服器實例"""

    def __init__(self, data):
        self.uuid = data.get('uuid')
        self.name = data.get('name')
        self.path = data.get('path')
        self.port = int(data.get('port', 19132))
        self.screen_name = data.get('screen_name')
        self.discord_channel_id = data.get('discord_channel_id', '')
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
        """取得 screen log 路徑"""
        return os.path.join(self.path, 'bedrock_screen.log')

    def is_running(self):
        """判斷遠端伺服器是否運行中：優先查詢 VM2 Agent，超時時以 GCP 來確認 VM2 開機狀態"""
        import proxy_helpers
        # 第一層：GCP 機器是否開啟
        if not proxy_helpers.is_vm2_running():
            return False
        # 第二層：嘗試向 VM2 Agent 查詢 screen 狀態
        try:
            res = proxy_helpers.proxy_to_agent("get_system_status")
            if isinstance(res, dict) and res.get("status") == "success":
                screens = res.get("screens", [])
                return self.screen_name in screens
        except Exception:
            pass
        # Agent 超時或無回應時，VM2 機器確實做開著，僅代表 Agent 未就緒，
        # 退而求其次回傳 True (反映「VM2 開機中」而非絕對離線)
        return True


class InstanceManager:
    """管理所有伺服器實例的新增、刪除、更新"""

    def __init__(self):
        self.instances = {}
        self.load_instances()

    def load_instances(self):
        """從 JSON 載入實例清單"""
        if os.path.exists(INSTANCES_FILE):
            try:
                with open(INSTANCES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for inst_data in data.get('instances', []):
                        instance = Instance(inst_data)
                        self.instances[instance.uuid] = instance
            except Exception as e:
                print("Error loading instances: %s" % e)

        # 確保 'main' 實例始終存在
        if 'main' not in self.instances:
            print("Initializing default 'main' instance...")
            main_instance = Instance({
                'uuid': 'main',
                'name': '主伺服器 (Main)',
                'path': DEFAULT_SERVER_ROOT,
                'port': 19132,
                'screen_name': 'bedrock',
                'discord_channel_id': ''
            })
            self.instances['main'] = main_instance
            self.save_instances()

    def save_instances(self):
        """將實例清單寫入 JSON"""
        data = {'instances': [inst.to_dict() for inst in self.instances.values()]}
        try:
            with open(INSTANCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving instances: %s" % e)

    def get_instance(self, uuid):
        return self.instances.get(uuid)

    def get_all_instances(self):
        return list(self.instances.values())

    def create_instance(self, name, port, discord_channel_id=''):
        """建立新的伺服器實例 (複製預設伺服器)"""
        # 驗證 Port 衝突
        for inst in self.instances.values():
            if int(inst.port) == int(port):
                raise ValueError("Port %s is already in use by %s" % (port, inst.name))

        new_uuid = str(uuid_module.uuid4())
        new_path = "/home/terraria/servers/instances/%s" % new_uuid

        # 1. 複製伺服器檔案
        if not os.path.exists(DEFAULT_SERVER_ROOT):
            raise FileNotFoundError("Default server root not found, cannot clone.")

        print("Cloning server to %s..." % new_path)
        try:
            def ignore_patterns(path, names):
                return ['worlds', 'backups', 'bedrock_screen.log', 'bedrock_input',
                        'server.properties', 'server.properties.bak',
                        'white-list.txt', 'whitelist.json', 'permissions.json']

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.copytree(DEFAULT_SERVER_ROOT, new_path, ignore=ignore_patterns, dirs_exist_ok=True)
            os.makedirs(os.path.join(new_path, 'worlds'), exist_ok=True)
        except Exception as e:
            if os.path.exists(new_path):
                shutil.rmtree(new_path)
            raise e

        # 2. 設定 server.properties
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
                new_content += "server-port=%s\n" % port
                found_port = True
            elif line.strip().startswith('server-portv6='):
                new_content += "server-portv6=%s\n" % (int(port) + 1)
                found_portv6 = True
            elif line.strip().startswith('server-name='):
                new_content += "server-name=%s\n" % name
                found_name = True
            elif line.strip().startswith('level-name='):
                new_content += "level-name=%s\n" % name
                found_level = True
            else:
                new_content += line + "\n"

        if not found_port:
            new_content += "server-port=%s\n" % port
        if not found_portv6:
            new_content += "server-portv6=%s\n" % (int(port) + 1)
        if not found_name:
            new_content += "server-name=%s\n" % name
        if not found_level:
            new_content += "level-name=%s\n" % name

        with open(props_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # 2.5 自動為新世界啟用 ChatLogger
        level_name = name
        for line in new_content.splitlines():
            if line.strip().startswith('level-name='):
                level_name = line.strip().split('=', 1)[1]
                break
        world_dir = os.path.join(new_path, 'worlds', level_name)
        os.makedirs(world_dir, exist_ok=True)
        chatlogger_manifest = [{"pack_id": "e4b3e6d2-1234-4567-8901-abcdef123456", "version": [1, 0, 0]}]
        with open(os.path.join(world_dir, 'world_behavior_packs.json'), 'w') as f:
            json.dump(chatlogger_manifest, f, indent=2)
        print("ChatLogger auto-enabled for world '%s'" % level_name)

        # 2.6 複製 Script API 模組權限
        src_perms = os.path.join(DEFAULT_SERVER_ROOT, 'config', 'default', 'permissions.json')
        if os.path.exists(src_perms):
            dst_perms_dir = os.path.join(new_path, 'config', 'default')
            os.makedirs(dst_perms_dir, exist_ok=True)
            shutil.copy2(src_perms, os.path.join(dst_perms_dir, 'permissions.json'))
            print("Script API permissions copied for instance '%s'" % name)

        # 3. 建立 Instance 物件
        new_instance = Instance({
            'uuid': new_uuid,
            'name': name,
            'path': new_path,
            'port': int(port),
            'screen_name': "bedrock_%s" % port,
            'discord_channel_id': discord_channel_id
        })

        self.instances[new_uuid] = new_instance
        self.save_instances()
        return new_instance

    def delete_instance(self, uuid):
        """刪除伺服器實例"""
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
        """更新伺服器實例設定"""
        inst = self.get_instance(uuid)
        if not inst:
            raise ValueError("Instance not found")

        if name:
            inst.name = name
        if discord_channel_id is not None:
            inst.discord_channel_id = discord_channel_id

        if port and int(port) != inst.port:
            # 檢查 port 衝突
            for other in self.instances.values():
                if other.uuid != uuid and int(other.port) == int(port):
                    raise ValueError("Port %s is already in use by %s" % (port, other.name))
            inst.port = int(port)
            inst.screen_name = "bedrock_%s" % port if uuid != 'main' else inst.screen_name
            # 同步更新 server.properties
            props_path = os.path.join(inst.path, 'server.properties')
            if os.path.exists(props_path):
                with open(props_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = ''
                for line in content.splitlines():
                    if line.strip().startswith('server-port='):
                        new_content += "server-port=%s\n" % port
                    elif line.strip().startswith('server-portv6='):
                        new_content += "server-portv6=%s\n" % (int(port) + 1)
                    elif line.strip().startswith('server-name=') and name:
                        new_content += "server-name=%s\n" % name
                    else:
                        new_content += line + '\n'
                with open(props_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

        self.save_instances()
        return inst
