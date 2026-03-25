---
description: 同步更新所有 docs/ 資料夾內的架構文件，確保與程式碼一致
---
請完全依照以下步驟執行：

1. **列出所有文件**：掃描 `docs/` 資料夾，列出所有 `.md` 文件。

2. **逐一比對**：對每份文件，讀取其內容並與對應的程式碼進行交叉比對：
   - `FRONTEND_ARCH.md` ↔ `web_interface/frontend/src/`
   - `BACKEND_API.md` ↔ `web_interface/api.py`
   - `VM_ARCHITECTURE.md` ↔ `web_interface/proxy_helpers.py`, `web_interface/remote_api.py`
   - `HiHi_Proposal.md` ↔ `discord_bot/utils/memory_manager.py`, `discord_bot/cogs/ai_chat.py`

3. **修正過期內容**：包含但不限於：
   - 檔案結構樹與實際不符
   - 技術堆疊描述過時
   - API 路由新增或移除但文件未更新
   - 重複段落或錯字

4. **回報修正摘要**：列出每份文件的修正項目。

5. **同步索引**：確認 `.agent/rules/readrules.md` 的「開發手冊索引」包含所有 `docs/` 內的文件。
