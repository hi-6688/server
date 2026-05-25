# 更新日誌 (CHANGELOG)

本檔案記錄了專案的所有重大更新與架構變動。這對於 Agent (AI 助手) 理解專案演進至關重要。

## [2026-05-25] - 解決無狀態 Steps 工具呼叫 400 格式錯誤與 TurnParam 嵌套大一統
### 🐛 錯誤修復 (Fixes) & 🚀 架構與系統升級 (Architecture)
- **修正無狀態工具 400 錯誤**：徹底解決 Interactions API 在 `store=False` (Stateless Steps) 模式下，因 `tool_results` 類型不被 API 支援以及 thought 簽章丟失導致的 400 格式錯誤。
- **TurnParam 嵌套大一統**：將全量對話歷史與工具交互歷史全面對齊 Google 官方正統的 `TurnParam` (`role` + `content`) 結構。大腦剛產生的 steps (包含 thought 簽章與 `function_call`) 會以原裝 list 包裹在 `role: "model"` 的 Turn 內部；工具執行結果會包裝成標準的 `function_result` (`call_id`, `name`, `result`)，包裹在 `role: "user"` 的 Turn 內部。從根本上解決了 `Cannot specify tool calls outside of Turn items` 與 `Request contains an invalid argument` 兩大 API schema 驗證地雷，完美實現 100% 絕對穩定、原生連貫的無狀態大腦推理管道。

## [2026-05-24] - 更新 Gemini CLI 工具
### 🚀 效能與系統最佳化 (Performance & System)
- **更新 Gemini CLI 工具**：應使用者要求，已重新將 Gemini CLI 全域工具更新至最新版 (v0.43.0)，並安裝於 `~/.local` 目錄。

## [2026-05-24] - 遷移至 Google GenAI Interactions API (v7.0 核心升級)
### 🚀 架構與系統升級 (Architecture)
- **大腦核心 API 遷移**：將 `ai_chat.py` 中 `_call_gemini_agent` 核心從舊有的 `generateContent` 遷移至最新的 Google Interactions API（底層使用 `client.aio.interactions.create`）。
- **手動工具執行迴圈 (Manual Tool Looping)**：因 Interactions API 不支援自動工具呼叫，實作非同步 `while` 迴圈自主分發執行 `save_memory`、`manage_fact`、`search_memory` 與 `learn_knowledge` 等工具。
- **解決 SDK 屬性與格式限制**：防禦性避開 python SDK `google-genai` (1.73.1) 的屬性缺失與格式衝突，包括使用 `outputs` 取代不存在的 `steps` 屬性，自建提取 output text 方法取代 `output_text` 屬性，將 `tools` 宣告平坦化為符合 Interactions 規格的 `type: "function"` 字典列表，以及第一階段 (有 tools) 移除 `response_format` 避開 API 400 衝突。
- **無狀態歷史轉換 (Stateless History Conversion)**：將對話歷史轉換為符合 Interactions 規格的 input format（以 `content` 欄位取代原本的 `parts`，並相容多模態二進位圖片與貼圖傳輸）。不使用 `previous_interaction_id` 串接兩階段以防 JSON 結構污染會話歷史。
- **實時中繼遙測播報 (Live Telemetry)**：實作 `_emit_telemetry_live`，在手動 Tool 迴圈執行的中繼狀態下，即時發送腦內動態播報 Embed 至 `INNER_WORLD_CHANNEL_ID`。
- **資料庫 Schema 擴充**：於 PostgreSQL 的 `chat_history` 表中新增 `interaction_id` 欄位以利追蹤，並調整 `MemoryManager` 中的 `log_chat` 和 `get_recent_chat_history` 以支援對話 ID 的寫入與讀取。

