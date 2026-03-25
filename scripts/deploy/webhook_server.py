#!/usr/bin/env python3
import http.server
import json
import os
import hmac
import hashlib
import subprocess
import sys

# Configuration
PORT = 5000
SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.webhook_secret')
PROJECT_DIR = '/home/terraria/servers'

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Load Secret
        if not os.path.exists(SECRET_FILE):
            self.send_error(500, "Secret not configured")
            return
        
        with open(SECRET_FILE, 'r') as f:
            SECRET = f.read().strip().encode('utf-8')

        # 2. Get Headers and Payload
        header_signature = self.headers.get('X-Hub-Signature-256')
        if not header_signature:
            self.send_error(403, "Missing signature")
            return
            
        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)

        # 3. Verify Signature
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha256':
            self.send_error(501, "Operation not supported")
            return

        mac = hmac.new(SECRET, msg=payload, digestmod=hashlib.sha256)
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            self.send_error(403, "Invalid signature")
            return

        # 4. Handle Event (Push)
        # GitHub sends 'ping' event on creation, treat as success
        event = self.headers.get('X-GitHub-Event', 'ping')
        
        if event == 'ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Pong! Webhook configured successfully.")
            return

        if event == 'push':
            print("Received push event. Triggering git pull...")
            try:
                # Execute git pull
                result = subprocess.check_output(
                    ['git', 'pull'], 
                    cwd=PROJECT_DIR, 
                    stderr=subprocess.STDOUT
                )
                print(f"Git Pull Result: {result.decode('utf-8')}")
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Deployed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Git Pull Failed: {e.output.decode('utf-8')}")
                self.send_error(500, f"Git pull failed: {e.output.decode('utf-8')}")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Event received but ignored")

if __name__ == '__main__':
    print(f"Starting Webhook Server on port {PORT}...")
    server = http.server.HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    server.serve_forever()
