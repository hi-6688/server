#!/bin/bash
pkill -f "discord_bot/main.py"
sleep 1
cd /home/terraria/servers/discord_bot
nohup python3 main.py > bot.log 2>&1 &
echo "Bot restarted."
