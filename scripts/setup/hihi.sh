#!/bin/bash
# 啟動 HiHi CLI (終端機聊天模式)
# 確保 .env 檔案被載入 (如果 cli.py 有處理這一塊就不用 source)
export PYTHONPATH=/home/terraria/servers/discord_bot
cd /home/terraria/servers/discord_bot
.venv/bin/python3 cli.py
