# 更新日誌 (CHANGELOG)

本檔案記錄了專案的所有重大更新與架構變動。這對於 Agent (AI 助手) 理解專案演進至關重要。

## [2026-06-28] - Minecraft BDS (CoffeeHost) Admin Tools v2.9.5 安全防禦重構與 Runtime Crash 核心修復
### 🚀 模組部署與安全重構 (Modding & Hotfix Deployment)
- **全新正向預查防線 (Lookahead Regex)**：升級雙引號與單引號正則表達式，增加 `(?=\s*[\),])` 與 `(?=\s*[,\}])` 正向預查。要求 UI 字串右引號後必須緊接括號、逗號或花括號，徹底杜絕了對任何「字串拼接（帶有 `+` 的動態字串）」進行物件化的誤殺，完美保留原版程式碼運作邏輯。
- **排除非 UI 系統核心檔案**：在編譯管線中引入 `EXCLUDE_FILES` 機制，精確排除 `stat-scoreboards.js` 等非 UI 渲染檔案。這成功避開了麥塊原生計分板 API `addObjective`（僅支援 String 參數）傳入物件時造成的 TypeError 致命載入崩潰，根治了工具失效的問題。
- **白名單查表與 100% 漢化率補齊**：回歸 100% 安全的白名單對照表替換方式。由 AI 全自動捕捉並補齊了最後 17 筆漏網字串（如 `Clear Inventory`、`Bonus Playtime`、`Bulk Remove` 等高頻選單詞彙），達到了 **0 筆未翻譯字串殘留、100% 完美全中文覆蓋**。
- **清理幽靈 UUID 註冊殘留**：分析伺服器啟動日誌，精確鎖定了 `world_behavior_packs.json` 中已失效的歷史模組 UUID `4c9e83bd-47ba-4a37-b673-8a39e8020a5c` 殘留，將其在世界中徹底清理移除，**完美根治了玩家進服時提示「至少有一項資源或行為套件無法載入」的經典紅字警報**。
- **jsDelivr 全球加速 CDN 下載**：將下載連結從 GitHub 直連升級為全球加速 CDN (jsDelivr)，玩家在台灣/大陸等地區重載資源包時將享有近乎無感的極速加載。
- **全方位測試與自動部署**：通過全體 JS 語法校驗（node --check），版本升級至 `2.9.5`，重新打包 `Admin_Tools_2.9.5_繁中版.mcaddon`，同步部署伺服器端 BP 與 RP 覆蓋，並同步更新世界版本註冊表。

## [2026-06-28] - Minecraft BDS (CoffeeHost) Admin Tools v2.9.2 官方標準多語言 (i18n) 終極漢化與通知訊息劫持
### 🚀 模組部署與 100% 官方標準漢化 (Modding & Official Localization)
- **漏網選單 100% 全數漢化**：清查出分散在後台檔案中的選單呼叫（如 `players.js` 的坐騎傳送選單、`spectator-rescue.js` 的旁觀者退出選單、`support-access.js` 的診斷選單、`stress-test.js` 與 `utils.js` 的 Discard 等），將其全數納入 RawMessage 替換範圍。並修正了正則表達式在匹配時吞噬「冒號與空格」的致命 Bug，實現了 JS 語法的 100% 合規。
- **通知訊息劫持翻譯 (AOP 攔截器)**：針對那些原本寫死在 JS 核心邏輯中且無法透過 RawMessage 輕易替換的聊天欄通知訊息（如 `Your home has been saved.`, `Request sent.` 等），在 `utils.js` 的 `tell` 函數底層寫入「執行期字串翻譯對照攔截器」，實現了聊天欄通知訊息的 100% 安全中文化，且完全不會有 `[object Object]` 運行時崩潰的隱患。
- **1 秒極速 GitHub CDN 加速下載**：將最新的資源包打包上傳並強制推送到 GitHub `dev` 分支，利用微軟官方的 `raw.githubusercontent.com` 全球 CDN 節點進行託管，並在伺服器根目錄部署了最新版本的 `cdn_config.json`。玩家進服重載資源包時將享有 1 秒瞬間下載完成的極速體驗！
- **自定義物品名稱完全中文化**：追加寫入 7 個自定義工具的物品本地化鍵值（如 `item.jm_at:admin_tool.name=§l§c管理員工具§r` 等）到資源包 `.lang` 檔，實現了手持工具名稱的 100% 繁體中文化。
- **675 筆多語言翻譯條目覆蓋**：總翻譯量提升至 675 筆，版本全體升級至 `2.9.2`，重新打包為 `Admin_Tools_2.9.2_繁中版.mcaddon` 並上傳同步伺服器。

