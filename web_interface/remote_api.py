import http.server
import socketserver
import json
import subprocess
import os
import urllib.parse
import urllib.request
import threading
import time
import re
import glob

PORT = 9999
API_KEY = "hihi_secret_key_2026"  # Simple security token

# ==========================================
# 智慧型串流全域變數 (Smart Connection)
# ==========================================
STREAM_URL = "http://39.12.35.16:24446/internal_stream?key=AdminKey123456"
is_streaming = False
stream_thread = None
stream_log_process = None

class AgentHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "running", "version": "1.0"}).encode())

    def do_POST(self):
        # Basic Auth
        auth_header = self.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {API_KEY}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        action = data.get('action')
        
        if action == "execute_command":
            screen_name = data.get('screen_name')
            command = data.get('command')
            if not screen_name or not command:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing parameters")
                return

            try:
                # Inject command into screen
                full_cmd = f"{command}\r"
                subprocess.run(
                    ["screen", "-S", screen_name, "-p", "0", "-X", "stuff", full_cmd],
                    check=True
                )
                self._send_json({"status": "success"})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        elif action == "get_system_status":
            try:
                output = subprocess.check_output("screen -ls", shell=True, text=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output = e.output
            active_screens = []
            for line in output.split("\n"):
                if "Detached" in line or "Attached" in line:
                    parts = line.split("\t")
                    if len(parts) > 1:
                        screen_full = parts[1].strip()
                        if "." in screen_full:
                            name = screen_full.split(".", 1)[1]
                            active_screens.append(name.strip())
                        else:
                            active_screens.append(screen_full)
            self._send_json({"status": "success", "screens": active_screens})

        elif action == "get_stats":
            import psutil
            import shutil
            try:
                mem = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=0.5)
                disk = shutil.disk_usage("/")
                net_io = psutil.net_io_counters()

                stats = {
                    "cpu_percent": cpu_percent,
                    "ram_used_mb": mem.used // (1024*1024),
                    "ram_total_mb": mem.total // (1024*1024),
                    "ram_percent": mem.percent,
                    "disk_used_gb": round(disk.used / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    "disk_percent": round((disk.used / disk.total) * 100, 1),
                    "net_rx_mb": round(net_io.bytes_recv / (1024*1024), 2),
                    "net_tx_mb": round(net_io.bytes_sent / (1024*1024), 2)
                }
                self._send_json({"status": "success", "stats": stats})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        elif action == "read_log_tail":
            filepath = data.get('filepath')
            lines = data.get('lines', 50)
            if not filepath or ".." in filepath:
                self.send_response(400)
                self.end_headers()
                return
            try:
                output = subprocess.check_output(["tail", "-n", str(lines), filepath], text=True)
                self._send_json({"status": "success", "content": output})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        elif action == "read_file":
            filepath = data.get('filepath')
            if not filepath or ".." in filepath:
                self.send_response(400)
                self.end_headers()
                return
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                self._send_json({"status": "success", "content": content})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)
                
        elif action == "write_file":
            filepath = data.get('filepath')
            content = data.get('content')
            if not filepath or content is None or ".." in filepath:
                self.send_response(400)
                self.end_headers()
                return
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                self._send_json({"status": "success"})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)
                
        elif action == "start_stream":
            screen_name = data.get('screen_name', 'main')
            filepath = f"/home/terraria/servers/instances/{screen_name}/bedrock_screen.log"
            start_streaming_to_vm1(filepath)
            self._send_json({"status": "success", "message": "Streaming started"})

        elif action == "stop_stream":
            stop_streaming_to_vm1()
            self._send_json({"status": "success", "message": "Streaming stopped"})
                
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Unknown action")

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

# ==========================================
# 智慧型連線背景推播 (Smart Connection Streamer)
# ==========================================

import psutil # Ensure this is available

