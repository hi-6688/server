# routes/files.py — 檔案讀寫路由
import os
import json
import proxy_helpers


def handle_read(handler, params, instance):
    """GET /read — 讀取設定檔 (server.properties, allowlist.json 等)"""
    filename = params.get('file', '')
    fpath = os.path.join(instance.path, filename)
    allowed_files = ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json', 'bedrock_screen.log']

    if filename not in allowed_files:
        handler._set_headers(404)
        handler.wfile.write(b'{"content":""}')
        return

    # 優先檢查離線快取
    cached_content = proxy_helpers.read_offline_cache(instance.path, filename)
    if cached_content is not None:
        handler._set_headers()
        handler.wfile.write(json.dumps({"content": cached_content, "source": "offline_cache"}).encode('utf-8'))
        return

    if proxy_helpers.is_vm2_running():
        lines = params.get('lines', '')
        if lines:
            res = proxy_helpers.proxy_to_agent("read_log_tail", filepath=fpath, lines=int(lines))
        else:
            res = proxy_helpers.proxy_to_agent("read_file", filepath=fpath)

        if res.get('status') == 'success':
            content = res.get('content', '')
            handler._set_headers()
            handler.wfile.write(json.dumps({"content": content}).encode('utf-8'))
        else:
            handler._set_headers(404)
            handler.wfile.write(b'{"content":""}')
    else:
        handler._set_headers(404)
        handler.wfile.write(b'{"content":""}')


def handle_write(handler, params, instance):
    """POST /write — 覆寫設定檔"""
    filename = params.get('file')
    allowed_files = ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json']

    if filename not in allowed_files:
        handler._set_headers(403)
        handler.wfile.write(b'{"error":"File not allowed"}')
        return

    content = params.get('content')
    full_dest = os.path.join(instance.path, filename)

    try:
        if proxy_helpers.is_vm2_running():
            res = proxy_helpers.proxy_to_agent("write_file", filepath=full_dest, content=content)
            if res.get('status') == 'success':
                handler._set_headers()
                handler.wfile.write(b'{"status":"saved"}')
            else:
                handler._set_headers(500)
                handler.wfile.write(json.dumps({"error": res.get('message')}).encode('utf-8'))
        else:
            # 離線快取
            proxy_helpers.save_offline_cache(instance.path, filename, content)
            handler._set_headers()
            handler.wfile.write(b'{"status":"saved_offline"}')
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
