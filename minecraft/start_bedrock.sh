#!/bin/bash
# Minecraft Bedrock 伺服器啟動腳本
# 使用命名管道 (FIFO) 接收指令，同時輸出日誌到檔案

cd /home/terraria/servers/minecraft

# 設定 LD_LIBRARY_PATH
export LD_LIBRARY_PATH=.

# 建立命名管道（如果不存在）
FIFO_PATH="/home/terraria/servers/minecraft/bedrock_input"
[ -p "$FIFO_PATH" ] || mkfifo "$FIFO_PATH"

# 清空舊日誌
> bedrock_screen.log

# 啟動伺服器：
# - stdin 從 FIFO 讀取（用 tail -f 保持 FIFO 開啟）
# - stdout/stderr 同時輸出到終端 (journalctl) 和日誌檔案
# 使用 Dummy Writer 保持 FIFO 開啟，防止 EOF 導致讀取中斷
sleep infinity > "$FIFO_PATH" &
SLEEP_PID=$!
trap "kill $SLEEP_PID" EXIT

# 使用 cat 持續讀取 (因有 Dummy Writer，cat 不會結束)
cat "$FIFO_PATH" | ./bedrock_server 2>&1 | stdbuf -oL tee -a bedrock_screen.log
