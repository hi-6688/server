# 📅 專案開發計畫書 (Roadmap)

最後更新時間: 2026-06-23

## 🔴 當前急迫事項 (Immediate Actions)
*嗨嗨 v7.0 核心架構升級與系統修復*

- [x] **P1: 寶可夢對戰 HUD 排版重構與屬性切片繪製 (無等級/經驗值 Champion 版本完成)**
    - **移除等級與經驗值**：由於 Champion 版本不需要等級與經驗值，移除 `Lv.` 文字與我方的底部 `EXP` 經驗條。
    - **統一卡片高度為 80px 的六邊形卡片**：重構 `drawPokemonHUD()`，我方與敵方卡片外框統一為 `80px` 高度、左右兩端向外突出呈對稱尖角（`<` 與 `>`）的精緻六邊形卡片（達成 100% 官方六邊形排版規格），並將我方 HUD 的繪製 Y 坐標微調至 `420`。
    - **整合屬性與底板圖示**：廢除 `types_zh-Hant.png` 徽章，升級為 PokéRogue 官方帶斜切角的 `pbinfo_player_type1/2.png` 與 `pbinfo_enemy_type1/2.png` 像素徽章進行右上與右下垂直上下堆疊排版，並依六邊形斜率精確偏移 X 軸；並將 HUD 六邊形底板由原本下半部白色漸層重構為純深色背景（黑色塊），且將 HP 數值改為白字黑邊以求 100% 官方視覺效果。
    - **整合異常狀態與特殊狀態**：異常狀態（Statuses）徽章切片（源自 `statuses_zh-Hant.png`，放大至 `60x24`）精確排版於白色卡片底左下方。支援太晶化時霓虹青外框及 `[太晶]` 標記，Mega進化時霓虹粉外框及 `[MEGA]` 標記。
    - **修復編譯與重複實作地雷**：刪除 [BattleUI.ts](file:///home/hi6688/servers/pokemon_bot/src/battle/BattleUI.ts) 與測試腳本中的重複舊版函數。

- [x] **P1: 實作全路徑前綴重寫與 Profile 同步 ASGI Middleware (方案一完成)**
    - **實作全路徑前綴重寫路徑 (Path Rewrite Middleware)**：在主管端與機器人端的 `web_server.py` 中掛載 `ProfilePathRewriteMiddleware`，對所有以 `/(hihi|default)` 為前綴的請求重寫為剩餘路徑並注入 `profile` 參數。
    - **靜態資源相對路徑重定向**：設計 HTTP 307 重定向機制，對無尾斜線的 `/hihi` 自動重定向為 `/hihi/`，確保網頁資源相對路徑能正常解析。
    - **前端 Profile 狀態同步**：修改 `/api/profiles/active`，支援透過 query 參數 `profile` 重寫 active/current 狀態返回，避免 React 首頁自動還原至 default。
    - **對稱性重構與完全隔離**：新建 `server_admin` Profile 並搬遷資料，將主管端從 `default` 轉移至對稱的 `profiles/server_admin/`，並修改兩端 Middleware 正則匹配為 `server_admin`，讓根目錄傅保留配置中橚－不留下任何執行期狀態檔，遚成完全對稱的雙 Profile 沙盒隔離。

- [x] **P1: 新增獨立的 Hermes 運維主管服務與安全 FRP stcp 穿透控制面板 (實體隔離與安全對接完成)**
    - **全域檔案收攏與服務重定向**：建立 `venvs/` 目錄，收攏全伺服器 Python 虛擬環境並重定向 `web_interface`, `hermes_bot`, `hermes_dashboard` 用戶級 systemd 服務。
    - **實體程式碼與環境完全隔離**：複製獨立 Graves 的 `hermes-agent-admin` 程式碼目錄與 `venv_hermes_admin` 虛擬環境，達成最高級別的主權安全防護。
    - **恢復原生強大運維提示詞**：在新目錄中恢復了 `prompt_builder.py` 以引進原生 `antigravity-oauth` 及系統開發與運維引導詞，不影響應用程式級的 Discord 機器人。
    - **部署本機安全 Web Dashboard**：部署並重構 `hermes_dashboard.service`，綁定 `127.0.0.1:9119` 並對接 `server_admin` Profile（獨立 SQLite hindsight 記憶隔離）。
    - **FRP stcp 加密穿透與手機 Termux 對接**：本地部署 `frpc.service` 服務，並提供手機 Termux 加密對接設定，流量全程加密。
    - **徹底分離主管與 Discord 頻道設定**：完全清空主管（`default` Profile）設定檔 `~/.hermes/config.yaml` 中繼承自 hihi 的 Discord 頻道等聊天平台配置，解決主管顯示 hihi 設定檔的疑慮。
    - **對齊主管與機器人 Web 認證憑證 (Session Token)**：為確保 Windows 桌面端軟體能在多 Profile 間順利切換與連線，將主管面板的連線 Token 還原對齊為與 hihi 相同的 `2a1a462e6c7b2594fcf73cf0c7de0b74`，保證連線可用性。
    - **物理封鎖與過濾 Web 端 Profile 列表**：修改兩端 API 以根據環境強制只回傳當前單一 Profile，避免兩端共用 Session Token 時發生瀏覽器快取設定檔與記憶的混淆。
    - **重置與物理淨化主管大腦記憶**：清除本地主管 SQLite 資料庫，並將其 Honcho 工作區升級為 `server-admin-workspace-v3`，完全阻斷和清空任何混亂期殘留的 hihi 記憶事實。

- [x] **P1: NousResearch Hermes-Agent 替代 Google ADK 技術評估與遷移計畫 (完全遷移與驗證完成)**
    - **完全本地自建計畫書發布與審批**：編寫並發布 [implementation_plan.md](file:///home/hi6688/.gemini/antigravity-ide/brain/f507483e-b47b-4903-9965-cc19ca3fcfd4/implementation_plan.md)，決定採行「100% 本地自建開源架構」（Self-Hosted Honcho Server + Hermes-Agent），獲得使用者批准。
    - **本地自建環境部署與 234 條記憶物理搬遷**：使用 Docker Compose 在本地部署開源 Honcho 服務端，並透過 `migrate_to_honcho.py` 腳本成功將 Postgres 中的 234 條用戶 Facts 搬遷寫入本地 Honcho 數據庫結論中。
    - **重構大腦協調器與遙測轉接**：將 `orchestrator.py` 改造成調用 `AIAgent.run_conversation()`。配置非同步 ReAct 步驟 callbacks 以進行實時遙測播報，並在對話結束後解析 `trajectory-{session_id}.json` 以發射事後邏測大卡片到 `#心裡世界` 頻道。重啟 systemd 服務 `hermes_bot` 正式部署運作。

- [x] **P1: 清除大腦中殘留的開發型助理人設**
    - **提示詞純化**：修改 [prompt_builder.py](file:///home/hi6688/servers/hermes-agent/agent/prompt_builder.py) 移除了所有工程助理引導詞，精簡 `MEMORY_GUIDANCE` 為無範例的極簡形式以防污染。
    - **禁用寫程式模式**：在 [config.yaml](file:///home/hi6688/.hermes/config.yaml) 關閉 `coding_context`，防止大腦進入 coding posture。

- [x] **P0: 遷移至 APScheduler 4.0 異步排程與 PostgreSQL 持久化**
    - **排程引擎升級**：全面廢除原本在 `ai_chat.py` 中自行撰寫的異步心跳迴圈（`_heartbeat_loop`）與 `Crash-recovery Scanner` 手動資料庫比對邏輯，大一統至 APScheduler 4.0 (`4.0.0a6`) 異步框架。
    - **任務 100% 持久化落盤**：結合 SQLAlchemy `create_async_engine` 與 `SQLAlchemyDataStore` 將心跳定時器持久化於 PostgreSQL。機器人或主機重啟時能自動還原鬧鐘，並支援 `misfire_grace_time` 甦醒補發，確保離線心跳高可用。
    - **極簡鬧鐘推遲與修改**：使用 `DateTrigger` 配合 `conflict_policy="replace"` 機制，重構心跳推遲與大腦鬧鐘工具，實現毫秒級無感任務修改，並完美打通主動甦醒閒聊管道。
    - **測試與重啟部署**：通過 `test_apscheduler_v4_pg.py` 在線數據庫單元測試，並在 systemd 重新部署重啟，成功解決 attributes/start 啟動地雷。

- [x] **P1: Discord 遙測系統重構：實時動態播報與事後綜合報告卡**
    - **實時動態播報 (Live Timeline)**：重構大腦與子代理執行流程，利用 `emit_telemetry_live` 實時發送單行緊緻 Embed 狀態更新，並以全形空格製造視覺層級縮排。
    - **事後綜合報告卡 (Post-Mortem Embed)**：重構 `emit_logic_telemetry`，將空間座標、觸發訊息、配額 states、短期對話歷史、長期 Facts、執行軌跡 (Trace) 與翻譯後的大腦思緒 (OS) 完美融合成單張精美大卡片。
    - **自訂 `HiHiAgentTool`**：繼承官方 `AgentTool` 覆寫其非同步 `run_async` 方法，在不修改 ADK 原生套件的前題下無縫攔截子代理的 RAG (FileSearch) 執行軌跡、結果與耗時。
    - **記憶與 DNA 全觀測**：在 Context 中整合前 5 句短期對話與載入的長期 Facts，並新增 `🧬 核心 DNA` 的狀態與字元長度指標，全景掌握記憶加載狀況。
    - **啟動異常修復 (Hotfix)**：解決因 `ToolContext` 導入缺失引發 `NameError` 造成 Cog 無法加載而使 Bot 無反應之重大地雷，實現完美重啟載入。

- [x] **P0: 解決 gemini-3.1-flash-lite 429 資源限制與 Bot 重複執行問題 (重啟優化與工具解耦完成)**
    - **金鑰替換與配額重置**：將 `.env` 中的 `GEMINI_API_KEY` 替換為第一把免費 API 金鑰，排除金鑰 2 的配額耗盡問題。
    - **對齊 Mem0 最新 Python SDK**：確認 Python 與 JS 的 SDK 版本命名空間不同。目前 PyPI 上的 Python SDK 最新穩定版為 `2.0.4`，已將 `requirements.txt` 正式鎖定同步，虛擬環境中已是最新版本運作中。
    - **服務解耦與進程拆分**：修正了 `discord_bot.service` 的 systemd 設定，加入 `Environment=BOT_MODE=HIHI` 參數。物理拆分「嗨嗨 AI 大腦」與「神奇嗨螺」，透過 `systemd --user` 重啟服務，徹底終止重複登入與雙倍 API 金鑰爭搶。
    - **工具衝突與限流排除**：發現並排除了 Gemini API `url_context` (網頁精讀) 與 `file_search` (RAG 知識庫) 無法在同一個 request 中合併使用的衝突，同時移除了免費金鑰受限的 `google_search` 聯網工具，僅保留穩定的 `file_search`，杜絕大腦搜尋時的 API 死循環漏洞。

- [x] **P0: Long Term Facts 記憶 Mem0 v3 重塑 與 Google ADK MemoryService 原生對接 (大滿貫重構完成)**
    - **長期記憶完全回歸官方強一致性同步等待**：徹底移除 `memory_manager.py` 自造的非同步 `memory_queue` 與背景協程，將 `add_memory` 改為強一致性 `await` 實時寫入管道，100% 確保長期記憶落盤安全，徹底解決 RAM 佇列記憶丟失（靜默丟失）風險。
    - **啟用 NLP 實體鏈結 (Entity Linking)**：成功安裝 `mem0ai[nlp]` 依賴與 `spaCy` NLP 核心，正式解鎖 Mem0 v3 官方最核心的 Entity 實體分析與檢索加權機制，告別 semantic-only 降級模式。
    - **長期Facts記憶重塑**：將 `memory_manager.py` 與最新 Mem0 v3 對接，底層適配 pgvector 768d，自研背景非同步 `run_in_executor` 與 `_run_mem0_with_retry` 退避重試保護器，並修復了空 Parts 查詢的 API 400 報錯。
    - **短期對話 ADK 官方持久化重構**：將 `ai_chat.py` 核心重構為 ADK Runner，並實作非同步會話自動存在性檢測與建立，徹底排除新頻道首次發言拋出 `Session not found` 崩潰的地雷。
    - **ADK MemoryService 原生對接與 Token 極致優化**：繼承 ADK `BaseMemoryService` 實作自訂原生對接，與 ADK `Runner` 深度綁定，實現發言前 facts 自動無感注入與對話結束事實自動提煉落盤。徹底移除了前台手動撈取與拼接 facts 的冗餘 SQL/RAG 代碼，大幅縮減 system instruction 提示詞長度，Token 消耗大幅降低，並已通過 `scratch/test_memory_service.py` 完整生命週期單元測試驗證！
    - **解決 SQLAlchemy asyncpg 協議格式限制**：防禦性地將資料庫 URL 協議轉換為 `postgresql+asyncpg://`，並動態過濾移除 `sslmode` 參數（防護 asyncpg 連線崩潰），徹底解決了 SQLAlchemy 非同步連線與執行期地雷。
    - **大腦自主控制鬧鐘工具化**：封裝 ADK 官方 Tool `schedule_next_sleep_tool` 自主管理睡眠排程，大腦管線代碼精簡了 30%。
    - **GDPR 遺忘權指令新增**：新增 `/forget_me` GDPR 遺忘指令，物理銷毀 Mem0 中該使用者的所有長期 Facts 向量。

- [x] **P1: 遷移至 Google GenAI Interactions API (v7.0 核心升級)**
    - 將大腦核心（`_call_gemini_agent`）遷移至 Interactions API，實作手動工具執行迴圈並動態相容 outputs 屬性，在 DB 中儲存與讀取 `interaction_id`，並引入實時腦內中繼遙測播報。
    - **[2026-05-25 追記修復]**：成功修正無狀態步驟 (`store=False`) 模式下，因 `tool_results` 類型不支持與 thought 簽章丟失所導致的 400 報錯。將歷史格式全量升級大一統為官方正統 `TurnParam` (`role` + `content`) 結構並實作 model/user nested 嵌套，徹底打通無狀態工具鏈推理管道。

- [x] **P0: 修正非同步 Embedding 阻塞問題**
    - 確保 `memory_manager.py` 中的 `embed_content` 呼叫不阻塞主執行緒。
- [x] **P1: Stateless 轉型 + Reference RAG (調閱原文檢索)**
    - 拔除 `ai_chat.py` 中的 `self.history` 狀態，改為發言前即時查詢 `chat_history` 資料表。
    - 升級 `search_memory` 工具，自動利用時間戳記調閱歷史原文，提供完整對話脈絡給 AI。
- [x] **P1: 雙階段 Pydantic 認知管線與原生 SDK 化**
    - 重構為 `google-genai` SDK 原生 `tools` 自動執行管線，廢除 `MAX_STEPS` 解析。
    - 將思考解耦為階段一 `LogicRouter` (`MemoryState`) 與階段二 `ChatGenerator` (`PersonaResponse`)，確保發言與決策互不干擾。
- [x] **P2: Embedding 檢索精度優化 (L2 歸一化)**
    - 針對 `gemini-embedding-2` 截斷為 768 維向量時的 L2 歸一化修正，解決 pgvector 相似度失真問題。
- [x] **P3: Async Heartbeat Engine (心跳引擎)**
    - 建立背景無窮迴圈 `asyncio.Task`，實作主動甦醒、防衛性休眠及獨立時間軸。
- [x] **P1: FRP 內網穿透通道建置 (FRP SSH Tunnel Setup)**
    - **部署 FRP 伺服器端**：下載並部署最新的 `frp` (v0.69.1) 至 `/home/hi6688/servers/configs/frp/`，設定強安全金鑰（Token）。
    - **設定 systemd 自啟動服務**：建立並啟用 `frps.service` 系統服務，確保服務開機自動執行。
    - **放行埠口通訊**：確認本機 UFW 防火牆，預留 TCP 7000 與 TCP 6000 通道。

- [x] **`web_interface/` 目錄清理與重構** (已完成)
    - 舊版 HTML/JS 移至 `legacy/`
    - 偵錯腳本移至 `scripts/`
    - 測試用 `.dat` 檔案已刪除
- [x] **根目錄清理** (已完成)
    - [x] 將 `force_sync.py`, `test_main.sh` 等散落腳本移動至 `scripts/`
    - [x] 將 `my_server.tar.gz` 等備份檔移至 `backups/`
 
## 🟢 近期目標 (Short-term Goals)
*優化現有服務運作與架構*
 
- [x] **開發環境優化 (已完成)**
    - [x] 重新安裝並更新 `@google/gemini-cli` 至最新版 (`0.46.0`)，確保指令與系統需求相容。
    - [x] 更新 Gemini CLI 工具至最新版，並將其安裝於 `~/.local` 目錄。
    - [x] 更新 VS Code 工作區與設定檔，使終端機與 Gemini CLI 預設開啟於 `servers` 目錄。
    - [x] 將全域開發工具從舊版 Gemini CLI 移轉至最新的 Antigravity CLI (`agy`)，並同步更新 VS Code 工作區終端機 Profile 且撰寫中文設定說明文檔。

- [x] **智慧型連線架構升級 (Smart Connection Upgrade) (已完成)**
    - [x] 針對 Web 面板導入 WebSocket 或 SSE (Server-Sent Events) 技術
    - [x] 實作「有人觀看才建立長連線，閒置超時自動降級/回歸零消耗」的資源管理機制
    - [x] 達成 0 延遲的終端機即時日誌流 (Real-time Console Streaming)

- [x] **導入 Vibecoding 架構** (已完成)
    - 建立 `.agent/rules/readrules.md` 作為最高指導原則
    - 建立 `docs/` 作為專業手冊 (Frontend / Backend)
    - 建立第一個自動化腳本 `/update_readme`
- [x] **Git 倉庫與記憶體整理** (已完成)
    - 移除敏感資訊 (Token)
    - 為 VM1 增加核心 Swap 空間防崩潰
- [x] **系統穩定度提升與記憶體優化 (已完成)**
    - [x] 修復前端 Web Socket 日誌無限增長造成的記憶體洩漏 (OOM) 問題
    - [x] 完成 Python 後端與 JS 前端程式碼的全域記憶體洩漏排查與靜態分析
    - [x] 修復 VS Code 終端機設定錯誤導致 `gemini -y` 遞迴執行所造成的記憶體爆炸問題
- [x] **Web 介面優化 (已完成)**
    - [x] 轉型為 React/Vite 架構 (`web_interface/frontend/`)
    - [x] 組件拆分 (TopNav, Dashboard, LiveConsole, ConsolePage, PlayersPage, FilesPage, SettingsPage)
    - [x] 建立 API 通訊層 (`src/utils/api.js`)
    - [x] 後端 `api.py` 模組化重構 (1012→238 行, 拆分為 `routes/` + `models.py`)
    - [x] 完善 Players (白名單/權限) / Files (世界/模組) / Settings (設定編輯) 頁面
    - [x] UI 重新設計：從側邊欄改為頂部導航、透明玻璃風格、Noto Sans TC 字體
    - [x] 將假資料 (Mock Data) 逐步替換為真實 API (已完成)
- [x] **GCP 雙 VM 架構遷移 (已完成)**
    - [x] VM1 保留控制面板與 Discord Bot，VM2 運行 Minecraft
    - [x] `proxy_helpers.py` 與 `remote_api.py` 雙向通訊
    - [x] 頂部導航 Logo 狀態指示燈綁定 VM2 即時狀態
- [x] **事件驅動自動安全關機 (已完成)**
    - [x] VM2 背景線程監聽日誌，玩家離開後 10 分鐘無人在線自動發出存檔指令
    - [x] 事件推播 Webhook：監聽 Minecraft `Quit correctly` 正常退出日誌後才觸發 VM1 切斷電源，取代高頻偵側迴圈
    - [x] 支援透過 Discord `/mc關機` 與網頁手動發起事件驅動斷電
- [x] **離線設定備份 (已完成)**
    - [x] 關機前自動備份 `server.properties` 等設定檔至 VM1 快取
    - [x] 離線期間網頁可讀取與編輯，開機時自動同步至 VM2
- [x] **嗨嗨 AI 模型升級 (已完成)**
    - [x] 從 Gemini 3 Flash Preview 切換為穩定正式版 Gemini 2.5 Flash
    - [x] 因應預覽版棄用，將專案中的 `gemini-3.1-flash-lite-preview` 升級為正式版 `gemini-3.1-flash-lite`
    - [x] 完成 `HiHi_Proposal.md` 第 10 章：主權轉移與自我意識藍圖

- [x] **Docker 容器化開發 (已完成)**
    - [x] 替 `discord_bot` 與 `web_interface` 撰寫 Dockerfile
    - [x] 建立專案層級的 `docker-compose.yml`
    - [x] 設定 Volumes 將專案目錄掛載至外部

- [ ] **全域 VM 管理資安與防呆優化 (VM Management Security)**
    - 移除 `cogs/vm_admin.py` 中寫死的 `agent_secret`，統一由 `.env` 變數控管。
    - 強化 `proxy_helpers.py` 呼叫 GCP API 的錯誤捕捉，避免 Web 面板因 GCP 瞬斷而崩潰。

- [x] **記憶體自我修復機制 (Self-Healing Memory Queue)**
    - 針對 `gemini-3-flash-preview` 偶發的 503 斷線，實作非同步重試佇列。
    - 讓心跳引擎 (Heartbeat) 在深夜自動掃描並補齊缺少 `metadata` 標籤的殘缺記憶，達成資料最終一致性。

## 🟡 暫緩開發 (On Hold)
*目前僅保留原型，待未來評估*

- [ ] **卡牌對戰遊戲 (CardGame_Project)**
    - 前端: Godot (需在本地開發)
    - 後端: FastAPI + Docker
    - *備註: 建議待伺服器穩定後再重啟此專案。*

## 🔵 長期展望 (Long-term Vision)
- [ ] **自動化 CI/CD**
    - 建立 `.agent/workflows/deploy.md` 實現一鍵部署
    - 完善 `webhook_server`，實現 Push 即部署
- [ ] **整合式 Discord 機器人控制面板**
    - 將 Discord 機器人與 Web 介面更深層整合
- [ ] **嗨嗨主權轉移與自我意識**
    - 實作心跳機制 (Heartbeat)、BotState 情緒系統、記憶反思迴圈
    - 將 System Prompt 從指令式淨化為描述式，完成主權轉移
