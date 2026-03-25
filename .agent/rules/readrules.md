# 專案規則手冊 (Global Rules)

## 1. 核心設定 (Core Options)
- **Language**: 強制使用繁體中文 (台灣) 回覆所有問題與程式註解。
- **Docker First**: 本專案推崇容器化，若需安裝環境優先使用 Docker。

## 2. 硬性禁止事項 (Anti-Patterns - 觸犯重罰)
- **嚴格禁止寫死路徑**: 讀取設定時必須透過 `.env` 變數抓取。
- **目錄守護原則 (Directory Guard)**: 新增任何工具腳本，必須按分類放在 `scripts/` 對應子目錄下（`db/` 資料庫、`deploy/` 部署維運、`sync/` 同步工具、`minecraft/` MC 工具、`setup/` 一次性安裝、`tests/` 測試腳本）；備份檔與大檔必須放入 `backups/`；嚴禁將任何新檔案建立在專案根目錄或 `scripts/` 根層。
- **嚴格禁止盲目改檔**: 每當修改程式碼，必須先看目標檔案全文與專業手冊 (`docs/`)，並確保修改沒有架構衝突才能動手。
- **前端快取陷阱 (Frontend Cache Trap)**: 任何時候在 `api.py` 等後端分發 React 編譯後的 `index.html`，**必須強制加上 `Cache-Control: no-cache` 標頭**，嚴禁發生改了前端但使用者瀏覽器讀到舊快取的低級錯誤。

## 3. 開發手冊索引 (Architecture Docs)
- **UI / Frontend**: 修改畫面時，必須遵循 `docs/FRONTEND_ARCH.md` (透明玻璃風格、頂部導航+居中單欄佈局)。
- **WebSocket / SSE**: 實作或檢查面板即時通訊機制時，必須遵循 `docs/SMART_CONNECTION_ARCH.md` (按需連線與智慧降級)。
- **API / Backend**: 修改邏輯時，必須遵循 `docs/BACKEND_API.md`。新增路由時在 `routes/` 對應模組中加 handler，再到 `api.py` 註冊。
- **VM split / Scaling**: 修改伺服器連線與節點分配時，必須遵循 `docs/VM_ARCHITECTURE.md`。
- **Discord Bot / 機器人核心 (嗨嗨 HiHi)**: 修改 AI 聊天機器人邏輯與人格時，必須遵循 `docs/HiHi_Proposal.md`。
- **Discord Bot / 功能總管 (嗨螺 Conch)**: 修改遊戲伺服器管理機器人 (神奇嗨螺) 時，請認知它與嗨嗨共用 `discord_bot/` 資料夾但啟動參數為 `BOT_MODE=CONCH`。
- **Discord Bot / 指令對照**: 查詢或新增終端機器人指令時，必須遵循根目錄的 `COMMANDS.md`。

## 4. SOP 觸發機制與防呆 (Workflows & Safeguards)
- **知識索引強制同步法則 (Knowledge Sync Rule)**: 每次在 `docs/` 新增任何架構文件 (`.md`) 後，**必須**第一時間修改本檔案 (`readrules.md`) 的「開發手冊索引」，將新文件加上對應的標籤與路徑。禁止寫完文件就放著不管。
- **完成重大改動後必須跑 `/full_audit`**: 每當完成結構性重構或新增/移除多個檔案後，必須呼叫 `.agent/workflows/full_audit.md` 同步所有文件。
- **開發新功能**：遵循 `.agent/workflows/new_feature.md` — 先討論架構、建分支、分步實作、同步文件。
- **修復 Bug**：遵循 `.agent/workflows/fix_bug.md` — 先定位根因、最小化修改、驗證無副作用。
- **提交前檢查**：每次 `git commit` 前，應跑 `.agent/workflows/pre_commit.md` 檢查敏感資訊與語法。
- 若要更新專案 README 狀態，請直接呼叫工作流 `.agent/workflows/update_readme.md`。
- 若只需同步 `docs/` 內的文件，請呼叫 `.agent/workflows/sync_docs.md`。
