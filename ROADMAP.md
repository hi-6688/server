# 📅 專案開發計畫書 (Roadmap)

最後更新時間: 2026-03-03

## 🔴 當前急迫事項 (Immediate Actions)
*修正資安、架構升級與設定問題*

- [ ] **Docker 容器化開發** `[High Priority]`
    - [ ] 替 `discord_bot` 與 `web_interface` 撰寫 Dockerfile
    - [ ] 建立專案層級的 `docker-compose.yml`
    - [ ] 設定 Volumes 將 `.db` 或設定檔掛載至外部
- [ ] **根目錄清理與重構**
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
- [ ] **Web 介面優化**
    - 套用 `admin.html` 毛玻璃設計與元件重構
    - 將假資料 (Mock Data) 逐步替換為真實 API

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
