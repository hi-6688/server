# 專案規則手冊 (Global Rules)

## 1. 核心設定 (Core Options)
- **Language**: 強制使用繁體中文 (台灣) 回覆所有問題與程式註解。
- **Docker First**: 本專案推崇容器化，若需安裝環境優先使用 Docker。

## 2. 硬性禁止事項 (Anti-Patterns - 觸犯重罰)
- **嚴格禁止寫死路徑**: 讀取設定時必須透過 `.env` 變數抓取。
- **目錄守護原則 (Directory Guard)**: 新增任何零散測試或 Python 工具腳本，必須放在 `scripts/` 下；備份檔與大檔必須放入 `backups/`；嚴禁將任何新檔案建立在專案根目錄。
- **嚴格禁止盲目改檔**: 每當修改程式碼，必須先看目標檔案全文與專業手冊 (`docs/`)，並確保修改沒有架構衝突才能動手。

## 3. 開發手冊索引 (Architecture Docs)
- **UI / Frontend**: 修改畫面時，必須遵循 `docs/FRONTEND_ARCH.md` (毛玻璃風格、堆疊式排版)。
- **API / Backend**: 修改邏輯時，必須遵循 `docs/BACKEND_API.md`。
- **VM split / Scaling**: 修改伺服器連線與節點分配時，必須遵循 `docs/VM_ARCHITECTURE.md`。
- **Discord Bot / 機器人核心 (嗨嗨 HiHi)**: 修改 AI 聊天機器人邏輯與人格時，必須遵循 `docs/HiHi_Proposal.md`。
- **Discord Bot / 功能總管 (嗨螺 Conch)**: 修改遊戲伺服器管理機器人 (神奇嗨螺) 時，請認知它與嗨嗨共用 `discord_bot/` 資料夾但啟動參數為 `BOT_MODE=CONCH`。
- **Discord Bot / 指令對照**: 查詢或新增終端機器人指令時，必須遵循根目錄的 `COMMANDS.md`。

## 4. SOP 觸發機制與防呆 (Workflows & Safeguards)
- **目錄守護原則 (Directory Guard)**: 新增任何測試或 Python 腳本，必須放 `scripts/`；備份檔放大檔必須放 `backups/`；嚴禁將任何新檔案建立在專案根目錄。
- **知識索引強制同步法則 (Knowledge Sync Rule)**: 每次在 `docs/` 新增任何架構文件 (`.md`) 後，**必須**第一時間修改本檔案 (`readrules.md`) 的「開發手冊索引」，將新文件加上對應的標籤與路徑。禁止寫完文件就放著不管。
- 若要更新專案 README 狀態，請直接呼叫工作流 `.agent/workflows/update_readme.md`。
