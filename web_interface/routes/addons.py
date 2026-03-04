# routes/addons.py — 模組 (Addon) 管理路由
import os
import json
import re
import urllib.parse
import proxy_helpers


def handle_list_addons(handler, params, instance):
    """GET /addons — 列出所有已安裝模組"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers()
        handler.wfile.write(json.dumps({"addons": []}).encode('utf-8'))
        return

    res = proxy_helpers.proxy_to_agent("list_addons", path=instance.path)
    if res.get('status') == 'success':
        handler._set_headers()
        handler.wfile.write(json.dumps({"addons": res.get("addons", [])}).encode('utf-8'))
    else:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))


def handle_upload_addon(handler, params, instance, raw_headers, rfile, query_string):
    """POST /addon/upload — 上傳模組檔案"""
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
        original_filename = 'addon.zip'

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
                        header_str = part[:header_end].decode('utf-8', errors='replace')
                        fn_match = re.search(r'filename="([^"]+)"', header_str)
                        if fn_match:
                            original_filename = fn_match.group(1)
                    break

        addon_type = urllib.parse.parse_qs(query_string).get('type', [''])[0]
        encoded_data = base64.b64encode(file_data).decode('utf-8')

        res = proxy_helpers.proxy_to_agent("upload_addon",
            path=instance.path, addon_type=addon_type,
            original_filename=original_filename, file_data_base64=encoded_data)

        if res.get('status') == 'success':
            handler._set_headers()
            handler.wfile.write(json.dumps({
                "status": "ok",
                "message": res.get("message", "Uploaded"),
                "packs": res.get("packs", [])
            }).encode('utf-8'))
        else:
            handler._set_headers(500)
            handler.wfile.write(json.dumps({"error": res.get("message")}).encode('utf-8'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_delete_addon(handler, params, instance):
    """POST /addon/delete — 刪除模組"""
    if not proxy_helpers.is_vm2_running():
        handler._set_headers(409)
        handler.wfile.write(b'{"error":"VM2 is offline"}')
        return

    addon_name = params.get('name', '')
    addon_type = params.get('type', 'behavior_packs')
    if not addon_name:
        handler._set_headers(400)
        handler.wfile.write(b'{"error":"No addon name"}')
        return
    try:
        proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(instance.path, addon_type, addon_name))
        handler._set_headers()
        handler.wfile.write(b'{"status":"deleted"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
