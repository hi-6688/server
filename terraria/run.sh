#!/bin/bash
cd $(dirname "$0")
# 確保有 venv
if [ ! -d "venv" ]; then
    echo "錯誤：找不到 venv 資料夾！請確認您在 terraria-server 資料夾內。"
    exit 1
fi
source venv/bin/activate

# --- 這裡填入您的設定 ---
export DISCORD_BOT_TOKEN='MTM4MTQ4Mjg3Mjg0NTYzNTYxNA.G45upl.vVeG-ndcGbAEDlbvdv_h6fvctIQ5agbB1rkkQ4' export DISCORD_CHANNEL_ID='1463979890805051423' # ----------------------

echo "正在啟動泰拉瑞亞管家..."
python3 terraria_wrapper.py
