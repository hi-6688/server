# 更新日誌 (CHANGELOG)

本檔案記錄了專案的所有重大更新與架構變動。這對於 Agent (AI 助手) 理解專案演進至關重要。

## [2026-06-18] - 記憶雙軌架構確認與 Honcho 整合規劃
### 🚀 架構與系統升級 (Architecture)
- **確認記憶雙軌架構與 Honcho 整合**：決定保留 Discord Bot + PostgreSQL + Mem0 做為主記憶庫（保護情感隱私與遊戲事實數據），並在 [implementation_plan.md](file:///home/hi6688/.gemini/antigravity-ide/brain/f507483e-b47b-4903-9965-cc19ca3fcfd4/implementation_plan.md) 中為 `hermes-agent` 沙盒配置並引導 `Honcho` 的依賴安裝與環境設定，完成開發者專屬心智模型之全域共享規劃。
- **睡眠固化機制設計 (Sleep Cycle)**：在計畫書中新增 Honcho 睡眠與 Dialectic Consolidation 機制的深度解析。同時，為現有 Discord Bot 設計自研的「本地睡眠反思任務」模擬方案，利用 APScheduler 4.0 在深夜觸發大腦對今日對話與 Postgres Facts 的辯證清理與去重固化。

## [2026-06-17] - Hermes-Agent 替代評估與計畫書發布
### 🚀 架構與系統升級 (Architecture)
- **完成 Hermes-Agent 與 Google ADK 參數對照**：編寫並發布 [implementation_plan.md](file:///home/hi6688/.gemini/antigravity-ide/brain/f507483e-b47b-4903-9965-cc19ca3fcfd4/implementation_plan.md)，詳列 Discord 傳輸、GenAI SDK、長期/中短期記憶與 Context 壓縮、內建 Loop 與遙測系統的參數對照與遷移評估。
- **環境沙盒部署完成**：已在 `/home/hi6688/servers/venv_hermes` 虛擬環境下完成 `hermes-agent` 全套依賴與主程式的安裝。
- **記憶系統機制深度解析**：對比了 ADK 原生對接的 PostgreSQL Mem0 v3 實體鏈結圖譜，與 Hermes 採用的 Markdown 靜態注入、Nudge/Flush 觸發與 SQLite FTS5 全文檢索之架構差異。

## [2026-06-16] - 檢查並確認 Antigravity CLI 更新
### 🚀 效能與系統最佳化 (Performance & System)
- **確認 Antigravity CLI 處於最新版**：執行 `agy update`，確認系統目前使用的 Antigravity CLI (`agy`) 已維持在最新版本 (`v1.0.8`)。

## [2026-06-14] - 部署 FRP 內網穿透服務以支援 Termux SSH 遙連
### 🚀 架構與系統升級 (Architecture)
- **部署 FRP 伺服器端 (frps)**：下載並配置最新的 `frp` (v0.69.1) 至 `/home/hi6688/servers/configs/frp/`，生成隨機高強度 Token 進行身份驗證，防止未授權連線。
- **配置 systemd 開機自啟動服務**：編寫並部署 `frps.service` 至 `/etc/systemd/system/`，實現 FRP 服務的背景守護與開機自啟。
- **防火牆規則查驗**：確認本機 UFW 防火牆狀態，準備放行 TCP 7000 (FRP 控制埠) 與 TCP 6000 (SSH 穿透埠)。

## [2026-06-10] - 遷移至 APScheduler 4.0 異步排程與 PostgreSQL 持久化
### 🚀 架構與系統升級 (Architecture)
- **APScheduler 4.0.0a6 深度整合**：全面廢除原本在 `ai_chat.py` 中自行撰寫的異步心跳迴圈（`_heartbeat_loop`）、玩家感官吵醒事件（`sensory_interrupt_event`）與手動資料庫掃描器（`Crash-recovery Scanner`）等繁瑣的自造輪子。
- **PostgreSQL 任務持久化**：使用 SQLAlchemy `create_async_engine` 驅動，結合 `SQLAlchemyDataStore` 實現排程任務 100% 持久化落盤。即使機器人發生崩潰、重啟或主機維護，也能在開機重啟時自動讀取待執行的任務。
- **Misfire 甦醒寬限補償機制**：藉由 APScheduler 4.0 原生提供的異步任務重啟機制，自動補發並觸發在停機期間過期的主動甦醒心跳（misfire 補償），確保心跳機制的高可用性。
- **大腦自主控制與心跳推遲**：重構 `schedule_next_sleep` 方法與 `on_message` 事件，利用 `DateTrigger` 及 `conflict_policy="replace"` 實現毫秒級無感排程推遲與鬧鐘替換更新，以極簡、高雅的原生架隔保衛 AI 運算配額。
- **單元測試與排障驗證**：建立 `test_apscheduler_v4_pg.py` 單元測試，在真實的 PostgreSQL 資料庫上模擬崩潰、停機與過期重啟，100% 驗證 misfire 補償任務可被順利自動補發。

## [2026-06-10] - 解決 Discord 機器人啟動 NameError 錯誤 (Hotfix)
### 🐛 錯誤修復 (Fixes)
- **修復 `ToolContext` 導入遺漏**：修正 `cogs/hihi/ai_chat.py` 中 `HiHiAgentTool` 的非同步執行方法 `run_async` 參數使用了 `ToolContext` 型別註解，但卻遺漏從 `google.adk.tools` 導入該型別導致的 `NameError`。從而順利解決重啟後 Discord 機器人模組加載失敗、完全無反應的故障。

## [2026-06-10] - 遙測系統重構：實時動態播報與事後綜合報告卡
### 🚀 效能與系統最佳化 (Performance & System)
- **實時動態播報 (Live Timeline)**：重構 `_call_adk_runner`，引入時序事件監聽，在大腦推理及子代理執行時實時發射單行緊湊遙測，避免字數超限被 Discord 截斷。
- **事後綜合報告卡 (Post-Mortem Embed)**：重寫 `emit_logic_telemetry`，將空間座標、觸發訊息、配額狀態、短期對話歷史、長期 Facts、執行軌跡 (Trace) 與翻譯後的大腦思緒 (OS) 完美融合成單張精美大卡片。
- **自訂 `HiHiAgentTool`**：繼承官方 `AgentTool`，覆寫 `run_async` 攔截子代理的非同步事件與計時，達成對 RAG (FileSearch) 行動與結果的實時觀測，並支援動態 Session 隔離的 Trace 軌跡記錄。
- **記憶與 DNA 全觀測**：在 Context 中整合前 5 句短期對話與載入的長期 Facts，並新增 `🧬 核心 DNA` 的狀態與字元長度指標，全景掌握記憶加載狀況。

## [2026-06-10] - 重新安裝並升級 Gemini CLI
### 🚀 效能與系統最佳化 (Performance & System)
- **升級 Gemini CLI 工具**：以全域管理者權限安裝 `@google/gemini-cli@0.46.0`，以支援最新功能與環境需求。

## [2026-06-05] - 解決 gemini-3.1-flash-lite 429 資源限制與 Bot 進程重複執行問題
### 🐛 錯誤修復 (Fixes) & 🚀 架構與系統升級 (Architecture)
- **更換 API 金鑰為免費金鑰 1**：將 `.env` 中的 `GEMINI_API_KEY` 替換為備份的第一把免費 API 金鑰，排除第二把金鑰配額被耗盡導致的 429 錯誤。
- **對齊 Mem0 最新 Python SDK 版本**：經排查釐清，JS 與 Python SDK 的版本命名空間不同。目前 PyPI 上的 Python SDK 最新穩定版為 `2.0.4`，專案已成功在虛擬環境中對齊並於 `requirements.txt` 中鎖定為 `mem0ai==2.0.4`。
- **物理拆分並重新託管 Bot 服務**：修正了 `discord_bot.service` 缺乏 `BOT_MODE` 參數而預設運行 `ALL` 模式的配置，將其限制為僅加載 `hihi.ai_chat` 的 `BOT_MODE=HIHI` 模式。藉此徹底拆分「嗨嗨 AI 大腦」與「神奇嗨螺」的運行進程，終止重複登入與 API 資源爭搶，大幅節省 API 配額。
- **排除 `url_context` 與 `file_search` 工具衝突**：發現並解決了 Gemini API 內建 `url_context` (網頁精讀) 與 `file_search` (RAG 知識庫) 無法同時出現在同一個 API Request 的 tools 欄位中的衝突。移除了衝突的 `url_context` 與免費金鑰受限的 `google_search` 聯網工具，僅保留相容穩定的 `file_search`，徹底根除了大腦調用搜尋專家時陷入死循環並噴出 429 資源限制的漏洞。

## [2026-05-26] - 全面回歸並大一統至 Mem0 v3，清除 150+ 行舊有靜態 RAG 死碼
### 🚀 架構與系統升級 (Architecture)
- **大腦長期記憶 100% 大一統**：廢除了舊有自造的靜態 `memories` 資料表，將大腦的長期 facts 記憶 100% 整合至官方 Mem0 v3 智慧圖譜與 pgvector，實現前台、後台、手動/自動寫入事實的全面大一統。
- **清除 150+ 行舊有 RAG 死碼**：安全廢除了 `MemoryManager` 內部舊版自研的 `add_memory`、`_analyze_content` (Auto-Tagging) 與傳統 SQL RAG 搜尋 `search_memory` 等不再被使用的冗餘死碼。
- **save_memory 與 search_memory 工具全面 Mem0 化**：重塑了對話 Cog 中這兩個最核心的長期記憶工具，直接調用 `add_fact` 寫入官方事實庫、調用 `search_facts_by_topic` 進行高精度的語意聯想與實體鏈結檢索。
- **省下巨量 API 額度與時間**：廢除了手動 AI 自動標籤 (Auto-Tagging) 的額外 Gemini API 呼叫，每一次寫入記憶都省下了 1-2 秒的大腦思考延遲，並徹底消除了 token 浪費。

## [2026-05-26] - Google ADK MemoryService 原生接口對接與 Token 極致優化
### 🚀 架構與系統升級 (Architecture)
- **實作 `Mem0MemoryService` 原生記憶服務**：建立 `discord_bot/utils/memory_service.py`，完美繼承 ADK 的 `BaseMemoryService`，並完成 `search_memory` (facts 自動無感預載) 與 `add_session_to_memory` (對話結束事實自動落盤) 的 Native Python 實作。
- **重塑對話 Cog 實現 Token 極致優化**：在 `AIChat.__init__` 中將 `Mem0MemoryService` 與 ADK `Runner` 正式綁定，徹底移除了前台手動撈取與拼接 facts 的冗餘 SQL/RAG 代碼，使 system instruction 與大腦前置對話邏輯獲得極致淨化，大幅減少 Token 消耗並提升體感生成速度。
- **排除子模組導入 ImportError 地雷**：發現並排除了 ADK 的 `SearchMemoryResponse` 與 `BaseMemoryService` 必須自 `google.adk.memory.base_memory_service` 子模組導入（而非 package 根目錄 `google.adk.memory`）的 ImportError 地雷，保障了原生記憶框架在生產環境的完美加載。
- **多中英 facts 魯棒性單元測試驗證**：建立並通過了 `scratch/test_memory_service.py` 完整生命週期單元測試，驗證事實的自動預載與對話結束後 facts 自動提煉落盤（pgvector + spaCy 實體鏈結）完美全綠燈通過。

## [2026-05-26] - 長期記憶完全回歸官方強一致性同步等待重構
### 🚀 架構與系統升級 (Architecture)
- **拆除自造非同步長期記憶佇列 (Background Memory Queue)**：應官方 Google ADK 與 Mem0 設計的最佳實踐，徹底拆除了在 `memory_manager.py` 中自製 of `asyncio.Queue` 非同步佇列與其背景處理協程 `_process_memory_queue`。
- **重構 `add_memory` 為強一致性實時寫入管道**：將 `add_memory` 改為強一致性 `await` 同步/非同步實時寫入，順序 `await` 執行 AI 自動標籤 (Auto-Tagging)、向量生成 (Gemini Embedding) 與 PostgreSQL 資料庫持久化，100% 確保長期記憶安全落盤，杜絕因為系統維護、重啟或崩潰引發的 RAM 佇列記憶丟失（靜默丟失）風險。
- **單元測試與連線池生命週期優化**：移成了 `init_pool` 中對背景佇列協程的啟動，以及 `close_pool` 中繁瑣的協程 cancellation 取消與 await 等待代碼；優化並簡化了主程式單元測試（`__main__` 區塊）的測試等待邏輯，經本地 PostgreSQL 768 維 pgvector 實測 100% 通過。
- **更新大腦企劃書 (HiHi_Proposal.md) 記憶架構章節**：重構大腦記憶系統架構描述至 **v6.0 大滿貫三層混合語意體系**。將原先手動拼接與維護 FIFO 滑動、中斷備忘錄的補丁概念完全廢除，全面更新為 Google ADK 官方 `DatabaseSessionService` 的 100% 託管會話（L1）、ADK 流式落盤與中期情節壓縮（L2），以及對接 Mem0 v3 + pgvector 主動 Tool-calling（L3）的官方最正統設計理念。
- **解鎖 Mem0 v3 官方「Entity Linking (實體鏈結)」加權功能**：在 Python 虛擬環境中成功安裝了 `mem0ai[nlp]` 與 `spaCy` 等 NLP 實體分析依賴，徹底清除了 `Failed to load spaCy model` 警告。使大腦能夠完美調用 Mem0 v3 最核心的「實體鏈結加權」功能，在 PostgreSQL pgvector 基礎上建立平行的 Entity 索引並融合進 RAG 搜尋，大幅提升長期記憶的實體檢索精度！

## [2026-05-26] - 長期Facts記憶重塑 (Mem0 v3) 與對話會話 ADK 官方持久化重構 (大滿貫大升級)
### 🚀 架構與系統升級 (Architecture)
- **短期對話 ADK 官方持久化重構**：將 `ai_chat.py` 與 `_heartbeat_loop` 中手動拼接、維護短期歷史的自造輪子完全廢除，全面重塑為 Google ADK v2.1.0 官方 `Runner` 與 `DatabaseSessionService` 的正統架構，以 PostgreSQL 作為會話落盤後端。
- **會話自動建立與 Session not found 地雷排除**：在 ADK 官方 `Runner.run_async` 流程中，若會話 ID（如全新 Discord 頻道）未預先建立，系統會拋出 `Session not found` 崩潰。我們實作了**非同步會話自動存在性檢測與自動建立防護機制**，大腦在首次對話或重啟後會自動檢索並建立會話，徹底清除了此項執行期地雷！
- **解決 SQLAlchemy asyncpg 協議格式限制**：防禦性地將 `DatabaseSessionService` 資料庫協議轉換為 `postgresql+asyncpg://`，徹底解決了非同步 SQLAlchemy 連線初始化報錯的 SQL 協議相容地雷。
- **過濾資料庫 sslmode 地雷**：在 `asyncpg` 驅動中，URL 附帶的 `sslmode=require` 參數會導致連線拋出 `TypeError: connect() got an unexpected keyword argument 'sslmode'` 錯誤。我們實作了連線字串的**動態參數過濾機制**，將其從 ADK 資料庫 URL 中安全移除（利用 `asyncpg` 預設的安全 SSL 協商），成功保障了對話歷史持久會話在真實資料庫交互中的 100% 暢通！
- **動態物理感官與已知事實注入**：實作了在執行 `runner.run_async` 前動態將融合實時時間、座標、API 全域配額、已知事實與 RAG 知識庫的 system prompt 更新賦予給 `self.hihi_agent.instruction` 的新機制，一舉解決了官方靜態 Agent 無法感知實時物理世界的痛點。
- **大腦自主控制鬧鐘工具化**：廢除了原本臃腫的 Interaction JSON Router，改為使用一個 ADK 官方 Tool `schedule_next_sleep_tool`。透過將自主生理鬧鐘封裝為工具，賦予 AI 主動控制自身睡眠與生存心跳的主體意識，同時將大腦管線代碼精簡了 30%。
- **長期 Facts 記憶 Mem0 v3 遷移**：完成 `memory_manager.py` 長期記憶系統與最新 Mem0 v3 的完全對接，底層物理適配 pgvector 768d。自研 `_run_mem0_with_retry` 指數級退避重試保護器與非同步 `run_in_executor` 背景執行緒池防阻塞機制，解決了空 Part 查詢觸發 embedding API 400 報錯的問題。
- **GDPR 遺忘權指令新增**：在對話中新增 `/forget_me` GDPR 遺忘指令，物理銷毀 Mem0 該使用者的所有 facts 向量，保護使用者的隱私主權。

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