def stream_worker(filepath):
    global is_streaming, stream_log_process
    print(f"[Streamer] Started pushing logs from {filepath} to VM1")
    
    # 開啟 tail -F 監控特定伺服器的 log
    try:
        stream_log_process = subprocess.Popen(["tail", "-n", "0", "-F", filepath], stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"[Streamer] Failed to start tail: {e}")
        return

    # 定期回報資源使用率的非阻塞檢查時間
    last_status_time = time.time()

    try:
        # non-blocking 讀取，配合頻率控制
        os.set_blocking(stream_log_process.stdout.fileno(), False)
        
        while is_streaming:
            # 1. 發送日誌更新
            log_batch = ""
            for _ in range(50): # 一次最多處理 50 行避免卡住
                line = stream_log_process.stdout.readline()
                if not line:
                    break
                log_batch += line
            
            if log_batch:
                payload = {
                    "type": "console_log",
                    "data": log_batch
                }
                _post_to_vm1_stream(payload)

            # 2. 每秒發送一次 CPU/RAM 狀態
            now = time.time()
            if now - last_status_time >= 1.0:
                mem = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=None)
                status_payload = {
                    "type": "server_status",
                    "data": {
                        "system": {
                            "cpu_percent": cpu_percent,
                            "ram_used_mb": mem.used // (1024*1024),
                            "ram_total_mb": mem.total // (1024*1024),
                            "ram_percent": mem.percent
                        },
                        "timestamp": int(now * 1000)
                    }
                }
                _post_to_vm1_stream(status_payload)
                last_status_time = now

            time.sleep(0.1) # 100ms cycle

    except Exception as e:
        print(f"[Streamer] Worker crashed: {e}")
    finally:
        if stream_log_process:
            stream_log_process.kill()
            stream_log_process = None
        print("[Streamer] Stopped.")

def _post_to_vm1_stream(payload):
    try:
        req = urllib.request.Request(STREAM_URL, method="POST")
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(payload).encode('utf-8')
        urllib.request.urlopen(req, data=data, timeout=1)
    except Exception as e:
        # 暫時忽略連線錯誤以防止阻塞
        pass 

def start_streaming_to_vm1(filepath):
    global is_streaming, stream_thread
    if is_streaming:
        return
    is_streaming = True
    stream_thread = threading.Thread(target=stream_worker, args=(filepath,), daemon=True)
    stream_thread.start()

def stop_streaming_to_vm1():
    global is_streaming
    is_streaming = False

# ==========================================
# 背景事件驅動機制 (自動關機與智慧存檔偵測)
# ==========================================

VM1_WEBHOOK_URL = "http://10.140.0.2:24445/webhook/shutdown_vm2?key=AdminKey123456"
SHUTDOWN_DELAY_SECONDS = 600  # 10 分鐘 = 600 秒

shutdown_timer = None
shutdown_lock = threading.Lock()
auto_reason_flag = None

def trigger_auto_shutdown():
    """計時炸彈引爆，執行智慧安全關機"""
    global shutdown_timer, auto_reason_flag
    try:
        # 1. 廣播關機警告並發送 stop 給所有 Minecraft 螢幕
        output = subprocess.check_output("screen -ls", shell=True, text=True, stderr=subprocess.STDOUT)
        active_screens = []
        for line in output.split('\n'):
            if "Detached" in line or "Attached" in line:
                parts = line.split('\t')
                if len(parts) > 1:
                    screen_name = parts[1].strip()
                    active_screens.append(screen_name)
                    # 踢出可能卡住的玩家並執行安全存檔
                    subprocess.run(["screen", "-S", screen_name, "-p", "0", "-X", "stuff", "say 伺服器閒置達 10 分鐘，正在執行自動安全存檔並關機...\r"])
                    time.sleep(1)
                    subprocess.run(["screen", "-S", screen_name, "-p", "0", "-X", "stuff", "stop\r"])

        # 標記為自動關機，等待 log_monitor_thread 捕捉到 Quit correctly 即可發送 webhook
        auto_reason_flag = "auto"

    except Exception as e:
        print(f"[AutoShutdown] Error during shutdown sequence: {e}")
    finally:
        with shutdown_lock:
            shutdown_timer = None

