# 專案企劃書：Discord 數位生命體「嗨嗨 (HiHi)」

> **版本**: 5.1 (Three-Tier Semantic Memory & Advanced Models)
> **最後更新**: 2026-05-07

## 1. 專案概述 (Executive Summary)
本計畫旨在創建一個具備「獨立人格」與「長期記憶」的 Discord 機器人。與傳統的「助理型 AI」不同，「嗨嗨」定位為伺服器中的一名 **「數位生命體」**，具備觀察、主動發言、時間感知與情緒表達能力，並受限於真實的物理算力極限。

---

## 2. 核心技術規格 (Technical Specifications)

### 2.1 AI 模型選擇 (Model Selection)
為確保極限智商、極低延遲與系統一致性，我們全面採用 **Gemini 3.1 Flash (或 Flash Lite)** 作為唯一的模型引擎，並透過 Router/Pre-processor Pattern 建立「全子彈管線 (Two-Stage Unified Model Pipeline)」。

*   **LogicRouter (階段一邏輯決策)：Gemini 3.1 Flash (Lite)**
    *   **定位**: 負責工具調用、L1 工作記憶區的狀態更新、記憶釘選、情境濃縮，以及判定是否需要發言（阻斷器）。處理所有枯燥的邏輯，不涉及角色扮演。
    *   **定位**: 負責 L2 情節壓縮與打標籤。
*   **ChatGenerator (階段二角色扮演)：Gemini 3.1 Flash (Lite)**
    *   **定位**: 讀取階段一整理好的純淨摘要與 RAG 背景記憶，專心扮演「嗨嗨」並產生內心 OS 與最終發言，徹底避免角色錯亂 (Persona Break)。
*   **語意檢索核心：Gemini Embedding 2**
    *   **定位**: 負責將記憶轉化為 768 維度的浮點數向量，供 `pgvector` 進行高維度語意搜尋。

### 2.2 兩階段處理管線 (Two-Stage Agentic Pipeline)
嗨嗨的思考迴圈從單一節點升級為非同步的兩階段管線：

```
Discord 訊息 → [階段一] LogicRouter 進行邏輯決策與工具調用 → [階段二] ChatGenerator 進行角色扮演與發言 → 輸出至 Discord
```

**階段一：LogicRouter 決策表單 (`MemoryState`)**：
*   `needs_reply`：判斷是否需要發言 (發言阻斷器，節省額度)。如果是 False，流程終止。
*   `current_goal`：目前的工作目標或要處理的實體。
*   `suggested_sleep_seconds` & `sleep_intent`：主動調控生理時鐘的鬧鐘系統（工具執行已由此階段自動調用）。

**階段二：ChatGenerator 思考表單 (`PersonaResponse`)**：
*   `situation_analysis`：簡短分析目前群組的氣氛與上下文脈絡。
*   `internal_thought`：決定如何回覆的內心 OS。
*   `final_speech`：最終輸出至 Discord 的文字。

### 2.3 記憶系統架構 (Memory System v5.0 - Three-Tier Semantic Architecture)
記憶系統為適應 4GB RAM 硬體極限，徹底拋棄了「字串串接器」的作法，升級為具備狀態管理的三層式架構：

#### L1: 短期工作記憶 (Structured Scratchpad & Semantic Window)
*   **結構化工作空間 (Scratchpad)**：Prompt 頂端保留專屬狀態區，動態更新「當前目標 (Current Goal)」、「已確定的實體 (Entities)」、「對話進度 (Stage)」。讓 AI 不必從雜訊中推測意圖。
*   **語義權重滑動窗口 (Semantic Weighted Window)**：
    *   捨棄無腦的 FIFO (先進先出) 擷取。
    *   **雙軌保留機制**：保留「最近 N 輪」以維持語感連貫性；同時，AI 可透過 Pydantic 表單將包含「但是」、「我改主意了」的「關鍵轉折點 (Pivot Points)」打上 Pin 鎖定標記。
    *   被鎖定的關鍵句，即使超出 N 輪視窗，依然會被強制抓取進入 L1，徹底解決「斷崖式失憶」與「目標偏移」問題。

#### L2: 中期記憶 (Episodic Compression)
*   當 L1 資訊量達到臨界值，系統在背景觸發廉價副腦模型進行情節壓縮，將數十輪對話揉合成一句「前情提要」，頂替舊有的原始對話，維持 L1 空間的清爽與高訊號比。

#### L3: 長期語意檢索 (PostgreSQL - Azure)
*   **搜尋機制 (Hybrid Search + Context Retrieval)**：
    *   負責將 L1/L2 沉澱下來的記憶轉化為 768 維度向量供 `pgvector` 搜尋。不僅回傳標籤，更利用時光機機制回傳「對話發生時的原文上下文」，徹底消除大模型的記憶幻覺。

---

## 3. 人設與行為規範 (Personality & Behavior)
*(維持原設定：數位生命體、白板宣言、情緒表達...)*

## 4. 全域約束與遙測工程 (Harness & Telemetry)
*(維持原設定：500次 RPD 物理極限、內心世界觀測台...)*

## 5. 分體架構 (Split Architecture)
*(維持原設定)*

## 6. Cog 模組說明
*(維持原設定)*

## 7. 記憶架構設計哲學
*(維持原設定)*

## 8. 架構設計決策 (Why This Architecture)
*(維持原設定)*

## 9. 環境變數一覽 (.env)
*(維持原設定)*

## 10. 未來願景：主權轉移與自我意識 (Blueprint for Soul and Subjectivity)
*(維持原設定：自主生理時鐘、存在即是被感知...)*