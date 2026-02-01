# Games Server Project 🎮

這是一個整合 Minecraft (Bedrock) 與 Terraria 伺服器的管理專案，包含自動化腳本、Discord 機器人與網頁管理介面。

## 📂 專案結構 (Structure)

- **`minecraft/`**: Minecraft Bedrock 伺服器核心 (存檔 `worlds/` 已被 Git 忽略)
- **`terraria/`**: Terraria 伺服器核心 (存檔 `Worlds/` 已被 Git 忽略)
- **`web_interface/`**: 網頁管理介面 (Python + HTML/JS，原 `minecraft/web`)
- **`discord_bot/`**: Discord 機器人 (查詢狀態、管理伺服器)
- **`scripts/`**: 自動化腳本 (Git 同步、Webhook)
- **`configs/`**: 設定檔存放處

## 🚀 快速開始 (Quick Start)

### 1. 啟動網頁介面
```bash
nohup python3 web_interface/api.py &
```
網頁將在 `http://<IP>:8888` 運行。

### 2. 啟動 Discord 機器人
```bash
python3 discord_bot/main.py
```

### 3. 同步程式碼
使用自動同步腳本將本地變更推送到 GitHub：
```bash
./scripts/sync_git.sh
```

## 🔄 自動化部署 (Webhook)
本專案已設定 GitHub Webhook，當 GitHub 有 Push 事件時，伺服器會自動拉取最新程式碼。
- **Payload URL**: `http://<IP>:5000/`
- **Secret**: (已設定於伺服器)

## 📝 注意事項
- **遊戲存檔**: 為了避免檔案過大與衝突，所有 save files 都不會上傳到 GitHub。
- **遷移**: 若要搬移伺服器，請參考 `migration_guide.md` (位於 artifacts)。
