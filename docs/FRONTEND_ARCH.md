# 前端架構規範 (Frontend Architecture)

本文件定義麥亂伺服器控制面板 (`web_interface`) 的前端架構與設計準則，所有前端開發與修改均須遵守此規範。

## 1. 技術堆疊 (Tech Stack)
*   **核心框架**: React (JSX/JS) 搭配 Vite 進行建置。
*   **樣式與設計體系**: Tailwind CSS + 原生 CSS (透明玻璃風格，無模糊)，禁止為了單一特效引入龐大的 UI 庫 (如 Material UI / AntD)。
*   **字體**: Noto Sans TC (Google Fonts)，等寬字體使用 Consolas / JetBrains Mono。
*   **圖示庫**: Material Symbols (導航) + Font Awesome 6 (功能圖示)。
*   **專案路徑**: 所有的 React 開發皆位於 `web_interface/frontend/` 目錄下。
*   **API 請求**: 透過 `src/utils/api.js` 統一管理，使用原生 `fetch()` 進行非同步呼叫。

## 2. 目錄結構 (Directory Structure)

```
web_interface/
├── api.py               ← 後端 API 入口 (路由分發器)
├── models.py            ← 資料模型 (Instance + InstanceManager)
├── routes/              ← 路由處理模組 (auth, server, files, worlds, addons, instances)
├── helpers/             ← 工具函式 (pack_installer, level_utils)
├── remote_api.py        ← 遠端 VM2 API
├── proxy_helpers.py     ← 代理工具
├── instances.json       ← 伺服器實例設定
├── admin_config.json    ← API Key 設定
├── web_config.json      ← 網頁設定
├── schema.json          ← API Schema
├── frontend/            ← React 前端
│   ├── index.html       ← HTML 模板 (引入 Noto Sans TC + Font Awesome)
│   └── src/
│       ├── App.jsx              ← 主入口 (頂部導航 + 居中單欄佈局)
│       ├── index.css            ← 全域 Tailwind + 透明玻璃 CSS
│       ├── main.jsx             ← React 掛載入口
│       ├── components/
│       │   ├── TopNav.jsx       ← 頂部雙層導航列 (取代舊版 Sidebar)
│       │   ├── Dashboard.jsx    ← 狀態儀表板 (狀態區 + 9 張資訊卡片)
│       │   ├── LiveConsole.jsx  ← 嵌入式即時終端機 (儀表板下方)
│       │   ├── ConsolePage.jsx  ← 獨立全畫面終端機
│       │   ├── PlayersPage.jsx  ← 白名單與權限管理
│       │   ├── FilesPage.jsx    ← 世界地圖與模組管理
│       │   └── SettingsPage.jsx ← server.properties 設定編輯器
│       └── utils/
│           └── api.js           ← 前端 API 通訊層
├── scripts/             ← 偵錯與工具腳本
└── legacy/              ← 舊版 Vanilla HTML/JS (已廢棄，僅存檔)
```

## 3. 視覺設計系統 (Design System)

### 3.1 核心風格 (透明玻璃 + Dark Mode)
本專案採用**透明玻璃 (Transparent Glass)** 風格，無背景模糊(blur)效果。
背景圖為本地 `custom_bg.jpg`，透過透明面板直接透出背景。
所有的主要版塊必須使用預先定義好的 CSS class：

*   `.glass-panel`: 用於大型容器。`background: rgba(0,0,0,0.3)` + 白色細邊框 + 立體浮動陰影 (box-shadow) + 頂部高光邊框。
*   `.glass-card`: 用於小型卡片。滑鼠懸停時有向上浮動效果與加深陰影。

### 3.2 配色方案
*   **主色 (Primary)**: `#ee2b8c` — 導航 active indicator、重點高光
*   **成功 (Success)**: `#2ecc71` — 線上狀態、啟動按鈕
*   **危險 (Danger)**: `#e74c3c` — 離線狀態、關閉按鈕
*   **藍色 (Blue)**: `#3498db` — 資訊、記憶體進度條
*   **橘色 (Orange)**: `#e67e22` — 重啟按鈕、磁碟進度條
*   **文字**: `#e0e0e0` (主) / `#aaa` (副)

### 3.3 文字陰影系統
所有文字都帶有 `text-shadow` 以確保在任何背景上都清晰可讀。
標題 (`h1`/`h2`/`h3`) 使用加強陰影，輸入框內文字使用較輕陰影。

### 3.4 佈局結構 (Layout Structure)
*   **頂部雙層導航 (TopNav)**: 固定於畫面頂部。
    *   第一層：Logo + 伺服器名稱 + Tab 導航 (儀表板/設定/世界/規則/玩家)
    *   第二層：伺服器列表 + 新增按鈕
    *   Active Tab 有底部亮線 indicator + 圖示發光效果
*   **主內容區**: 居中單欄 (`max-w-7xl`)，根據 Tab 切換顯示不同頁面。
*   **SPA 架構**: 透過 React State 切換顯示，不刷新頁面。

## 4. React 邏輯架構 (React Architecture)

### 4.1 狀態管理
所有的前端狀態透過 React Hooks 管理：
*   **`useState`**: 管理伺服器狀態、CPU/RAM/Disk/Network、玩家數、指令輸入等。
*   **`useEffect`**: 初始化 API、每 5 秒自動輪詢伺服器狀態。

### 4.2 API 通訊層 (`src/utils/api.js`)
所有的 API 請求必須經過 `api.js` 提供的函式：
*   `initApi()` — 從 `admin_config.json` 載入 API Key。
*   `fetchStatus()` — 拉取伺服器狀態。
*   `sendCommandToConsole(cmd)` — 送出指令。
*   `sendPowerAction(action)` — 開機/關機/重啟。
*   `readFile(filename)` — 讀取設定檔。
*   `writeFile(filename, content)` — 寫入設定檔。
*   `fetchWorlds()` / `switchWorld()` / `deleteWorld()` — 世界管理。
*   `fetchAddons()` / `deleteAddon()` — 模組管理。
*   `fetchVersion()` — 取得伺服器版本。
*禁止在組件中直接撰寫包含敏感字串的 fetch URL。*

## 5. 🚫 前端避坑指南 (Anti-Patterns)
1. **維持輕量化組件**：請善用 React 的組件化拆分邏輯，禁止在單一 `.jsx` 塞入上千行程式碼。
2. **遵守 React State 鐵律**：所有資料流與畫面更新依賴 `useState` 與 `useEffect`，**嚴格禁止**使用 `document.getElementById` 直接干涉 DOM。
3. **樣式定義在全局 CSS**：所有的透明玻璃 className 寫在 `index.css`，各組件直接套用 class，保持邏輯與樣式分離。
4. **避免 scrollIntoView**：日誌自動捲動應使用容器的 `scrollTop`，不要用 `scrollIntoView()` 以免牽動整個頁面。