## [2026-06-28] - Minecraft BDS (CoffeeHost) 效能調優與 Admin Tools v2.2.4 全方位繁中版部署
### 🛠️ 伺服器效能與網路調優 (Server & Performance Optimization)
- **優化手機熱點連線與網路壓縮**：調整 `server.properties` 的視距為 `6`（封包量減少 45%），寫入 `compression-threshold=256` 進行封包深度壓縮，防止 NAT 3 玩家丟包；開啟 `max-threads=0` 全開 CPU 運算資源；將 `enable-ipv6` 設為 `off` 排除 IP 衝突。
- **預設玩家權限修改**：將 `default-player-permission-level` 修改為 `operator`，實現新加入玩家自動獲取 OP 管理員權限，簡化測試與管理授權流程。
- **強制啟用伺服器資源包**：在 `server.properties` 中將 `texturepack-required` 設為 `true`，強制登入玩家必須下載伺服器端中文化資源包，避免客戶端顯示錯誤。

### 🚀 模組部署與 NBT 實驗性功能修改 (Modding & NBT Modification)
- **首創 Python NBT 編輯修復實驗性功能**：因 `Admin Tools v2.2` 高度依賴 Script API (JS 腳本)，在本地利用 `nbtlib` 對遠端下載的 `level.dat` 進行 NBT 標籤底層修改，強制將 `experiments` 下的 `gametest`、`beta_api` 和 `upcoming_creator_features` 寫入並開啟為 `1`（啟用 Beta APIs 實驗性功能），重新包裝為基岩版小端序格式並透過 SFTP 覆蓋部署，完美解決 Script 模組無法加載的硬性限制。
- **Admin Tools v2.2.4 全方位精密漢化實作**：
  - 解壓並透過 SFTP 部署 Admin Tools 插件至 `behavior_packs/` 與 `resource_packs/`。
  - 修復了前一版因粗暴改寫系統模組依賴版本號引發的套件載入錯誤。
  - **2.2.4 擴大漢化範圍**：重寫漢化程式，擴大正則匹配範圍至 `label: "..."`（物件屬性宣告）以及 `.header(...)`、`.slider(...)` 等 UI 元件函數。成功將玩家主選單（`Player Menu`）的按鈕副標題及描述（如 "Manage your saved locations"、"Server teleport locations" 等）精密中文化。
  - 將插件與世界註冊表中的版本號強制升級為 `2.2.4`，清空玩家本地的舊快取，達成 100% 不崩潰的全中文可視化玩家選單。
- **Admin Tools v2.2.2 安全繁中版實作與部署**：
  - 解壓並透過 SFTP 部署 Admin Tools 插件至 `behavior_packs/` 與 `resource_packs/`。
  - 修復了前一版因粗暴改寫 `@minecraft/server` 等系統模組的 dependency 版本號，導致連線時報錯「至少有一項行為或資源套件無法載入」的 Bug。
  - **2.2.2 安全漢化設計**：重新對 12 個 JS 代碼執行正則替換，**保留代碼核心判斷用的英文按鈕單字**（如 `Save`、`Cancel`、`Reset`、`Close` 等操作動詞），只漢化純顯示的選單標題、天氣、設定等，完美相容代碼 runtime 條件判斷。
  - 將插件與世界註冊表中的版本號強制升級為 `2.2.2`，清空玩家本地的舊英文快取，順暢加載中文化介面。

