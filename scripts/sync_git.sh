#!/bin/bash

# 進入專案根目錄
cd /home/terraria/servers

# 顯示狀態
echo "Checking status..."
git status

# 加入所有變更
echo "Adding changes..."
git add .

# 提交變更 (使用當前時間作為訊息)
echo "Committing..."
git commit -m "Auto sync: $(date '+%Y-%m-%d %H:%M:%S')"

# 推送到 GitHub
echo "Pushing to GitHub..."
git push

echo "Done! ✅"