def reset_timer():
    """重置或啟動 10 分鐘計時炸彈"""
    global shutdown_timer
    with shutdown_lock:
        if shutdown_timer is not None:
            shutdown_timer.cancel()
        print("[AutoShutdown] Server empty! Starting 10-minute countdown bomb...")
        shutdown_timer = threading.Timer(SHUTDOWN_DELAY_SECONDS, trigger_auto_shutdown)
        shutdown_timer.start()

def cancel_timer():
    """有人進入伺服器，拆除炸彈"""
    global shutdown_timer
    with shutdown_lock:
        if shutdown_timer is not None:
            print("[AutoShutdown] Player joined! Canceling countdown bomb.")
            shutdown_timer.cancel()
            shutdown_timer = None

def get_active_screens():
    """取得所有目前活躍的 screen"""
    screens = []
    try:
        output = subprocess.check_output("screen -ls", shell=True, text=True, stderr=subprocess.STDOUT)
        for line in output.split('\n'):
            if "Detached" in line or "Attached" in line:
                parts = line.split('\t')
                if len(parts) > 1:
                    screens.append(parts[1].strip())
    except:
        pass
    return screens

def trigger_server_list_cmd():
    """向所有遊戲伺服器索取目前人數 (寫入日誌)"""
    for screen_name in get_active_screens():
        subprocess.run(["screen", "-S", screen_name, "-p", "0", "-X", "stuff", "list\r"], stderr=subprocess.DEVNULL)

def log_monitor_thread():
    """被動監聽 Minecraft 日誌"""
    time.sleep(3) # 等待主程式與伺服器暖機
    
    # 確保有 log 檔案可以 tail
    base_dir = "/home/terraria/servers/instances"
    main_log = f"{base_dir}/main/bedrock_screen.log"
    if not os.path.exists(main_log):
        os.makedirs(os.path.dirname(main_log), exist_ok=True)
        open(main_log, 'a').close()

    list_pattern = re.compile(r'(?:There are|共有)\s+(\d+)/(\d+)')
    
    # 開機時先戳一次確認目前有沒有人（有的話取消，沒有的話直接啟動計時器）
    trigger_server_list_cmd()

    # 使用 tail -F 監控所有 instances 底下的 bedrock log
    cmd = ["bash", "-c", f"tail -F {base_dir}/*/bedrock_screen.log 2>/dev/null"]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            # 偵測玩家連線
            if "Player connected:" in line or "PlayerJoin" in line:
                cancel_timer()
                
            # 偵測玩家離線 (不直接開始倒數，而是觸發一次精準的人數查詢)
            elif "Player disconnected:" in line or "PlayerLeave" in line:
                trigger_server_list_cmd()
                
            # 偵測 Minecraft 伺服器順利結束存檔
            elif "Quit correctly" in line:
                global auto_reason_flag
                reason = auto_reason_flag or "manual"
                try:
                    url = f"{VM1_WEBHOOK_URL}&reason={reason}"
                    req = urllib.request.Request(url, method="POST")
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    print(f"Webhook error: {e}")
                auto_reason_flag = None

            # 偵測 list 指令的回傳結果
            else:
                m = list_pattern.search(line)
                if m:
                    current_players = int(m.group(1))
                    if current_players == 0:
                        reset_timer()
                    elif current_players > 0:
                        cancel_timer()

    except Exception as e:
        print(f"[LogMonitor] Died with error: {e}")

if __name__ == "__main__":
    Handler = AgentHandler
    # 啟動背景事件驅動監聽器
    t = threading.Thread(target=log_monitor_thread, daemon=True)
    t.start()
    
    # Listen on all interfaces so VM1 can reach it via internal IP
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Agent API running on port {PORT}")
        httpd.serve_forever()
