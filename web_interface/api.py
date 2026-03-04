# api.py — 伺服器控制面板 API 入口 (路由分發器)
# 原始版本備份於 api.py.bak

import http.server
import socketserver
import urllib.parse
import os
import json
import sys
import threading
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import proxy_helpers
from models import InstanceManager

# 路由處理模組
from routes import auth, server, instances, files, worlds, addons

# 設定常數
PORT = 24445
API_KEY = "AdminKey123456"

# 初始化實例管理器
instance_manager = InstanceManager()


class ReuseAddrTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    """路由分發處理器 — 根據路徑分派給對應的路由模組"""

    def _set_headers(self, code=200, content_type='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))

        # 跳過 multipart 檔案上傳路由的 body 預讀
        skip_body_paths = ['/upload', '/addon/upload']
        params = {}
        if parsed.path not in skip_body_paths:
            if content_length > 0:
                try:
                    params = json.loads(self.rfile.read(content_length).decode('utf-8'))
                except:
                    params = {}

        # 驗證 (登入路由除外)
        if parsed.path != '/login':
            key_in_query = urllib.parse.parse_qs(parsed.query).get('key', [''])[0]
            if params.get('key') != API_KEY and key_in_query != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

        # 實例上下文
        instance_id = params.get('instance_id')
        if not instance_id:
            instance_id = urllib.parse.parse_qs(parsed.query).get('instance_id', ['main'])[0]
        current_instance = instance_manager.get_instance(instance_id)

        # 不需要實例的路由
        no_instance_routes = ['/instances/create', '/login', '/save_config']
        if not current_instance and parsed.path not in no_instance_routes:
            self._set_headers(404)
            self.wfile.write(b'{"error":"Instance not found"}')
            return

        # === 路由分發 ===

        # Webhook (VM2 自動關機觸發)
        if parsed.path == '/webhook/shutdown_vm2':
            if params.get('key') != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            self._set_headers()
            self.wfile.write(b'{"status":"shutting_down"}')

            def do_shutdown():
                # 在斷電前先備份所有設定檔到 VM1 離線快取
                try:
                    proxy_helpers.backup_all_instances_to_cache()
                except Exception as e:
                    print(f"[Webhook] Backup before shutdown failed: {e}")

                # 加入 discord_bot 目錄以存取 GCPManager
                sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../discord_bot'))
                try:
                    from utils.gcp_manager import GCPManager
                    # 與 minecraft.py 一致的設定
                    gcp = GCPManager(project_id="project-ad2eecb1-dd0f-4cf4-b1a", zone="asia-east1-c")
                    success = gcp.stop_instance("instance-20260220-174959")

                    # 發送 Discord 通知
                    if success:
                        from dotenv import load_dotenv
                        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env'))
                        token = os.getenv('CONCH_TOKEN') 
                        channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
                        
                        if token and channel_id:
                            headers = {
                                "Authorization": f"Bot {token}",
                                "Content-Type": "application/json"
                            }
                            data = {"content": "💤 **自動關機系統**：偵測到 VM2 遊戲伺服器閒置達 10 分鐘，已完成安全存檔並切斷主機電源。 (Event-Driven Timeout)"}
                            requests.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", headers=headers, json=data)
                except Exception as e:
                    print(f"[Webhook Error] {e}")

            threading.Thread(target=do_shutdown, daemon=True).start()
            return

        # 登入
        elif parsed.path == '/login':
            auth.handle_login(self, params, current_instance)

        # 伺服器操作
        elif parsed.path == '/start':
            server.handle_start_post(self, params, current_instance)
        elif parsed.path == '/stop':
            server.handle_stop_post(self, params, current_instance)
        elif parsed.path == '/command':
            server.handle_command(self, params, current_instance)
        elif parsed.path == '/exec':
            server.handle_exec(self, params, current_instance)

        # 實例管理
        elif parsed.path == '/instances/create':
            instances.handle_create(self, params, instance_manager)
        elif parsed.path == '/instances/delete':
            instances.handle_delete(self, params, instance_manager)
        elif parsed.path == '/instances/update':
            instances.handle_update(self, params, instance_manager)

        # 檔案讀寫
        elif parsed.path == '/write':
            files.handle_write(self, params, current_instance)

        # 世界管理
        elif parsed.path == '/switch_world':
            worlds.handle_switch_world(self, params, current_instance)
        elif parsed.path == '/delete_world':
            worlds.handle_delete_world(self, params, current_instance)
        elif parsed.path == '/reset_world':
            worlds.handle_reset_world(self, params, current_instance)
        elif parsed.path == '/update':
            worlds.handle_update_server(self, params, current_instance, parsed.query)
        elif parsed.path == '/upload':
            worlds.handle_upload(self, params, current_instance, self.headers, self.rfile)
        elif parsed.path == '/addon/upload':
            addons.handle_upload_addon(self, params, current_instance, self.headers, self.rfile, parsed.query)
        elif parsed.path == '/addon/delete':
            addons.handle_delete_addon(self, params, current_instance)

        # 設定儲存 (空操作)
        elif parsed.path == '/save_config':
            self._set_headers()
            self.wfile.write(b'{"status":"saved"}')

        else:
            self._set_headers(404)
            self.wfile.write(b'{"error":"Not Found"}')

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        get_param = lambda k: params.get(k, [''])[0]

        # 驗證 (只對 API 路由)
        api_endpoints = ['/instances/list', '/server_status', '/stats', '/read',
                         '/worlds', '/addons', '/version', '/start', '/stop', '/download']
        if parsed.path in api_endpoints and get_param('key') != API_KEY:
            self._set_headers(403)
            self.wfile.write(b'{"error":"Forbidden"}')
            return

        # 實例上下文
        instance_id = get_param('instance_id') or 'main'
        current_instance = instance_manager.get_instance(instance_id)

        if not current_instance and parsed.path != '/instances/list':
            self._set_headers(404)
            self.wfile.write(b'{"error":"Instance not found"}')
            return

        # 組裝 params dict (讓路由 handler 使用統一介面)
        p = {k: v[0] for k, v in params.items()}

        # === 路由分發 ===

        if parsed.path == '/instances/list':
            instances.handle_list(self, p, instance_manager)
        elif parsed.path == '/server_status':
            server.handle_server_status(self, p, current_instance)
        elif parsed.path == '/stats':
            server.handle_stats(self, p, current_instance)
        elif parsed.path == '/version':
            server.handle_version(self, p, current_instance)
        elif parsed.path == '/start':
            server.handle_start_get(self, p, current_instance)
        elif parsed.path == '/stop':
            server.handle_stop_get(self, p, current_instance)
        elif parsed.path == '/read':
            files.handle_read(self, p, current_instance)
        elif parsed.path == '/worlds':
            worlds.handle_list_worlds(self, p, current_instance)
        elif parsed.path == '/addons':
            addons.handle_list_addons(self, p, current_instance)
        elif parsed.path == '/download':
            worlds.handle_download(self, p, current_instance)
        elif parsed.path == '/public_config':
            config = {
                'server_title': current_instance.name,
                'port': current_instance.port,
                'ip': '39.12.35.16'
            }
            instances_public = []
            for inst in instance_manager.get_all_instances():
                instances_public.append({'name': inst.name, 'port': inst.port, 'uuid': inst.uuid})
            config['instances'] = instances_public
            self._set_headers()
            self.wfile.write(json.dumps(config).encode('utf-8'))
        else:
            # 靜態檔案伺服器 (使用絕對路徑)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            dist_dir = os.path.join(base_dir, 'frontend', 'dist')

            requested_path = parsed.path.lstrip('/')

            # /admin.html → 重導向到新版首頁
            if requested_path == 'admin.html':
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return

            if not requested_path:
                requested_path = 'index.html'

            # 優先讀取 React build 目錄
            dist_path = os.path.join(dist_dir, requested_path)
            if os.path.exists(dist_path) and os.path.isfile(dist_path):
                ctype = 'application/octet-stream'
                if requested_path.endswith('.html'):
                    ctype = 'text/html'
                elif requested_path.endswith('.js'):
                    ctype = 'application/javascript'
                elif requested_path.endswith('.css'):
                    ctype = 'text/css'
                elif requested_path.endswith('.svg'):
                    ctype = 'image/svg+xml'
                elif requested_path.endswith('.png'):
                    ctype = 'image/png'
                elif requested_path.endswith('.jpg') or requested_path.endswith('.jpeg'):
                    ctype = 'image/jpeg'
                self._set_headers(200, ctype)
                with open(dist_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

            # SPA Fallback: 未知路徑一律回傳 index.html (React 前端處理路由)
            index_path = os.path.join(dist_dir, 'index.html')
            if os.path.exists(index_path):
                self._set_headers(200, 'text/html')
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(b'Not Found')


with ReuseAddrTCPServer(("", PORT), CustomHandler) as httpd:
    print("Server running on port %s" % PORT)
    httpd.serve_forever()