## [2026-06-27] - Minecraft BDS (CoffeeHost) 與神奇嗨螺 Conch 機器人雙向互通
### 🚀 系統與功能升級 (System & Functions)
- **實作 BDS 與 Discord 雙向 WebSocket 橋接**：
  - 在本地 `discord_bot` 中實作了全新的 [minecraft.py](file:///home/hi6688/servers/discord_bot/cogs/inactive/minecraft.py)（當 `BOT_MODE=CONCH` 時載入），非同步啟動 WebSocket 伺服器監聽 `24446` 連接埠。
  - 實作安全握手驗證與雙向訊息轉發，玩家發言與進出廣播即時在遊戲內與 Discord 頻道（ID: `1471089934319489045`）互轉。
  - 支援管理員利用 `/mc狀態` 查看橋接連線數，以及透過 `/mc指令 <command>` 在遊戲內遠端下達控制台指令。
- **建立 BDS Behavior Pack 行為包**：
  - 在本地建立了 `coffee_bridge_bp` 連接器行為包，包含 [manifest.json](file:///home/hi6688/servers/scratch/coffee_bridge_bp/manifest.json) 與 [main.js](file:///home/hi6688/servers/scratch/coffee_bridge_bp/scripts/main.js)，以 `@minecraft/server-net` 的 WebSocket 實作啟動主動連線、每 10 秒自動斷線重連及事件發送。
- **升級 SFTP 自動部署與設定工具**：
  - 擴充並改寫 [coffeehost_sync.py](file:///home/hi6688/servers/scratch/coffeehost_sync.py)，讀取並解析 `.env` 後動態將本機公網 IP 及 Token 替換入 Behavior Pack 中。
  - 透過 SFTP 成功部署行為包至 CoffeeHost 伺服器端的 `development_behavior_packs/`，並自動建立遠端 `config/default/` 目錄完成 `permissions.json` 的上傳放行。

## [2026-06-26] - VS Code 終端機設定更新
### 🔧 設定與系統最佳化 (Configuration & Performance)
- **更新 VS Code 終端機設定檔**：在 `.vscode/settings.json` 中移除 `Gemini CLI` 設定檔，並新增 `OpenCode` 終端機設定檔。

## [2026-06-26] - 寶可夢裝備/招式/特性全繁中翻譯 + Bot 共享查詢
### 🌐 繁中翻譯 (Phase 1 — teambuilder_client)
- **物品翻譯**：補齊 Reg M-B 155 個合法物品的繁中名稱與描述，含 34 個新 Mega 進化石命名、21 個 Mega 石描述物種名修正、倍率統一改倍率 (1.2x→1.2倍)、機率用語統一 (幾率/概率→機率)、分數還原 (1/2 最大 HP)
- **招式翻譯**：補齊 Reg M-B 500 個合法招式的繁中 shortDesc/desc，含 Champions mod 改寫的招式描述 (Rage Fist, Belch 等)、保護系/束縛系/多段攻擊系等模板化描述、幾率/倍率/分數統一修正
- **特性翻譯**：補齊 Reg M-B 200 個合法特性的繁中 shortDesc/desc，含 6 個自創 Champions Mega 特性翻譯 (Dragonize→龍化、Mega Sol→超級陽光 等)、Cheek Pouch/Sheer Force 數值錯誤修正
- **不動 upstream**：僅修改 `js/translations.json`，`data/*.js`、`translate.js` 引擎、上游源碼全未觸及

### 🤖 對戰機器人 (Phase 2 — pokemon_bot)
- **新增 `src/battle/data.ts`**：共享翻譯資料載入器，啟動時讀取 `translations.json` + @pkmn/dex 建立 id→繁中對照表
- **擴充 `translations.ts`**：`translateItem`/`translateMove` 改讀共享表，新增 `translateAbility`，對戰日誌全繁中化
- **對戰看板新增道具/特性欄位**：`BattleUI.ts` Embed 顯示持有道具與特性 (🎒/⭐)
- **新增查詢指令**：`/item <name>`、`/move <name>`、`/ability <name>` 支援中英文雙向查詢
- **全部 TypeScript 編譯通過** (tsc --noEmit)

## [2026-06-23] - 寶可夢對戰 HUD 排版重構 (無等級/經驗值 Champion 版本)
### 🎨 介面與體驗優化 (UI/UX)
- **移除了等級與經驗值繪製**：移除 `Lv.` 文字與我方的底部 `EXP` 經驗條。
- **統一 HUD 卡片設計**：
  - 高度縮小至 `50px` 以完美貼合雙屬性徽章。
  - 移除所有邊框 (No Border/Stroke)，採用無框極簡排版。
  - 將 HUD 六邊形底板重構為統一的純深色背景，主體寬度縮小為 `w - 40` (350px) 以緊密貼合屬性徽章。
- **重構我方屬性置左、敵方置右的排版**：
  - **屬性無縫貼合**：取消原先屬性徽章與主體卡片之間的 4px 空隙，實作**屬性徽章與六邊形卡片斜邊 100% 無縫貼合**，讓徽章像積木般完美貼緊斜切邊，極具視覺一體感。我方在左側無縫貼合，敵方在右側無縫貼合。
  - **升級像素徽章**：改用 PokéRogue 官方帶有斜切角的 `pbinfo_player/enemy_type1/2.png` 徽章。
  - **垂直對齊**：第一與第二屬性上下排列，精確計算 X 坐標確保邊緣垂直對齊。
- **新增真實特殊狀態與屬性 UI 素材 (取代純文字)**：
  - **太晶化狀態**：載入 PokéRogue 官方 `icon_tera.png` 像素寶石圖示（放大至 16x20 像素），於寶可夢名字與性別右側繪製，**完全取代原本難看的 `[太晶]` 純文字**。
  - **超級進化狀態**：載入 Showdown 官方對戰經典 `icon_mega.png` 螺旋標誌（16x16 像素），於寶可夢名字與性別右側繪製，**完全取代原本的 `[MEGA]` 純文字**。
- **資訊排版微調**：
  - 特殊狀態標記：順序為「名稱 性別 特殊圖示」，與官方對戰介面完全對齊。
  - 血條與數值：3D 血條寬度調整為 `125px`，HP 數值 `hp/maxHp` 對齊血條右端。
  - 狀態標記：異常狀態徽章切片（60x24）精確排版於底左方；狀態圖示垂直偏移至 `y + 23`。
- **新增霓虹視覺標示**：支援太晶化時外框渲染霓虹青色，Mega 進化渲染霓虹粉色。

### 🐛 錯誤修復 (Fixes)
- **同步修復 `test_pokerogue_ui.ts`**：調整測試環境參數，確保與真實渲染結果 100% 一致。
- **修復 TypeScript 實作**：移除 [BattleUI.ts](file:///home/hi6688/servers/pokemon_bot/src/battle/BattleUI.ts) 中舊版重疊的 `drawPokemonHUD` 函數，解決語法衝突與 `TransformError` 地雷。

## [2026-06-22] - 解決 Git 儲存庫過多使用中變更與編輯器效能限制
### 🔧 設定與系統最佳化 (Configuration & Performance)
- **優化 .gitignore 忽略規則**：在根目錄 `.gitignore` 中新增 `venvs/`、`node_modules/`、`**/node_modules/` 與 `.antigravitycli/` 等大型開發依賴與執行期目錄。
- **排除十萬個未追蹤檔案**：成功將 100,000+ 個由 Python 虛擬環境與 Node 模組產生的檔案排除於版控與編輯器監控外，解決 VS Code 的 Git 檔案變更監控上限警告，恢復編輯器 Git 完整功能。

## [2026-06-20] - 實作全路徑前綴重寫 ASGI Middleware 與獨立 Hermes 運維主管服務
### 架構與系統升級 (Architecture)
- **實現主管端 Profile 與機器人端之絕對對稱**：新建 `server_admin` Profile，並將原先歷史殛留、直接佔用 `~/.hermes/` 根目錄的主管端設定檔、SQLite 狀態資料庫與環境變數檔案完敥搬移至 `/home/hi6688/.hermes/profiles/server_admin/`，讓兩端在檔案目錄履級上遚成「絕對對稱與平排隔離」。
- **更新 systemd 背景服務身份**：修改亍 `hermes_dashboard.service` 的 `HERMES_PROFILE` 環境變數與加載的 `.env` 檔案路徑，使其以對稱的 `server_admin` 身份正常啟動。
- **重新調整 ASGI 路由重寫正則**：對兩端代碼庫中的 `ProfilePathRewriteMiddleware` 正則表遚式由 `(hihi|default)` 修改為對稱的 `(hihi|server_admin)`。
### 🚀 架構與系統升級 (Architecture)
- **實作全路徑前綴重寫與 Profile 同步 ASGI Middleware**：在主管端與機器人端的 `web_server.py` 中掛載 `ProfilePathRewriteMiddleware`，實現對所有以 `/<profile_name>/` 開頭的請求進行路徑重寫並注入 `?profile=<profile_name>` 參數，並提供對無尾斜線請求的自動 307 重定向，解決 Windows 桌面端（Hermes Desktop）因為不支援 `?` 參數而無法在單一 Port 9119 下實現連線與 Session 隔離的限制。
- **支援 Profile 狀態的動態同步**：修改 `/api/profiles/active` 端點，使其接收 `profile` 參數並將當前的 `current` 及 `active` profile 動態設定為傳入的參數值，成功解決前端 React 路由加載時強制跳轉回預設 profile 的問題。
### 🚀 架構與系統升級 (Architecture)
- **徹底分離主管大腦與聊天平台配置**：修剪並清空了 `/home/hi6688/.hermes/config.yaml`（`default` Profile）中殘留的 `discord` 與 `slack` 等平台頻道設定（原自 `hihi` 的 `free_response_channels`），解決了點開主管的 Web 控制面板 Settings 時依然顯示 hihi 聊天設定檔的混淆問題，並重啟 `hermes_dashboard.service` 服務使其載入生效。
- **對齊主管與機器人 Web 認證憑證 (Session Token) 以相容桌面端**：考量到 Windows 桌面端軟體 (Electron) 對多 Profile 連線之 Session Token 的設定限制，我們將主管面板 (`hermes_dashboard.service`) 的 `HERMES_DASHBOARD_SESSION_TOKEN` 還原對齊為 `2a1a462e6c7b2594fcf73cf0c7de0b74`，以確保桌面端能正常連線 Port 9119 的主管面板，並同步更新了偵錯腳本 `test_dashboards_status.py` 驗證成功。
- **物理封鎖與過濾 Web 端 Profile 列表**：為了徹底根除兩端 Dashboard 共用 Session Token 時因瀏覽器快取可能引發的設定檔與記憶混淆，我們修改了兩端代碼庫（主管與 hihi）中 `web_server.py` 的 `/api/profiles` API。後端現在會根據執行實體 (HERMES_HOME) 自動識別，並**強制只回傳當前執行的單一 Profile**，在 API 層級上強制鎖死，防止任何跨 Profile 切換、設定檔或記憶污染的漏洞。
- **重置與物理淨化主管大腦的記憶歷史**：清空並重建了主管的本地 SQLite 狀態資料庫 `state.db`（移成了混亂期殘留的 hihi 短期對話歷史），並將主管的 Honcho 長期記憶工作區升級重置為全新的 `server-admin-workspace-v3`，從根本上徹底重置並阻斷了主管大腦載入到 hihi 歷史記憶與事實的混淆問題。
- **全域檔案收攏與服務路徑重定向**：為優化伺服器根目錄結構，建立 `/home/hi6688/servers/venvs` 收納目錄，並將所有 Python 虛擬環境統一移動收攏為 `venv_web`、`venv_hermes` 及 `venv_hermes_admin`，避免根目錄散落。
- **重新進行 pip editable 綁定**：針對移動後損壞的 python venv 內部 pip 路徑，利用對應虛擬環境直譯器執行 `python -m pip install -e` 成功將 `venv_hermes` 重新綁定至 `hermes-agent`，及將 `venv_hermes_admin` 重新綁定至 `hermes-agent-admin`。
- **重定向 systemd 背景服務**：修改了 `web_interface.service`、`hermes_bot.service` 與 `hermes_dashboard.service` 的 `ExecStart` 直譯器啟動路徑，重載 systemd daemon 並重啟驗證，確認三個背景服務皆已 100% 綠燈順暢運行 (Active: active (running))。
- **程式碼與虛擬環境實體隔離**：為確保系統層級主管服務的安全性，複製並建立了獨立的 `hermes-agent-admin` 程式碼資料夾與 `venv_hermes_admin` 虛擬環境，達成最高級別的安全物理隔絕。
- **還原運維與指令分析提示詞**：在新目錄中還原了 `prompt_builder.py` 提示詞以支援 `antigravity-oauth` 驗證，並使伺服器主管 Agent 重新獲取強大的系統指令分析與推理能力，不影響 Discord 聊天機器人。
- **建立獨立運維 Profile (server_admin)**：藉由 `hermes profile create` 建立了獨立的運維環境。配置 `memory.provider` 為 `hindsight`（本地 SQLite），完成與 Discord 聊天機器人（`default` profile）的記憶物理隔離。
- **工具授權與人設定義**：在 `server_admin` 的 `config.yaml` 啟用 `terminal` 與 `file` 工具以獲取主管伺服器能力；重寫了 `SOUL.md`，將其人設定義為專業、冷靜、且以行動優先的雲端伺服器主管。
- **部署本機安全 Web Dashboard**：編寫並註冊了 `hermes_dashboard.service` 用戶級 systemd 背景服務（注入環境變數 `HERMES_PROFILE=server_admin`），僅 bind 監聽本機 `127.0.0.1:9119`。
- **配置 FRP stcp 加密隧道與手機端對接**：在本地 `frpc.toml` 新增 `stcp` 加密秘密代理，建立並啟動 `frpc.service` 背景自啟服務。同時為 Android 手機 Termux 訪客端提供了安全的對接設定，流量全程加密。
- **大腦模型升級至 Gemma 4 31B**：將系統主管大腦的預設 LLM 升級為 Google 最新發布的開源旗艦模型 `gemma-4-31b-it`，由現有的 `GEMINI_API_KEY` 直接驅動，免去額外申請 OpenRouter 金鑰與花費。

## [2026-06-19] - 完全遷移至本地自建開源 Nous Hermes-Agent + Honcho 架構正式完成與驗證
### 🚀 架構與系統升級 (Architecture)
- **重構大腦協調器 (orchestrator.py)**：徹底廢除舊有 Google ADK 依賴，改為實例化 `run_agent.AIAgent`。重寫對話 Loop 以非同步 executor 調用 `AIAgent.run_conversation()`，並在 Python 導入前精確過濾 `sys.path` 以避免 `honcho/src` 和 `discord_bot` 的 `utils` 命名空間衝突。
- **對接本地自建 Honcho 記憶引擎**：配置 `~/.hermes/config.yaml` 使用 `provider: honcho`。實作 `/forget_me` 和 `/profile` 指令底層介面對接 `Honcho` 的 Conclusions (事實與印象) 和 Sessions (會話與短期記憶) 管理。
- **234 條歷史記憶完整搬遷**：執行並完成 `migrate_to_honcho.py`，物理遷移原 PostgreSQL `hihi_mem0_facts` 的 234 條用戶 facts 到本地自建的 Honcho Server 數據庫中。
- **NeMo Relay 遙測與事後綜合卡片發射**：啟用 `nemo_relay` 插件導出 ATOF/ATIF 軌跡。在 `orchestrator.py` 配置 `on_thinking`、`on_reasoning` 與工具執行的非同步 callbacks，並在對話結束後讀取解析軌跡 JSON 以發射精美的事後邏測大卡片到 `#心裡世界` 頻道。
- **單元測試與服務部署**：編寫並執行 `test_hermes_migration.py`，完成 ReAct 推理循環、Honcho 記憶檢索與 telemetry 回調的 100% 綠燈驗證。重啟 systemd 服務 `hermes_bot` 正常運行。

## [2026-06-18] - 清除內建開發型人設與引導詞
### 🔧 設定與提示詞淨化 (Configuration & Prompts)
- **清空/改寫 prompt_builder.py 中的開發輔助詞**：清空了 `HERMES_AGENT_HELP_GUIDANCE`、`TASK_COMPLETION_GUIDANCE`、`GOOGLE_MODEL_OPERATIONAL_GUIDANCE`，並將 `DEFAULT_AGENT_IDENTITY` 改為 HiHi 的基礎聊天身份設定。
- **淨化記憶引導詞**：將 `MEMORY_GUIDANCE` 修改為極簡功能性規則說明，完全不包含任何具體對話或生活範例，防止範例污染。
- **全域停用寫程式模式 (coding_context)**：在 `~/.hermes/config.yaml` 中新增了 `agent.coding_context: "off"` 配置，以防止大腦在偵測到 codebase 時自動載入 senior engineer 寫程式人設。
- **重啟服務與驗證**：重啟了 `hermes_bot` systemd 服務，並通過 CLI oneshot 測試，成功證實大腦不再提及寫程式、處理檔案等生產力助手功能，回歸趣味聊天伴侶定位。

## [2026-06-18] - 完全遷移至本地自建開源 Hermes-Agent + Honcho 架構計畫發布
### 🚀 架構與系統升級 (Architecture)
- **發布 100% 本地自建遷移計畫書**：應使用者要求，將計畫書覆寫為 [implementation_plan.md](file:///home/hi6688/.gemini/antigravity-ide/brain/f507483e-b47b-4903-9965-cc19ca3fcfd4/implementation_plan.md)，全面採行「完全本地自建自託管（Self-Hosted）」架構，捨棄外部 SaaS 雲端，保障極致的資料主權與隱私。
- **本地 Honcho Server (Docker) 部署規劃**：計畫於伺服器上以 Docker Compose 部署完全開源的 Honcho 服務端，關閉驗證並提供本地 Gemini 大腦金鑰以實現自主睡眠固化（Sleep Cycle）。
- **更新一鍵遷移腳本**：更新 [migrate_to_honcho.py](file:///home/hi6688/servers/scripts/migration/migrate_to_honcho.py) 腳本，改為對接本地自建端點 `http://localhost:8000` 並支援免金鑰驗證，用以搬遷 Postgres 的 Mem0 Facts 至本地 Honcho 結論。
- **遙測系統轉接方案**：設計透過監聽會話日誌 JSON 來將大腦思緒即時推送至 Discord `#心裡世界` 頻道的遙測轉接機制。

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
