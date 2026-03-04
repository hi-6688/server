# 📅 專案開發計畫書 (Roadmap)

最後更新時間: 2026-03-04

## 🔴 當前急迫事項 (Immediate Actions)
*修正資安、架構升級與設定問題*

- [ ] **Docker 容器化開發** `[High Priority]`
    - [ ] 替 `discord_bot` 與 `web_interface` 撰寫 Dockerfile
    - [ ] 建立專案層級的 `docker-compose.yml`
    - [ ] 設定 Volumes 將 `.db` 或設定檔掛載至外部
- [x] **`web_interface/` 目錄清理與重構** (已完成)
    - 舊版 HTML/JS 移至 `legacy/`
    - 偵錯腳本移至 `scripts/`
    - 測試用 `.dat` 檔案已刪除
- [ ] **根目錄清理**
    - [ ] 將 `force_sync.py`, `test_main.sh` 等散落腳本移動至 `scripts/`
    - [ ] 將 `my_server.tar.gz` 等備份檔移至 `backups/`

## 🟢 近期目標 (Short-term Goals)
*優化現有服務運作與架構*

- [x] **導入 Vibecoding 架構** (已完成)
    - 建立 `.agent/rules/readrules.md` 作為最高指導原則
    - 建立 `docs/` 作為專業手冊 (Frontend / Backend)
    - 建立第一個自動化腳本 `/update_readme`
- [x] **Git 倉庫與記憶體整理** (已完成)
    - 移除敏感資訊 (Token)
    - 為 VM1 增加核心 Swap 空間防崩潰
- [x] **Web 介面優化 (已完成)**
    - [x] 轉型為 React/Vite 架構 (`web_interface/frontend/`)
    - [x] 組件拆分 (TopNav, Dashboard, LiveConsole, ConsolePage, PlayersPage, FilesPage, SettingsPage)
    - [x] 建立 API 通訊層 (`src/utils/api.js`)
    - [x] 後端 `api.py` 模組化重構 (1012→238 行, 拆分為 `routes/` + `models.py`)
    - [x] 完善 Players (白名單/權限) / Files (世界/模組) / Settings (設定編輯) 頁面
    - [x] UI 重新設計：從側邊欄改為頂部導航、透明玻璃風格、Noto Sans TC 字體
    - [ ] 將假資料 (Mock Data) 逐步替換為真實 API
- [x] **GCP 雙 VM 架構遷移 (已完成)**
    - [x] VM1 保留控制面板與 Discord Bot，VM2 運行 Minecraft
    - [x] `proxy_helpers.py` 與 `remote_api.py` 雙向通訊
    - [x] 頂部導航 Logo 狀態指示燈綁定 VM2 即時狀態
- [x] **事件驅動自動安全關機 (已完成)**
    - [x] VM2 背景線程監聽日誌，玩家離開後 10 分鐘無人在線自動關機
    - [x] 智慧進程監控：確認遊戲引擎完全關閉後才切斷電源
    - [x] Webhook 通知 VM1 並透過 Discord 廣播
- [x] **離線設定備份 (已完成)**
    - [x] 關機前自動備份 `server.properties` 等設定檔至 VM1 快取
    - [x] 離線期間網頁可讀取與編輯，開機時自動同步至 VM2

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
