# routes/worlds.py — 世界地圖管理路由
import os
import json
import re
import urllib.parse
import proxy_helpers


def handle_list_worlds(handler, params, instance):
    """GET /worlds — 列出所有世界"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers()
        handler.wfile.write(json.dumps({"worlds": [], "active": "Offline"}).encode('utf-8'))
        return

    res = proxy_helpers.proxy_to_agent("list_worlds", path=instance.path)
    if res.get('status') == 'success':
        handler._set_headers()
        handler.wfile.write(json.dumps({"worlds": res.get("worlds", []), "active": res.get("active", "")}).encode('utf-8'))
    else:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))


def handle_switch_world(handler, params, instance):
    """POST /switch_world — 切換使用的世界"""
    world = params.get('world')
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"VM2 is offline"}')
        return
    if not world:
        handler._set_headers(400)
        handler.wfile.write(b'{"error":"No world name"}')
        return
    try:
        props_path = os.path.join(instance.path, 'server.properties')
        res = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)

        if res.get('status') == 'success':
            content = res.get('content', '')
            new_content = ''
            found = False
            for line in content.splitlines():
                if line.strip().startswith('level-name='):
                    new_content += "level-name=%s\n" % world
                    found = True
                else:
                    new_content += line + '\n'
            if not found:
                new_content += "level-name=%s\n" % world

            proxy_helpers.proxy_to_agent("write_file", filepath=props_path, content=new_content)

        handler._set_headers()
        handler.wfile.write(b'{"status":"switched"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_delete_world(handler, params, instance):
    """POST /delete_world — 刪除世界"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"VM2 is offline"}')
        return

    world = params.get('world')
    if world:
        proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(instance.path, 'worlds', world))
        handler._set_headers()
        handler.wfile.write(b'{"status":"deleted"}')


def handle_reset_world(handler, params, instance):
    """POST /reset_world — 重置世界地形 (保留設定與模組)"""
    try:
        if not proxy_helpers.is_vm2_running():
            handler._set_headers(409)
            handler.wfile.write(b'{"error":"VM2 is offline"}')
            return

        # 讀取使用中的世界名稱
        active_world = ''
        props_path = os.path.join(instance.path, 'server.properties')
        res_props = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)
        if res_props.get('status') == 'success':
            content = res_props.get('content', '')
            for line in content.splitlines():
                if line.strip().startswith('level-name='):
                    active_world = line.strip().split('=', 1)[1]
                    break

        if not active_world:
            handler._set_headers(400)
            handler.wfile.write(b'{"error":"Cannot determine active world"}')
            return

        res = proxy_helpers.proxy_to_agent("reset_world",
            path=os.path.join(instance.path, 'worlds', active_world),
            screen_name=instance.screen_name)

        if res.get('status') == 'success':
            handler._set_headers()
            handler.wfile.write(json.dumps({
                "status": "ok",
                "world": active_world,
                "message": "地形資料已重置，設定與模組已保留"
            }).encode('utf-8'))
        else:
            handler._set_headers(500)
            handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_upload(handler, params, instance, raw_headers, rfile):
    """POST /upload — 上傳世界地圖 (.mcworld / .zip)"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"VM2 is offline"}')
        return
    try:
        import base64
        data_len = int(raw_headers.get('Content-Length', 0))
        raw_data = rfile.read(data_len)

        content_type = raw_headers.get('Content-Type', '')
        file_data = raw_data

        if 'boundary=' in content_type:
            boundary = content_type.split('boundary=')[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            parts = raw_data.split(('--' + boundary).encode())
            for part in parts:
                if b'filename=' in part:
                    header_end = part.find(b'\r\n\r\n')
                    if header_end == -1:
                        header_end = part.find(b'\n\n')
                    if header_end != -1:
                        file_data = part[header_end + 4:].rstrip(b'\r\n--')
                    break

        encoded_data = base64.b64encode(file_data).decode('utf-8')
        res = proxy_helpers.proxy_to_agent("upload_zip",
            path=os.path.join(instance.path, 'worlds'), file_data_base64=encoded_data)

        if res.get('status') == 'success':
            handler._set_headers()
            handler.wfile.write(b'{"status":"ok", "message":"Uploaded"}')
        else:
            handler._set_headers(500)
            handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_download(handler, params, instance):
    """GET /download — 下載世界地圖為 zip"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"VM2 is offline"}')
        return

    world = params.get('world', '')
    if not world:
        handler._set_headers(400)
        handler.wfile.write(b'{"error":"No world specified"}')
        return

    try:
        import base64
        res = proxy_helpers.proxy_to_agent("download_world", path=os.path.join(instance.path, 'worlds', world))
        if res.get('status') == 'success' and 'base64_data' in res:
            data = base64.b64decode(res['base64_data'])
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/zip')
            handler.send_header('Content-Disposition', 'attachment; filename="%s.zip"' % world)
            handler.send_header('Content-Length', str(len(data)))
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(data)
        else:
            handler._set_headers(404)
            handler.wfile.write(b'{"error":"World folder not found or zip failed"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_update_server(handler, params, instance, query_string):
    """POST /update — 更新伺服器版本"""
    try:
        url = urllib.parse.parse_qs(query_string).get('url', [''])[0]
        if not url:
            url = params.get('url')
        if not url:
            raise ValueError("No URL provided")

        if not proxy_helpers.is_vm2_running():
            handler._set_headers(409)
            handler.wfile.write(b'{"error":"VM2 is offline"}')
            return

        res = proxy_helpers.proxy_to_agent("update_server",
            path=instance.path, url=url, screen_name=instance.screen_name)
        if res.get('status') == 'success':
            handler._set_headers()
            handler.wfile.write(b'{"status":"updated"}')
        else:
            handler._set_headers(500)
            handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
