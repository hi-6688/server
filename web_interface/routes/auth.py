# routes/auth.py — 登入驗證路由
import json

# 從主設定取得密碼和金鑰
LOGIN_PASSWORD = "hmpb"
API_KEY = "AdminKey123456"


def handle_login(handler, params, instance):
    """POST /login — 密碼驗證，回傳 API Key"""
    if params.get('password') == LOGIN_PASSWORD:
        handler._set_headers()
        handler.wfile.write(json.dumps({"status": "ok", "key": API_KEY}).encode('utf-8'))
    else:
        handler._set_headers(401)
        handler.wfile.write(b'{"error":"Invalid password"}')
