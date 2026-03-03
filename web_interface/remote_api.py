import http.server
import socketserver
import json
import subprocess
import os
import urllib.parse

PORT = 9999
API_KEY = "hihi_secret_key_2026"  # Simple security token

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
                
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Unknown action")

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == "__main__":
    Handler = AgentHandler
    # Listen on all interfaces so VM1 can reach it via internal IP
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Agent API running on port {PORT}")
        httpd.serve_forever()
