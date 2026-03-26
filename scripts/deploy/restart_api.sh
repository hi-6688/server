#!/bin/bash
pkill -f "python3 main.py"
sleep 1
cd /home/terraria/servers/web_interface
nohup python3 main.py > api_server.log 2>&1 &
echo "API server restarted."