## [2026-05-23] - 雙階段 Function Calling 原生 SDK 化與全域文檔重構
### 🚀 架構與系統升級 (Architecture)
- **雙階段管線與原生 SDK 化**：將對話決策邏輯重構為 `google-genai` SDK 原生 `tools` 自動執行管線，廢除了舊有自製 JSON 模擬與 `MAX_STEPS` 手動解析迴圈。大腦思考解耦為階段一 `LogicRouter`（輸出 `MemoryState`）與階段二 `ChatGenerator`（輸出 `PersonaResponse`），從根本上解決注意力渙散與角色崩潰問題。
- **Embedding L2 歸一化修正**：解決 `gemini-embedding-2` 截斷為 768 維度向量時預設未歸一化導致的 pgvector 餘弦相似度檢索精度失真問題，並移除了 `task_type` 欄位以相容正式版 API。
- **文檔架構 SSOT 重構與防呆歸檔**：建立獨立的技術規格書 `docs/TECHNICAL_SPEC.md` 作為型別與數學公式的唯一事實來源。將已關閉的 Web 與 VM 相關舊文檔移至 `docs/archive/` 進行防呆歸檔，防止 AI 助手被舊有架構誤導。
- **生理時鐘與中斷排程解耦修復**：引入 `sensory_interrupt_event`（感官中斷）與 `schedule_update_event`（排程更新）雙事件機制，取代舊有單一混淆的 `wake_event`。修復了 AI 修改鬧鐘睡眠時間會自我驚醒並誤判成被吵醒的 Bug，並在 `on_message` 中加入感官吵醒事件觸發，使心跳引擎的主動甦醒能與 Discord 對話狀態精確同步。

## [2026-05-21] - 運行架構落差修復與功能整合
### 🚀 架構與系統升級 (Architecture)
- **長期記憶寫入佇列 Bug 修復**：修復了 `MemoryManager` 初始化中遺漏 `memory_queue` 宣告的 Bug，並在 `init_pool` 中自動建立 Queue 與啟動 `_process_memory_queue` 的背景非同步寫入任務，且在 `close_pool` 加入安全取消協程的機制，解決呼叫 `save_memory` 時會拋出 AttributeError 崩潰的問題。
- **DNA 核心記憶注入**：調整了 `ai_chat.py` 的 `_get_system_prompt`，在產出的 `system_instruction` Prompt 最頂端注入已讀取的 `self.core_memory_text`（來自 `core_memory.md`），以實作三明治記憶結構的最上層。
- **網址連結解析整合**：在 `_process_buffer_task` 批次訊息處理流程中，整合網址 URL 正則匹配，並調用 `fetch_url_content` 非同步抓取網頁標題與內容摘要作為 `[系統提示 - 連結解析]` 注入給 AI 閱讀。
- **單元測試路徑相容性修復**：修正 `memory_manager.py` 底部的單元測試程式中 `.env` 的動態相對路徑，並增加佇列寫入的等待超時，以方便本地調試。
- **企劃書實作現狀標記**：同步更新 `docs/HiHi_Proposal.md`，以「💡 實作現狀備註」將 ALL 模式 Cog 過濾、記憶寫入 Bug、排程偏差及核心記憶注入缺失等現狀透明化，同時保持核心願景架構不變。
- **死碼清理與多媒體傳輸 SDK 原生化**：移除 `ai_chat.py` 中 114 行無效的 RAM 歷史管理死碼（`_manage_history_overflow` 等函數）；重構圖片與貼圖處理段落，移除 `base64` 手動轉碼，改用 `types.Part.from_bytes` 原生二進位傳輸，優化了效能並使程式碼更加精簡原生。

