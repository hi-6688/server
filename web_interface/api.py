
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

PORT = 24445
API_KEY = "AdminKey123456"
LOGIN_PASSWORD = "hmpb" # User provided password

def is_server_running(port=19132):
    """Check if the server is running (Port check + Screen check)"""
    # 1. Check UDP port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        sock.close()
    except OSError:
        return True

    # 2. Check Screen Session (Prevents race condition during startup)
    try:
        result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if '.bedrock' in result.stdout:
             return True
    except:
        pass

    return False

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/read':
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return
                
            # Allow reading specific config files only for safety
            target = params.get('file', [''])[0]
            # Normalize path to prevent arbitrary reads (simple check)
            if '..' in target or not target.startswith('server.') and not target.endswith('.json'):
                 # For now, let's allow explicit known files
                 known_files = ['server.properties', 'permissions.json', 'allowlist.json', 'bedrock_screen.log']
                 if target not in known_files:
                    self._set_headers(400)
                    self.wfile.write(b'{"error":"Invalid file"}')
                    return

            filepath = os.path.join('/home/terraria/servers/minecraft', target)
            
            try:
                # Check if specific lines requested (tail)
                line_count = params.get('lines', [None])[0]
                
                if line_count and line_count.isdigit():
                    # Use tail command for efficiency on large files
                    cmd = ['tail', '-n', line_count, filepath]
                    content = subprocess.check_output(cmd).decode('utf-8', errors='replace')
                else:
                    # Full read
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        
                self._set_headers()
                self.wfile.write(json.dumps({"content": content}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        elif parsed.path == '/version':
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                # Run the server binary briefly to get the version
                # It usually prints "Version: X.Y.Z" in the first few lines
                cmd = "cd /home/terraria/servers/minecraft && LD_LIBRARY_PATH=. ./bedrock_server"
                process = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                version = "Unknown"
                try:
                    # Read line by line for a short duration
                    for _ in range(20): # Read first 20 lines max
                        line = process.stdout.readline()
                        if not line: break
                        if "Version:" in line:
                            # Format: [INFO] Version: 1.21.132.3
                            parts = line.split("Version:")
                            if len(parts) > 1:
                                version = parts[1].strip()
                                break
                except Exception:
                    pass
                
                process.terminate()
                try:
                    process.wait(timeout=1)
                except:
                    process.kill()

                self._set_headers()
                self.wfile.write(json.dumps({"version": version}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        elif parsed.path == '/size':
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                # 1. Get Folder Size
                result = subprocess.check_output(['du', '-sh', '/home/terraria/servers/minecraft/worlds']).decode('utf-8')
                size = result.split()[0]
                
                # 2. Get Active Level Name
                level_name = "Bedrock level"
                display_name = "Unknown"
                
                props_path = '/home/terraria/servers/minecraft/server.properties'
                if os.path.exists(props_path):
                    with open(props_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith('level-name='):
                                level_name = line.split('=')[1].strip()
                                break
                
                # 3. Get Level Display Name (from levelname.txt)
                level_txt_path = os.path.join('/home/terraria/servers/minecraft/worlds', level_name, 'levelname.txt')
                if os.path.exists(level_txt_path):
                    with open(level_txt_path, 'r') as f:
                        display_name = f.read().strip()
                else:
                    display_name = level_name
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    "size": size,
                    "levelName": level_name,
                    "displayName": display_name
                }).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/upload':
            # World/Full Backup Upload Endpoint
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                import tempfile
                import zipfile
                
                data_len = int(self.headers.get('Content-Length', 0))
                if data_len > 1024 * 1024 * 500: # 500MB Limit
                    # Warning but proceed? Or just handle chunks? 
                    # Python http.server reads all in memory... dangerous for large files.
                    # But for now we assume it fits in RAM (standard usage).
                    pass

                file_data = self.rfile.read(data_len)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
                
                # Analyze Zip
                server_root = '/home/terraria/servers/minecraft'
                is_full_backup = False
                
                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    top_levels = {item.split('/')[0] for item in zf.namelist()}
                    # Heuristic for Full Backup: contains 'worlds' folder AND 'server.properties' or 'behavior_packs'
                    if 'worlds' in top_levels and ('server.properties' in top_levels or 'behavior_packs' in top_levels):
                        is_full_backup = True
                    
                    if is_full_backup:
                        # Full Restore
                        # Extract everything to server_root
                        # Overwrite existing
                        zf.extractall(server_root)
                        msg = "Full server backup restored successfully."
                    else:
                        # Single World Upload
                        # Extract to worlds/UploadedWorld_{Timestamp}
                        extract_target = os.path.join(server_root, 'worlds')
                        
                        # Check if zip contains a single top-level folder
                        # e.g. "MyWorld/level.dat"
                        # If so, extract as is.
                        # If "level.dat" is at root, extract to new folder.
                        
                        file_list = zf.namelist()
                        has_root_level_dat = 'level.dat' in file_list
                        
                        if has_root_level_dat:
                            # Extract to specific folder
                            timestamp = int(time.time())
                            new_folder = os.path.join(extract_target, f'UploadedWorld_{timestamp}')
                            os.makedirs(new_folder, exist_ok=True)
                            zf.extractall(new_folder)
                            msg = f"World uploaded to: UploadedWorld_{timestamp}"
                        else:
                            # Extract as is
                            zf.extractall(extract_target)
                            msg = "World folder extracted to worlds directory."

                os.remove(tmp_path)
                self._set_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": msg}).encode('utf-8'))
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/download':
            # 下載世界檔案 API 端點
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                import zipfile
                import io
                import time
                
                server_root = '/home/terraria/servers/minecraft'
                targets = ['worlds', 'behavior_packs', 'resource_packs', 'server.properties', 'permissions.json', 'allowlist.json']
                
                # 建立 zip 檔案到記憶體
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for target in targets:
                        path = os.path.join(server_root, target)
                        if not os.path.exists(path):
                            continue
                            
                        if os.path.isfile(path):
                            # Add file
                            arc_name = os.path.relpath(path, server_root)
                            zf.write(path, arc_name)
                        else:
                            # Add directory contents
                            for root, dirs, files in os.walk(path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arc_name = os.path.relpath(file_path, server_root)
                                    zf.write(file_path, arc_name)
                
                zip_buffer.seek(0)
                zip_data = zip_buffer.read()
                
                # 設定下載標頭
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                filename = f'world_backup_{timestamp}.zip'
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Content-Length', str(len(zip_data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(zip_data)
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif parsed.path == '/update':
            # Update Server Endpoint
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            url = params.get('url', [''])[0]
            if not url:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing URL parameter"}')
                return

            try:
                # 1. Stop Server
                # Send Quit Command
                subprocess.run(['screen', '-S', 'bedrock', '-X', 'quit'], stderr=subprocess.DEVNULL)
                time.sleep(3) # Wait for shutdown
                
                # Double check kill
                subprocess.run("pkill -f bedrock_server", shell=True)

                server_root = '/home/terraria/servers/minecraft'
                backup_files = ['server.properties', 'permissions.json', 'allowlist.json', 'whitelist.json']
                temp_backup_dir = '/tmp/mc_update_backup'
                
                if os.path.exists(temp_backup_dir):
                    shutil.rmtree(temp_backup_dir)
                os.makedirs(temp_backup_dir)

                # 2. Backup Configs
                for file in backup_files:
                    src = os.path.join(server_root, file)
                    if os.path.exists(src):
                        shutil.copy2(src, temp_backup_dir)
                
                # 3. Download
                zip_path = os.path.join(server_root, 'update.zip')
                subprocess.run(['wget', '-O', zip_path, url], check=True, cwd=server_root)
                
                # 4. Extract (Overwrite binaries)
                # -o: overwrite without prompting
                subprocess.run(['unzip', '-o', zip_path], check=True, cwd=server_root)
                
                # 5. Restore Configs
                for file in backup_files:
                    backup = os.path.join(temp_backup_dir, file)
                    dest = os.path.join(server_root, file)
                    if os.path.exists(backup):
                         shutil.copy2(backup, dest)
                
                # Cleanup
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                shutil.rmtree(temp_backup_dir)
                
                self._set_headers()
                self.wfile.write(json.dumps({"status": "Update Completed. Please start server."}).encode('utf-8'))
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": f"Update failed: {str(e)}"}).encode('utf-8'))

        elif parsed.path == '/command':
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            cmd = params.get('cmd', [''])[0]
            if not cmd:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing cmd parameter"}')
                return

            # Send command to screen session
            # We use 'stuff' to inject command into the running screen session named 'bedrock'
            try:
                # 1. Send command
                full_cmd = ['screen', '-S', 'bedrock', '-p', '0', '-X', 'stuff', f'{cmd}\n']
                subprocess.run(full_cmd, check=True)
                
                # 2. If command is 'list' or 'gamerule', read the log file
                if cmd.strip() == 'list' or cmd.strip() == 'gamerule':
                   import time
                   time.sleep(1.0) # Wait for output to be logged (Increased to 1.0s)
                   try:
                       # Read last 20 lines of log
                       log_cmd = ['tail', '-n', '20', '/home/terraria/servers/minecraft/bedrock_screen.log']
                       result = subprocess.run(log_cmd, capture_output=True, text=True)
                       output = result.stdout
                       
                       # We need to return this output in a format admin.js expects
                       # admin.js expects {"result": "..."}
                       self._set_headers()
                       self.wfile.write(json.dumps({"result": output}).encode('utf-8'))
                       return
                   except Exception as e:
                       pass

                self._set_headers()
                self.wfile.write(json.dumps({"result": "Command sent"}).encode('utf-8'))
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": "Failed to send command: " + str(e)}).encode('utf-8'))

        elif parsed.path == '/exec':
            # 執行 Shell 指令的端點
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            cmd = params.get('cmd', [''])[0]
            if not cmd:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing cmd parameter"}')
                return

            # 安全檢查：只允許特定指令
            # Update to support screen commands with logging
            allowed_commands = [
                'systemctl start bedrock', # Keep legacy
                'screen -dmS bedrock -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"', # New Start with logging
                'screen -S bedrock -X quit', # New Stop
                'rm -rf /home/terraria/servers/minecraft/worlds',
                'ls -la /home/terraria/servers/minecraft/worlds',
                'du -sh /home/terraria/servers/minecraft/worlds',
                'zip -r /home/terraria/servers/web_interface/world-backup.zip /home/terraria/servers/minecraft/worlds',
                'tail -n 20 /home/terraria/servers/minecraft/bedrock_screen.log' # Allow reading log
            ]
            
            # 檢查是否為允許的指令
            is_allowed = any(cmd.startswith(allowed) for allowed in allowed_commands)
            if not is_allowed:
                self.wfile.write(json.dumps({"error": "Command not allowed", "allowed": allowed_commands}).encode('utf-8'))
                return

            # [SAFETY LOCK] Check if server is already running before starting new instance
            if 'bedrock_server' in cmd and 'screen -dmS' in cmd:
                if is_server_running():
                     self._set_headers(409) # Conflict
                     self.wfile.write(json.dumps({"error": "Safety Lock: Server is ALREADY running on port 19132. Please stop it first."}).encode('utf-8'))
                     return

            try:
                # Set CWD to server root so ./bedrock_server works
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30, cwd='/home/terraria/servers/minecraft')
                output = result.stdout.decode('utf-8') + result.stderr.decode('utf-8')
                self._set_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "returncode": result.returncode,
                    "output": output
                }).encode('utf-8'))
            except subprocess.TimeoutExpired:
                self._set_headers(500)
                self.wfile.write(b'{"error":"Command timeout"}')
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


        elif parsed.path == '/addons':
            # 列出已安裝的模組
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                addons = []
                server_root = '/home/terraria/servers/minecraft'
                
                # 掃描行為包和資源包目錄
                addon_dirs = [
                    ('behavior_packs', '行為包'),
                    ('resource_packs', '資源包'),
                ]
                
                for dir_name, type_label in addon_dirs:
                    dir_path = os.path.join(server_root, dir_name)
                    if not os.path.exists(dir_path):
                        continue
                        
                    for item in os.listdir(dir_path):
                        # 過濾掉系統內建模組，只顯示用戶安裝的模組
                        system_packs = ['vanilla', 'chemistry', 'editor', 'experimental_', 'server_ui_library', 'server_library', 'server_editor_library']
                        if any(item.startswith(prefix) or item == prefix for prefix in system_packs):
                            continue
                        
                        item_path = os.path.join(dir_path, item)
                        if not os.path.isdir(item_path):
                            continue
                            
                        manifest_path = os.path.join(item_path, 'manifest.json')
                        if not os.path.exists(manifest_path):
                            continue
                            
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                            
                            header = manifest.get('header', {})
                            addon_info = {
                                'uuid': header.get('uuid', item),
                                'name': header.get('name', item),
                                'description': header.get('description', ''),
                                'version': header.get('version', [0, 0, 0]),
                                'type': type_label,
                                'folder': item,
                                'dir': dir_name
                            }
                            addons.append(addon_info)
                        except Exception:
                            # 如果無法讀取 manifest，仍然列出資料夾
                            addons.append({
                                'uuid': item,
                                'name': item,
                                'description': '(無法讀取 manifest.json)',
                                'version': [0, 0, 0],
                                'type': type_label,
                                'folder': item,
                                'dir': dir_name
                            })
                
                self._set_headers()
                self.wfile.write(json.dumps({'addons': addons}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        elif parsed.path == '/worlds':
            # 列出所有可用世界
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                worlds_dir = '/home/terraria/servers/minecraft/worlds'
                worlds = []
                
                # 讀取目前使用的世界
                current_world = ""
                props_path = '/home/terraria/servers/minecraft/server.properties'
                if os.path.exists(props_path):
                    with open(props_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith('level-name='):
                                current_world = line.split('=')[1].strip()
                                break
                
                # 列出所有世界資料夾
                for folder in os.listdir(worlds_dir):
                    folder_path = os.path.join(worlds_dir, folder)
                    if os.path.isdir(folder_path):
                        # 檢查是否為有效世界 (有 level.dat)
                        level_dat = os.path.join(folder_path, 'level.dat')
                        if os.path.exists(level_dat):
                            # 取得世界大小
                            try:
                                result = subprocess.check_output(['du', '-sh', folder_path]).decode('utf-8')
                                size = result.split()[0]
                            except:
                                size = "?"
                            
                            # 取得顯示名稱 (從 level.dat 內部讀取)
                            # 如果讀取失敗，預設顯示資料夾名稱
                            internal_name = self._read_level_name(level_dat)
                            display_name = internal_name if internal_name else folder
                            
                            worlds.append({
                                'folder': folder,
                                'displayName': display_name,
                                'size': size,
                                'isActive': (folder == current_world)
                            })
                
                self._set_headers()
                self.wfile.write(json.dumps({'worlds': worlds, 'current': current_world}).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        elif parsed.path == '/switch_world':
            # 切換世界
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            world_name = params.get('world', [''])[0]
            if not world_name:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing world parameter"}')
                return

            try:
                # 驗證世界存在
                world_path = os.path.join('/home/terraria/servers/minecraft/worlds', world_name)
                if not os.path.exists(world_path):
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"World not found"}')
                    return

                # 更新 server.properties
                props_path = '/home/terraria/servers/minecraft/server.properties'
                with open(props_path, 'r') as f:
                    lines = f.readlines()
                
                with open(props_path, 'w') as f:
                    for line in lines:
                        if line.strip().startswith('level-name='):
                            f.write(f'level-name={world_name}\n')
                        else:
                            f.write(line)
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'message': f'已切換到世界: {world_name}。請重新啟動伺服器以套用變更。'
                }).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))



        elif parsed.path == '/server_status':
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return
            
            running = is_server_running()
            running = is_server_running()
            self._set_headers()
            self.wfile.write(json.dumps({"running": running}).encode('utf-8'))
            return

        elif parsed.path == '/stats':
            # System Statistics Endpoint
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                stats = {}
                
                # 1. Memory (free -h equivalent logic)
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            meminfo[parts[0].strip()] = int(parts[1].strip().split()[0]) # kB
                    
                    total = meminfo.get('MemTotal', 1)
                    available = meminfo.get('MemAvailable', 0)
                    used = total - available
                    stats['memory'] = {
                        'total': f"{total / 1024 / 1024:.1f} GB",
                        'used': f"{used / 1024 / 1024:.1f} GB",
                        'percent': int((used / total) * 100)
                    }

                # 2. CPU (Load Average)
                with open('/proc/loadavg', 'r') as f:
                    load = f.read().split()
                    stats['cpu'] = {
                        'load_1': float(load[0]),
                        'load_5': float(load[1]),
                        'load_15': float(load[2])
                    }

                # 3. Disk (Root /, df -h)
                statvfs = os.statvfs('/')
                total_disk = statvfs.f_frsize * statvfs.f_blocks
                free_disk = statvfs.f_frsize * statvfs.f_bavail
                used_disk = total_disk - free_disk
                stats['disk'] = {
                     'total': f"{total_disk / 1024 / 1024 / 1024:.1f} GB",
                     'used': f"{used_disk / 1024 / 1024 / 1024:.1f} GB",
                     'percent': int((used_disk / total_disk) * 100)
                }

                # 4. Network (ens4)
                # Parse /proc/net/dev
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                    rx_bytes = 0
                    tx_bytes = 0
                    for line in lines:
                        if 'ens4' in line:
                            parts = line.split(':')[1].split()
                            rx_bytes = int(parts[0]) # 1st column
                            tx_bytes = int(parts[8]) # 9th column
                            break
                    
                    stats['network'] = {
                        'rx_gb': f"{rx_bytes / 1024 / 1024 / 1024:.2f} GB",
                        'tx_gb': f"{tx_bytes / 1024 / 1024 / 1024:.2f} GB"
                    }

                self._set_headers()
                self.wfile.write(json.dumps(stats).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        elif parsed.path == '/public_config':
            # Public Config Endpoint (GET)
            # 無需驗證，供 join.html 使用
            try:
                config_path = '/home/terraria/servers/web_interface/web_config.json'
                conf_data = {}
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        conf_data = json.load(f)
                
                # Automatically fetch port from server.properties
                server_port = 19132
                try:
                    with open('/home/terraria/servers/minecraft/server.properties', 'r') as f:
                        for line in f:
                            if line.strip().startswith('server-port='):
                                server_port = int(line.split('=')[1].strip())
                                break
                except:
                    pass
                
                conf_data['port'] = server_port
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store') # Disable caching
                self.end_headers()
                self.wfile.write(json.dumps(conf_data).encode('utf-8'))
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        else:
            # Static File Serving
            # Security: Do not allow path traversal
            if '..' in parsed.path:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            # Default to index.html/admin.html if root
            path = parsed.path
            if path == '/':
                path = '/admin.html'

            # Remove leading slash to make it relative to CWD
            if path.startswith('/'):
                path = path[1:]

            # Serve file if exists
            if os.path.exists(path) and os.path.isfile(path):
                content_type = 'text/plain'
                if path.endswith('.html'): content_type = 'text/html'
                elif path.endswith('.js'): content_type = 'application/javascript'
                elif path.endswith('.css'): content_type = 'text/css'
                elif path.endswith('.json'): content_type = 'application/json'
                elif path.endswith('.png'): content_type = 'image/png'
                elif path.endswith('.ico'): content_type = 'image/x-icon'

                try:
                    with open(path, 'rb') as f:
                        content = f.read()
                        self.send_response(200)
                        self.send_header('Content-type', content_type)
                        self.end_headers()
                        self.wfile.write(content)
                except Exception as e:
                    self._set_headers(500)
                    self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            else:
                self._set_headers(404)
                self.wfile.write(b'{"error":"Not Found"}')

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Login Endpoint (無需 API Key)
        if parsed.path == '/login':
            if self.headers.get('Content-Type') != 'application/json':
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid Content-Type"}')
                return

            length = int(self.headers.get('Content-Length', 0))
            try:
                body = json.loads(self.rfile.read(length))
                password = body.get('password', '')
                
                if password == LOGIN_PASSWORD:
                    self._set_headers()
                    self.wfile.write(b'{"status":"ok", "key":"' + API_KEY.encode('utf-8') + b'"}')
                else:
                    self._set_headers(401)
                    self.wfile.write(b'{"error":"Invalid password"}')
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        if parsed.path == '/upload':
            # World/Full Backup Upload Endpoint (POST)
            # 支援「覆蓋前自動備份」功能
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            try:
                import tempfile
                import zipfile
                import datetime
                
                data_len = int(self.headers.get('Content-Length', 0))
                if data_len > 1024 * 1024 * 500: # 500MB Limit
                    pass

                file_data = self.rfile.read(data_len)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
                
                # Analyze Zip
                server_root = '/home/terraria/servers/minecraft'
                worlds_dir = os.path.join(server_root, 'worlds')
                is_full_backup = False
                backup_msg = ""
                
                # 取得使用者自訂的資料夾名稱
                custom_folder_name = params.get('folder_name', [''])[0].strip()
                if custom_folder_name:
                    # 放寬限制：允許中文，只過濾危險字元 (路徑遍歷/控制字元)
                    forbidden = {'/', '\\', '\0', '..', '.'}
                    if any(x in custom_folder_name for x in forbidden) or custom_folder_name in forbidden:
                        # 簡單清理：移除斜線
                        custom_folder_name = custom_folder_name.replace('/', '').replace('\\', '')
                    
                    if not custom_folder_name:
                        custom_folder_name = None

                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    file_list = zf.namelist()
                    top_levels = {item.split('/')[0] for item in file_list if item}
                    
                    # 判斷是否為完整備份
                    if 'worlds' in top_levels and ('server.properties' in top_levels or 'behavior_packs' in top_levels):
                        is_full_backup = True
                    
                    if is_full_backup:
                        # 完整還原 (覆蓋所有)
                        zf.extractall(server_root)
                        msg = "Full server backup restored successfully."
                    else:
                        # 單一世界上傳
                        has_root_level_dat = 'level.dat' in file_list
                        target_folder_name = None
                        
                        if custom_folder_name:
                            target_folder_name = custom_folder_name
                        elif has_root_level_dat:
                            timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            target_folder_name = f'UploadedWorld_{timestamp_str}'
                        else:
                            for item in file_list:
                                if item.endswith('level.dat') and '/' in item:
                                    target_folder_name = item.split('/')[0]
                                    break
                            if not target_folder_name:
                                timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                                target_folder_name = f'UploadedWorld_{timestamp_str}'

                        existing_path = os.path.join(worlds_dir, target_folder_name)
                        
                        if os.path.exists(existing_path):
                            timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_name = f'{target_folder_name}_backup_{timestamp_str}'
                            backup_path = os.path.join(worlds_dir, backup_name)
                            shutil.move(existing_path, backup_path)
                            backup_msg = f" (舊世界已備份為: {backup_name})"
                        
                        final_path = os.path.join(worlds_dir, target_folder_name)
                        os.makedirs(final_path, exist_ok=True)

                        if has_root_level_dat:
                            zf.extractall(final_path)
                        else:
                            # 處理含資料夾的 Zip
                            zip_root_folder = None
                            for item in file_list:
                                if '/' in item:
                                    zip_root_folder = item.split('/')[0]
                                    break
                            
                            # 原地改名邏輯
                            zf.extractall(worlds_dir)
                            extracted_path = os.path.join(worlds_dir, zip_root_folder) if zip_root_folder else None
                            
                            if extracted_path and extracted_path != final_path:
                                if os.path.exists(final_path):
                                     shutil.rmtree(final_path) 
                                os.rename(extracted_path, final_path)

                        msg = f"World uploaded to '{target_folder_name}' successfully.{backup_msg}"

                os.remove(tmp_path)
                self._set_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": msg}).encode('utf-8'))
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        if parsed.path == '/write':
            # Save File Endpoint (POST)
            if self.headers.get('Content-Type') != 'application/json':
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid Content-Type"}')
                return

            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            
            try:
                data = json.loads(post_body)
                if data.get('key') != API_KEY:
                    self._set_headers(403)
                    self.wfile.write(b'{"error":"Forbidden"}')
                    return
                
                filename = data.get('file')
                content = data.get('content')
                
                # Security Check: Allow only specific config files
                allowed_files = ['server.properties', 'whitelist.json', 'permissions.json']
                if filename not in allowed_files:
                     self._set_headers(403)
                     self.wfile.write(b'{"error":"File not allowed"}')
                     return
                
                file_path = os.path.join('/home/terraria/servers/minecraft', filename)
                
                # Backup before save (Optional, simple version)
                # shutil.copy(file_path, file_path + ".bak")

                with open(file_path, 'w') as f:
                    f.write(content)
                
                self._set_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/save_config':
            # Save Web Config (POST)
            if self.headers.get('Content-Type') != 'application/json':
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid Content-Type"}')
                return

            try:
                content_len = int(self.headers.get('Content-Length', 0))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)
                
                if data.get('key') != API_KEY:
                    self._set_headers(403)
                    self.wfile.write(b'{"error":"Forbidden"}')
                    return

                new_config = data.get('config', {})
                config_path = '/home/terraria/servers/web_interface/web_config.json'
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(new_config, f, ensure_ascii=False, indent=4)

                self._set_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/delete_world':
            # 刪除世界 (POST)
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            world_name = params.get('world', [''])[0]
            if not world_name:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing world parameter"}')
                return

            try:
                import shutil
                
                # 檢查是否為目前使用的世界 (禁止刪除)
                current_world = ""
                props_path = '/home/terraria/servers/minecraft/server.properties'
                if os.path.exists(props_path):
                    with open(props_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith('level-name='):
                                current_world = line.split('=')[1].strip()
                                break
                
                if world_name == current_world:
                    self._set_headers(400)
                    self.wfile.write(b'{"error":"Cannot delete active world. Switch to another world first."}')
                    return

                # 刪除資料夾
                world_path = os.path.join('/home/terraria/servers/minecraft/worlds', world_name)
                if not os.path.exists(world_path):
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"World not found"}')
                    return
                
                # 安全檢查：確保路徑在 worlds 下
                if os.path.dirname(os.path.abspath(world_path)) != os.path.abspath('/home/terraria/servers/minecraft/worlds'):
                     self._set_headers(403)
                     self.wfile.write(b'{"error":"Invalid path"}')
                     return

                shutil.rmtree(world_path)
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'message': f'已刪除世界: {world_name}'
                }).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/rename_world':
            # 重新命名世界 (修改 level.dat 內部名稱)
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return

            world_folder = params.get('world', [''])[0]
            new_name = params.get('new_name', [''])[0]
            
            if not world_folder or not new_name:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Missing parameters"}')
                return

            try:
                worlds_dir = '/home/terraria/servers/minecraft/worlds'
                world_path = os.path.join(worlds_dir, world_folder)
                level_dat_path = os.path.join(world_path, 'level.dat')

                # 1. 檢查來源存在
                if not os.path.exists(world_path):
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"World folder not found"}')
                    return
                
                if not os.path.exists(level_dat_path):
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"level.dat not found"}')
                    return

                # 2. 修改 level.dat (呼叫外部腳本)
                import subprocess
                script_path = os.path.join(os.path.dirname(__file__), 'nbt_editor.py')
                
                result = subprocess.run(
                    ['python3', script_path, level_dat_path, new_name],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    raise Exception(f"NBT Editor failed: {result.stdout} {result.stderr}")

                # 3. 更新完畢 (無需更新 levelname.txt，因為我們現在直接讀取 level.dat)
                
                # 4. 回傳成功
                self._set_headers()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'message': f'世界內部名稱已更改為: {new_name}'
                }).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

    # 輔助函式：讀取 level.dat 內的世界名稱
    def _read_level_name(self, level_dat_path):
        try:
            with open(level_dat_path, 'rb') as f:
                data = f.read()
            
            # 搜尋 LevelName tag
            # Bedrock NBT format: Tag String (08) + Name Length (09 00) + "LevelName"
            search_pattern = b'\x08\x09\x00LevelName'
            idx = data.find(search_pattern)
            
            if idx == -1:
                return None
            
            # Value Length is at idx + len(pattern)
            val_len_idx = idx + len(search_pattern)
            if val_len_idx + 2 > len(data):
                return None
                
            name_len = struct.unpack('<H', data[val_len_idx:val_len_idx+2])[0]
            name_start = val_len_idx + 2
            
            if name_start + name_len > len(data):
                return None

            decoded_name = data[name_start:name_start+name_len].decode('utf-8', errors='ignore')
            print(f"DEBUG: Read level name for {level_dat_path}: '{decoded_name}'")
            return decoded_name
        except Exception as e:
            print(f"DEBUG: Error reading {level_dat_path}: {e}")
            return None

        if self.path == '/write':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            
            if data.get('key') != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return
                
            target = data.get('file')
            content = data.get('content')
            
            known_files = ['server.properties', 'permissions.json', 'allowlist.json']
            if target not in known_files:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid file target"}')
                return

            filepath = os.path.join('/home/terraria/servers/minecraft', target)
            
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                self._set_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        elif self.path.startswith('/addon/upload'):
            # 上傳模組檔案
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return
            
            try:
                import tempfile
                import zipfile
                import shutil
                
                content_length = int(self.headers.get('Content-Length', 0))
                file_data = self.rfile.read(content_length)
                
                # 儲存到暫存檔
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
                
                # 解壓並分析 manifest.json
                extract_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    zf.extractall(extract_dir)
                
                # 找到 manifest.json
                manifest_path = None
                addon_folder = None
                for root, dirs, files in os.walk(extract_dir):
                    if 'manifest.json' in files:
                        manifest_path = os.path.join(root, 'manifest.json')
                        addon_folder = root
                        break
                
                if not manifest_path:
                    os.unlink(tmp_path)
                    shutil.rmtree(extract_dir)
                    self._set_headers(400)
                    self.wfile.write(b'{"error":"Invalid addon: manifest.json not found"}')
                    return
                
                # 讀取 manifest 判斷類型
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                modules = manifest.get('modules', [])
                addon_type = 'behavior_packs'  # 預設
                for module in modules:
                    if module.get('type') == 'resources':
                        addon_type = 'resource_packs'
                        break
                    elif module.get('type') in ['data', 'script', 'client_data']:
                        addon_type = 'behavior_packs'
                        break
                
                # 複製到正確目錄
                header = manifest.get('header', {})
                folder_name = header.get('uuid', os.path.basename(addon_folder))
                target_dir = os.path.join('/home/terraria/servers/minecraft', addon_type, folder_name)
                
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                shutil.copytree(addon_folder, target_dir)
                
                # 清理暫存
                os.unlink(tmp_path)
                shutil.rmtree(extract_dir)
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'name': header.get('name', folder_name),
                    'type': addon_type,
                    'uuid': folder_name
                }).encode('utf-8'))
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        
        elif self.path.startswith('/addon/delete'):
            # 刪除模組
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            if params.get('key', [''])[0] != API_KEY:
                self._set_headers(403)
                self.wfile.write(b'{"error":"Forbidden"}')
                return
            
            addon_dir = params.get('dir', [''])[0]
            addon_folder = params.get('folder', [''])[0]
            
            if addon_dir not in ['behavior_packs', 'resource_packs']:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid addon directory"}')
                return
            
            if not addon_folder or '..' in addon_folder:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid folder name"}')
                return
            
            try:
                import shutil
                target_path = os.path.join('/home/terraria/servers/minecraft', addon_dir, addon_folder)
                
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                    self._set_headers()
                    self.wfile.write(b'{"status":"ok"}')
                else:
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"Addon not found"}')
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        
        else:
            self._set_headers(404)

# 自定義 TCPServer 類別，設定 SO_REUSEADDR 避免 "Address already in use" 錯誤
class ReuseAddrTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

with ReuseAddrTCPServer(("", PORT), CustomHandler) as httpd:
    httpd.serve_forever()

