# 前端架構規範 (Frontend Architecture)

本文件定義麥亂伺服器控制面板 (`web_interface`) 的前端架構與設計準則，所有前端開發與修改均須遵守此規範。

## 1. 技術堆疊 (Tech Stack)
*   **核心框架**: React (JSX/JS) 搭配 Vite 進行建置。
*   **樣式與設計體系**: 原生 CSS (Glassmorphism 毛玻璃風格)，禁止為了單一特效引入龐大的 UI 庫 (如 Material UI / AntD)。
*   **專案路徑**: 所有的 React 開發皆位於 `web_interface/frontend/` 目錄下。
*   **API 請求**: 使用 原生 `fetch()` 或 `axios` 進行非同步呼叫。

## 2. 視覺設計系統 (Design System)

### 2.1 核心風格 (Glassmorphism & Dark Mode)
本專案採用**深色毛玻璃 (Glassmorphism)** 風格。
所有的主要版塊必須使用預先定義好的 CSS class：

*   `.glass-panel`: 用於大型容器 (Container)、對話框 (Modal)。背景為半透明的深灰色 (`rgba(20, 20, 25, 0.7)` 或類似)，帶有輕微邊框 (`border: 1px solid rgba(255, 255, 255, 0.1)`) 與 Backdrop Filter (背景模糊)。
*   `.glass-card`: 用於小型卡片、資料展示塊。滑鼠懸停 (Hover) 時應有細微的向上浮動效果 (`translateY(-2px)`) 與邊框高光 (`border-color: rgba(255, 255, 255, 0.2)`).

### 2.2 佈局結構 (Layout Structure)
*   **頂部導航列 (Top Nav)**: 固定於畫面頂端 (Fixed Top)。包含 Logo、右側的使用者頭像與主要功能連結 (`nav-links`)。
*   **次級導航列 (Secondary Nav)**: 位於 Top Nav 下方，用於頻繁切換的「伺服器實例列表 (Instance Selector)」。
*   **主內容區 (Main Content)**: 根據上方導航，將不同區塊以 `.section.active` 的形式切換顯示，支援單頁式切換 (SPA) 體驗，不刷新網頁。

## 3. JavaScript 邏輯架構 (JavaScript Architecture)

### 3.1 核心管理物件 (`DataManager`)
所有的前端狀態更新與輪詢皆透過 `DataManager` 控制：
*   **`init()`**: 初始化應用程式、驗證 API Key、載入實例列表。
*   **`startAutoSync()`**: 每隔 5 秒自動呼叫伺服器後端，更新 CPU/RAM、線上玩家數量與伺服器狀態。
*   **`refreshAll(silent)`**: 執行具體的資料更新。若 `silent` 為 `true`，則不顯示 Loading 轉圈動畫。

### 3.2 網路請求介面 (`buildApiUrl`)
所有的 API 請求必須經過 `buildApiUrl(endpoint, params)` 函式建立：
1. 自動注入安全金鑰 (`key=API_KEY`)。
2. 自動綁定當前選擇的伺服器環境 (`instance_id=CURRENT_INSTANCE_UUID`)。
*禁止直接撰寫包含敏感字串的 fetch URL。*

## 4. 🚫 前端避坑指南 (Anti-Patterns)
1. **維持輕量化組件**：這是一個極致輕量化的面板，請善用 React 的組件化 (Components) 拆分過於肥大的邏輯，禁止在單一 `App.jsx` 塞入上千行程式碼。
2. **遵守 React State 鐵律**：所有的資料流與畫面更新皆需依賴 `useState` 與 `useEffect`，**嚴格禁止**使用 `document.getElementById` 直接干涉真實 DOM 節點來修改文字或樣式。
3. **組件層級的毛玻璃 CSS**：所有的 Glassmorphism className 請寫妥在全局的 `.css` (例如 `admin.css`)，讓各個組件 (`.jsx`) 直接套用 class，保持邏輯與樣式分離。
