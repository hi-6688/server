---
description: 更新專案 README 文件與 ROADMAP 的標準作業流程
---
請完全依照以下步驟執行：

1. **現況盤點**：檢查目前專案根目錄 (`servers/`) 下的檔案與資料夾結構。
2. **遵守 README 標準格式**：在編輯 `README.md` 時，必須嚴格遵守以下結構與語言要求 (繁體中文)：

### I. 📁 檔案結構全覽 (Project File Structure)
   - 必須列出 **所有** 檔案與資料夾 (包含 .env, Dockerfile, docker-compose.yml, app.yaml)。
   - 使用 `tree` 圖表格式。
   - **關鍵**: 每個檔案都必須有註解說明其用途。

### II. 🚀 環境與執行 (Quick Start - Docker First)
   - 提供可直接複製貼上的 **Docker 部署** 指令。
   - 標準指令: `docker-compose up --build`
   - 說明「成功訊號」 (例如: Uvicorn running on 0.0.0.0:8080)。

### III. 📝 開發進度 (Dev Log)
   - 維護已完成 (`-[x]`) 與待辦 (`-[ ]`) 的清單。

3. **同步 ROADMAP**：如果本次更新涉及未來的開發計畫或已完成某個里程碑，請一併更新 `ROADMAP.md`。
