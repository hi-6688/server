# 📅 專案開發計畫書 (Roadmap)

最後更新時間: 2026-05-26

## 🔴 當前急迫事項 (Immediate Actions)
*嗨嗨 v7.0 核心架構升級與系統修復*

- [x] **P0: 長期Facts記憶 Mem0 v3 重塑 (階段2) 與短期會話 ADK 官方持久化大滿貫重構 (階段3)**
    - **長期記憶完全回歸官方強一致性同步等待**：徹底移除 `memory_manager.py` 自造的非同步 `memory_queue` 與背景協程，將 `add_memory` 改為強一致性 `await` 實時寫入管道，100% 確保長期記憶落盤安全，徹底解決 RAM 佇列記憶丟失（靜默丟失）風險。
    - **啟用 NLP 實體鏈結 (Entity Linking)**：成功安裝 `mem0ai[nlp]` 依賴與 `spaCy` NLP 核心，正式解鎖 Mem0 v3 官方最核心的 Entity 實體分析與檢索加權機制，告別 semantic-only 降級模式。
    - **長期Facts記憶重塑**：將 `memory_manager.py` 與最新 Mem0 v3 對接，底層適配 pgvector 768d，自研背景非同步 `run_in_executor` 與 `_run_mem0_with_retry` 退避重試保護器，並修復了空 Parts 查詢的 API 400 報錯。
    - **短期對話 ADK 官方持久化重構**：將 `ai_chat.py` 核心重構為 ADK Runner，並實作非同步會話自動存在性檢測與建立，徹底排除新頻道首次發言拋出 `Session not found` 崩潰的地雷。
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
    - 修復生理時鐘與中斷排程解耦 Bug，藉由 `sensory_interrupt_event` 與 `schedule_update_event` 雙事件排除驚醒與感官中斷的混淆問題。
 
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
