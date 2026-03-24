#!/bin/bash
pkill -f "python3 api.py"
sleep 1
cd /home/terraria/servers/web_interface
nohup python3 api.py > api_server.log 2>&1 &
echo "API server restarted."