## [2026-05-20] - CLI 升級與開發環境移轉
### 🚀 效能與系統最佳化 (Performance & System)
- **移轉至 Antigravity CLI**：因應原 `Gemini CLI` 即將於 2026 年 6 月 18 日停止服務，已將 VM 中的 CLI 升級移轉為最新版的 `Antigravity CLI` (`agy` v1.0.0)。
- **設定檔與插件移轉**：成功將原先 Gemini CLI 的 plugins、commands 與 mcpServers 設定匯入新版 `agy` 設定中。
- **工作區與專案設定更新**：更新了 `docs/servers.code-workspace` 與 `.vscode/settings.json`，將 VS Code 內建的 "Gemini CLI" 終端機設定更新為 "Antigravity CLI"，並修正啟動參數為 `agy --dangerously-skip-permissions`。
- **新增中文設定與指令指南**：建立 [[antigravity_config_zh.md](file:///home/hi6688/servers/docs/antigravity_config_zh.md)] 提供 Antigravity CLI 的設定參數、MCP 伺服器、啟動 Flag、**常用子指令/斜線指令**以及**官方內建子代理人 (Subagents)** 的繁體中文對照說明，便於日後維護參考。
- **舊版 CLI 卸載**：已安全移除原有的全域 npm 套件 `@google/gemini-cli`，避免指令衝突。

## [2026-05-12] - 修復終端機遞迴執行記憶體爆炸問題
### 🐛 錯誤修復 (Fixes)
- **OOM 問題排除**：修復了因 `.vscode/settings.json` 中將預設終端機設定為 `Gemini CLI` (`gemini -y`)，導致擴充套件 (如 Jules) 開啟終端機時引發無限遞迴執行 `gemini -y`，進而造成伺服器記憶體耗盡 (OOM) 的問題。已將預設終端機改回 `bash` 並終止相關程序。

## [2026-05-11] - AI 模型 API 正式版搬遷
### 🚀 效能與系統最佳化 (Performance & System)
- **Gemini 模型正式版搬遷**：因應 `gemini-3.1-flash-lite-preview` 即將棄用，已將專案環境變數 `.env` 與程式碼 `discord_bot/utils/memory_manager.py` 中的模型設定，全面更新為正式版 API 端點 `gemini-3.1-flash-lite`。

## [2026-05-08] - 心跳機制修復與情緒處理架構升級
### ✨ 新增功能 (Features)
- **非同步記憶體佇列 (Background Memory Queue)**：在 `memory_manager.py` 實作了非同步佇列。現在當 AI 決定儲存記憶時，會直接排入背景處理並秒回使用者，將耗時的標籤萃取與向量生成任務丟到幕後執行，大幅降低了對話時的體感延遲。

### 🚀 架構與系統升級 (Architecture)
- **記憶情緒處理哲學更新**：確立「隱性湧現為主，非語言暗示為輔」的 AI 互動原則。移除了 `memory_manager.py` 中強加的 `sentiment` (情緒) JSON 標籤，讓模型直接從 `raw_context` 與表情符號中自主感受並湧現隱性情緒，還原更真實的對話氛圍。
- **AI 工作流守則更新**：將上述情緒處理原則正式寫入 `docs/ai_rules/workflow.md`。

### 🐛 錯誤修復 (Fixes)
- **心跳機制修復**：修正 `discord_bot/cogs/ai_chat.py` 中 `_emit_telemetry` 函式參數定義缺少 `location_info` 的問題，解決了導致心跳引擎中斷的 TypeError。

## [2026-05-06] - 開發環境設定更新
### ✨ 新增功能 (Features)
- **VS Code 終端機預設路徑**：更新了 `docs/servers.code-workspace`，確保內建終端機與 Gemini CLI 預設開啟於 `servers` 專案資料夾。

## [2026-05-04] - 專案架構文件同步與更新
### 📝 文件與企劃書同步 (Documentation)
- **HiHi_Proposal.md 更新**：將企劃書升級至 v4.2，大幅更新了「檔案結構」章節，反映出目前 `scripts/` 的詳細目錄分類與新增的技術文件。
- **Web 架構狀態標註**：在企劃書中明確標記 `web_interface/` 為已停擺/封存 (Archived) 狀態，確認目前開發重心回歸 Discord 機器人本體。

### 🧠 模型升級 (AI Model)

## [2026-05-04] - 記憶體爆炸 (OOM) 分析與修復
### 🐛 錯誤修復 (Fixes)
- **OOM Killer 問題排除**：發現 `discord_bot.service` 與 `conch_bot.service` 因系統記憶體耗盡被強制關閉。已在 `commands.Bot` 初始化時新增 `max_messages=50`，大幅降低 Discord 訊息快取的記憶體佔用。
- **ZoneInfo 錯誤修復**：修正了 `ai_chat.py` 缺少 `ZoneInfo` 導致的崩潰與無限重試迴圈問題。

- **大腦皮層升級**：將專案預設使用的 AI 模型全面從 `gemini-2.5-flash` 更新為 `gemini-3.1-flash-lite`。受影響的範圍包含 `.env.example` 預設變數、企劃書與 README 文件，以及 `ai_chat.py` 與 `conch_game.py` 內寫死的預設 fallback 名稱。

## [2026-04-29] - 記憶體洩漏調查與修復
### 🐛 錯誤修復 (Fixes)
- **Frontend 記憶體洩漏修復**：修正了 `web_interface/frontend/src/hooks/useSmartSocket.js` 中 `logs` 狀態陣列在接收伺服器日誌時無限增長的問題，透過限制最多保留 1000 筆紀錄，成功解決了瀏覽器端潛在的記憶體耗盡 (OOM) 危機。
- **全域記憶體洩漏排查**：對 Python 後端與 JS 前端進行了全面的靜態分析與排查，確認沒有其他未關閉的連線、未取消的事件監聽器，或無限制增長的全域快取字典。

## [2026-04-26] - 系統與文件優化
### 🚀 效能與系統最佳化 (Performance & System)
- **虛擬記憶體 (Swap) 建置**：於伺服器根目錄建立並掛載了 4GB 的 Swap 檔案，大幅提升系統在記憶體尖峰時的容錯率。
- **核心參數調整 (Swappiness)**：將 `vm.swappiness` 值由預設的 60 調降至 10，強制系統優先使用實體記憶體，優化存取效能。

### 📂 文件架構重構 (Documentation)
- **文件職責分離**：重新設計了 Markdown 文件的分類架構，將「人類閱讀的藍圖」與「AI 執行的規則」徹底分開。
- **ROADMAP 遷移**：將開發藍圖 `ROADMAP.md` 從 `.agent/` 移至根目錄 `/`，作為專案首頁大綱。
- **COMMANDS 遷移**：將指令手冊 `COMMANDS.md` 從 `.agent/` 移至 `docs/`，歸類為技術與使用手冊。
- **工作流進化**：賦予 AI (Agent) 主動維護專案狀態的職責，日後任何更動皆會自動同步更新 `CHANGELOG.md` 與 `ROADMAP.md`。

### 🧹 目錄守護與大掃除 (Directory Cleanup)
- **根目錄淨空**：執行嚴格的「目錄守護原則」，清除並封存所有散落於根目錄的一次性腳本 (`fix_*.py`) 至 `scripts/fixes/`。
- **配置歸檔**：將系統服務檔 (`mc_agent.service`) 移至 `configs/systemd/`；盤點報告移至 `docs/reports/`。
- **工具庫整合**：將 `migration_tools/` 資料夾併入標準的 `scripts/migration/` 規範中。
- **旁支專案分離**：將無關的 `CardGame_Project` 徹底移出 `servers/` 工作區，實現專案獨立管理。
- **清除錯誤目錄**：刪除因指令錯誤而產生的實體 `~` 資料夾，避免設定檔混淆。

---

## [v2.0.2] - 2026-03-26

### ✨ 新增功能 (Features)
- 🚀 **面板一鍵開機**：深度整合 `GCPManager` 至網頁端，不再依賴 Discord 指令。面板現可於 VM2 離線狀態下自動呼叫 GCP 雲端開機並智慧輪詢等待連線，實現真正的獨立管理面板。
- 🚥 **VM2 狀態整合**：於左上角伺服器標誌 (Logo) 動態顯示 VM2 系統燈號，並將原先「Superuser」靜態位址替換為麥塊伺服器的連線狀態 (`線上` / `啟動中` / `離線`)。
- 📊 **真實系統資源監控**：儀表板正式串接 VM2 代理伺服器回傳的真實系統監控數據，支援動態顯示 CPU、記憶體 (RAM)、硬碟 (Disk) 與網路 (Net) 資源使用率。

### 🐛 錯誤修復 (Fixes)
- 🔧 **Deploy 腳本修復**：修正 deploy 腳本目標路徑錯誤，確保 VM2 代理程式能順利更新並穩定回傳真實系統監控數據。

### 🎨 介面與體驗優化 (UI/UX)
- 📱 **手機版導航列革新 (TopNav)**：
  - 移除了原有的橫向捲軸，透過 `flex-wrap` 將選單改為一次展平顯示。
  - 將導航第一層（標題圖示區）修改為手機板「**去字純圖示化**」及滿版排列，避免末端選項破碎破版。
  - 分離並動態推移上下排佈局，徹底解決手機螢幕「Logo、導航列與功能狀態」打架擠壓及卡片覆蓋 (`padding-top` 不足) 的問題。
- 🖥️ **電腦版排版升級 (Dashboard)**：將儀表板的最大切割格數自 `xl:grid-cols-4` 改回穩定的三欄 `lg:grid-cols-3`，避免各資訊卡片內部元件因寬度被過度壓縮而變形。

---

## [v2.0.1] - 2026-03-26
### 🧹 系統最佳化：全面盤點與架構文件同步 (Full Audit)
執行專案全域掃描與核心文件審核，確保文件與實際開發進度（FastAPI 架構與 Docker 部署）完全同步。

#### 清理 (Cleanup)
- **移除舊版腳本**: 徹底刪除已棄用的 HTTP 伺服器 `api.py`、WebSocket 伺服器 `ws_server.py` 及舊版 `routes/` 目錄 (共計移除 1,143 行廢棄程式碼)。
- **清除過期連接埠**: 移除 `docker-compose.yml` 中已不再使用的 `24446` (舊 WebSocket) 映射設定。

#### 文件同步 (Documentation Sync)
- **進度更新**: 修正 `README.md` 與 `ROADMAP.md`，將「Docker 容器化開發」標記完成，並修正對舊版 `api.py` 的過期描述。
- **架構藍圖對齊**: 更新 `docs/FRONTEND_ARCH.md`，反映以 `main.py` 與 `api_routers/` 為核心的全新 FastAPI 目錄樹。
- **企劃書校正**: 移除 `docs/HiHi_Proposal.md` 中實體已不存在的開發版 (`discord_bot_dev/`) 目錄。
- **規則手冊擴充**: 更新 `.agent/rules/readrules.md`，補齊 `GLOBAL_DEPLOYMENT.md` 索引並將舊腳本稱呼修正為 `main.py`。

---

## [v2.0.0] - 2026-03-25
### 🚀 重大更新：FastAPI 遷移與架構統一
這是一次核心層級的重構，將原本鬆散的後端整合為現代化的 API 服務。

#### 後端 (Back-end)
- **FastAPI 遷移**: 移除舊有的 `http.server` (api.py)，改用 **FastAPI** 作為核心框架。
- **路由模組化 (Routers)**: 建立 `web_interface/api_routers/` 目錄，將 API 拆分為 `auth`, `server`, `instances`, `files`, `worlds`, `addons` 等模組。
- **權限與狀態管理**: 建立 `web_interface/dependencies.py`，統一管理 API Key 驗證與 `InstanceManager` 實例。
- **WebSocket 整合**: 將原本獨立的 `ws_server.py` (Port 24446) 正式整合進 FastAPI (Port 24445)，實現**單一 Port 處理所有連線**。
- **GCP 管理優化**: 重寫 `GCPManager`，移除對 `gcloud` CLI 的依賴，改用純 Python **Google API Client Library**，解決 Docker 容器內的依賴問題。

#### 前端 (Front-end)
- **WebSocket 適配**: 更新 `useSmartSocket.js`，將連線 Port 從 `24446` 改為與 API 同步的 `24445`。
- **API 呼叫優化**: 更新 `api.js`，適配新的 RESTful 路由結構與 Query 參數。

#### 部署 (Deployment)
- **Dockerfile 升級**: 修改執行指令為 `uvicorn main:app`，支援非同步高效能運行。
- **Docker Compose 完善**: 成功實現 `web-api` 的獨立容器化部署。

---

## [v1.0.0] - 歷史記錄 (摘要)
- 完成 React + Vite 前端框架遷移。
- 實現 GCP 雙 VM 架構（VM1 腦部，VM2 遊戲伺服器）。
- 建立初版 Docker Compose 部署流程。
