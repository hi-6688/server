#!/bin/bash
cd $(dirname "$0")
# 確保有 venv
if [ ! -d "venv" ]; then
    echo "錯誤：找不到 venv 資料夾！請確認您在 terraria-server 資料夾內。"
    exit 1
fi
source venv/bin/activate

# --- 這裡填入您的設定 ---
# Token is now loaded from .env file by the python script
# export DISCORD_BOT_TOKEN='...'

echo "正在啟動泰拉瑞亞管家..."
python3 terraria_wrapper.py
