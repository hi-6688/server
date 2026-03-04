# routes/server.py — 伺服器操作路由 (開機/關機/指令/狀態)
import json
import subprocess
import time
import re
import os
import proxy_helpers


def handle_start_post(handler, params, instance):
    """POST /start — 透過 VM2 啟動伺服器"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write('{"error":"VM2 is offline. Please use /mc開機 to boot the server first."}'.encode('utf-8'))
        return

    proxy_helpers.flush_offline_cache()

    try:
        res = proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="")
        if res.get('status') == 'success':
            proxy_helpers.proxy_to_agent("start_screen", screen_name=instance.screen_name, path=instance.path)
            handler._set_headers()
            handler.wfile.write(b'{"status":"started"}')
        else:
            handler._set_headers(500)
            handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_start_get(handler, params, instance):
    """GET /start — 本機直接啟動伺服器"""
    if instance.is_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"Server already running"}')
        return
    try:
        cmd = 'cd %s && screen -dmS %s -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"' % (instance.path, instance.screen_name)
        subprocess.run(cmd, shell=True, check=True)
        handler._set_headers()
        handler.wfile.write(b'{"status":"started"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_stop_post(handler, params, instance):
    """POST /stop — 透過 VM2 關閉伺服器並切斷電源"""
    try:
        def do_shutdown():
            if proxy_helpers.is_vm2_running():
                try:
                    proxy_helpers.backup_all_instances_to_cache()
                except Exception as e:
                    print(f"[Web Shutdown] Backup failed: {e}")
                
                proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="say 網頁面板發起安全關機指令，系統執行存檔並準備斷電...\r")
                time.sleep(1)
                proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command="stop\r")
                time.sleep(15) 
                
                # 切斷 VM2 電源
                import sys
                bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../discord_bot')
                if bot_path not in sys.path:
                    sys.path.append(bot_path)
                from utils.gcp_manager import GCPManager
                gcp = GCPManager(project_id="project-ad2eecb1-dd0f-4cf4-b1a", zone="asia-east1-c")
                gcp.stop_instance("instance-20260220-174959")
                
        import threading
        threading.Thread(target=do_shutdown, daemon=True).start()
        
        handler._set_headers()
        handler.wfile.write(b'{"status":"stopped"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_stop_get(handler, params, instance):
    """GET /stop — 本機直接關閉伺服器"""
    try:
        subprocess.run(['screen', '-S', instance.screen_name, '-p', '0', '-X', 'stuff', 'stop\n'])
        time.sleep(3)
        subprocess.run(['screen', '-S', instance.screen_name, '-X', 'quit'], stderr=subprocess.DEVNULL)
        handler._set_headers()
        handler.wfile.write(b'{"status":"stopped"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_command(handler, params, instance):
    """POST /command — 發送指令到伺服器"""
    cmd = params.get('cmd', '')
    if not cmd:
        handler._set_headers(400)
        return
    try:
        if proxy_helpers.is_vm2_running():
            proxy_helpers.proxy_to_agent("execute_command", screen_name=instance.screen_name, command=cmd)
            if cmd.strip() in ['list', 'gamerule ']:
                time.sleep(1.0)
        handler._set_headers()
        handler.wfile.write(json.dumps({"result": "sent"}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_exec(handler, params, instance):
    """POST /exec — 執行指令並回傳 log 尾部"""
    cmd = params.get('cmd', '')
    if not cmd:
        handler._set_headers(400)
        handler.wfile.write(b'{"error":"No command"}')
        return
    try:
        subprocess.run(['screen', '-S', instance.screen_name, '-p', '0', '-X', 'stuff', '%s\\n' % cmd])
        time.sleep(1.5)
        log_file = instance.get_log_file()
        output = ''
        if os.path.exists(log_file):
            output = subprocess.check_output(['tail', '-n', '20', log_file]).decode('utf-8', errors='replace')
        handler._set_headers()
        handler.wfile.write(json.dumps({"result": output}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_server_status(handler, params, instance):
    """GET /server_status — 查詢伺服器是否運行中"""
    handler._set_headers()
    handler.wfile.write(json.dumps({"running": instance.is_running()}).encode('utf-8'))


def handle_stats(handler, params, instance):
    """GET /stats — 查詢系統資源 (CPU/RAM)"""
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

        resp = {
            "cpu": {"load_1": float(load), "load_5": 0.0},
            "memory": {"percent": perc, "used": "%s GB" % used_gb, "total": "%s GB" % tot_gb},
            "disk": {"percent": 0, "used": "0 GB", "total": "0 GB"},
            "network": {"rx_gb": "0", "tx_gb": "0"}
        }
        handler._set_headers()
        handler.wfile.write(json.dumps(resp).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_version(handler, params, instance):
    """GET /version — 取得伺服器版本"""
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
    handler._set_headers()
    handler.wfile.write(json.dumps({"version": version}).encode('utf-8'))
