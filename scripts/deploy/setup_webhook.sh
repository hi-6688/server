#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
SECRET_FILE="$SCRIPT_DIR/.webhook_secret"
SERVICE_FILE="/etc/systemd/system/webhook.service"

# 1. Generate Secret if not exists
if [ ! -f "$SECRET_FILE" ]; then
    echo "Generating new secret..."
    openssl rand -hex 20 > "$SECRET_FILE"
    chmod 600 "$SECRET_FILE"
fi

SECRET=$(cat "$SECRET_FILE")

# 2. Create Systemd Service
echo "Creating systemd service..."

# We need sudo to write to /etc/systemd/system
# Assuming the user runs this script with sudo or has permissions
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=GitHub Webhook Listener
After=network.target

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_DIR/webhook_server.py
WorkingDirectory=$SCRIPT_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOL

# 3. Enable and Start Service
echo "Enabling and Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable webhook
sudo systemctl restart webhook

# 4. Show Info
echo "---------------------------------------------------"
echo "✅ Webhook Server is running!"
echo ""
echo "Please configure your GitHub Webhook with:"
echo "Payload URL: http://YOUR_SERVER_IP:5000/"
echo "Content type: application/json"
echo "Secret: $SECRET"
echo "---------------------------------------------------"
