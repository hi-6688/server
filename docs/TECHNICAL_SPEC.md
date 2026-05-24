# 技術規格書 (Technical Specifications)

本文件為 Discord 數位生命體「嗨嗨 (HiHi)」的底層技術實作規格書，作為系統結構與運行規範的**單一事實來源 (Single Source of Truth, SSOT)**。所有關於 AI 決策表單、記憶向量、生理時鐘與表情符號轉換的細節皆收攏於此。

---

## 1. 兩階段認知管線 (Two-Stage Cognitive Pipeline)

為了避免大模型在角色扮演的同時處理複雜的邏輯決策，進而造成「注意力渙散 (Attention Dilution)」與「角色崩潰 (Persona Break)」，系統採用非同步的兩階段管線架構。

```
                    ┌────────────────────────┐
                    │  Discord Message Input │
                    └───────────┬────────────┘
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │ 【階段一：LogicRouter】                       │
         │ - 呼叫 SDK 原生 Tools (save_memory, RAG 等)   │
         │ - 輸出強型別 Pydantic: MemoryState           │
         └──────────────┬───────────────────────────────┘
                        │
                        ├─► needs_reply == False ──► (流程終止，不發言)
                        │
                        └─► needs_reply == True
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │ 【階段二：ChatGenerator】                     │
         │ - 載入階段一 RAG 結果與決策上下文             │
         │ - 輸出強型別 Pydantic: PersonaResponse       │
         └──────────────┬───────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Final Speech Output │
            │   (發送至 Discord 頻道)   │
            └───────────────────────┘
```

### 1.1 階段一：LogicRouter (邏輯決策)
此階段使用 `google-genai` SDK 的 `Interactions API`。由於 Interactions API 尚不支援 Python 自動工具呼叫 (Auto Tool Calling)，系統在此處實作了手動工具迴圈 (Manual Tool Looping)，藉由遍歷 `interaction.outputs` 攔截 `function_call`，執行本地 Python 工具後將 `function_result` 傳回大腦，直到 status 變為 `completed`。本階段不啟用 `response_format` 以防與 tools 傳參衝突，而是依靠 Prompt 來限制輸出格式，並由 Python 本地 `json.loads` 解析。

*   **模型類型**: `gemini-3.1-flash-lite`
*   **輸出結構**: `MemoryState` (Pydantic Model)
*   **欄位定義**:
    ```python
    class MemoryState(BaseModel):
        needs_reply: bool = Field(description="判斷目前對話歷史是否需要我回答。若需要填 True，不需要或決定休眠填 False。")
        current_goal: str = Field(description="我目前的工作目標或要處理的實體。")
        suggested_sleep_seconds: int = Field(description="我決定接下來要主動休眠多久（秒）？這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，填 3600；若配額快耗盡，請大膽填寫 14400 或更長，直到下午三點重置。")
        sleep_intent: Optional[str] = Field(default=None, description="如果妳設定了休眠秒數，請在這裡寫下妳『醒來後要做什麼』(例如：『等待60秒後回答問題』)。如果只是普通的長眠，請填 null。")
    ```

### 1.2 階段二：ChatGenerator (對話生成)
此階段讀取階段一整理好的上下文、今日額度狀況與 RAG 記憶，專注進行擬態角色扮演與發言輸出。此階段使用 `response_format` 指定 `PersonaResponse.model_json_schema()` 以強制輸出結構化 JSON，並且**不**掛載任何 Tool。

*   **模型類型**: `gemini-3.1-flash-lite`
*   **輸出結構**: `PersonaResponse` (Pydantic Model)
*   **欄位定義**:
    ```python
    class PersonaResponse(BaseModel):
        situation_analysis: str = Field(description="簡短分析目前群組的氣氛與上下文脈絡。")
        internal_thought: str = Field(description="妳在心裡的 OS。決定用什麼態度回覆。")
        final_speech: Optional[str] = Field(default=None, description="最後要在 Discord 說出口的話。如果覺得不想回，請填 null。")
    ```

---

## 2. 記憶與檢索系統 (Memory & RAG Specification)

### 2.1 記憶編碼規格
*   **向量模型**: `gemini-embedding-2` (正式版，不支援舊版 preview 的 `task_type` 欄位)
*   **維度規格**: 768 維度
*   **L2 歸一化 (L2 Normalization)**:
    由於使用 SDK 輸出 768 維度截斷向量時，API 回傳向量預設未進行歸一化。為防止 pgvector 餘弦相似度 (Cosine Similarity) 檢索失真，必須在儲存與檢索前，對向量進行手動 L2 歸一化：
    $$\hat{\mathbf{v}} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2} = \frac{\mathbf{v}}{\sqrt{\sum_{i=1}^{n} v_i^2}}$$

### 2.2 檢索機制
*   **RAG 類型**: RRF (Reciprocal Rank Fusion) 混合檢索（Vector 餘弦距離 + Full-Text 全文檢索）。
*   **時光機機制 (Context Retrieval)**：當檢索命中某一筆長期記憶或事實時，系統不僅載入該筆記憶，更會透過該筆記憶的時間戳記，調閱發生時「之前」的 10 句原始對話上下文，重現歷史現場以防幻覺。

### 2.3 背景寫入佇列
為解決 API 連線延遲阻塞主對話流程，`MemoryManager` 實作了非同步佇列 `memory_queue`：
1.  AI 調用 `save_memory` 工具時，資料被即時推入 `memory_queue` 並回傳成功。
2.  背景協程 `_process_memory_queue` 輪詢佇列，進行非同步標籤生成、Embedding 向量化與 PostgreSQL 寫入。
3.  在 Cog 解除載入時，自動呼叫 `close_pool()` 安全取消協程與清理連線池。

---

## 3. 自主生理時鐘與排程 (Heartbeat & Scheduler)

AI 可透過階段一輸出的 `suggested_sleep_seconds` 與 `sleep_intent` 主動控管自己的生命週期與甦醒排程：

1.  **心跳引擎**: 背景無窮迴圈的 `asyncio.Task` 運作。
2.  **物理中斷**: 當有新訊息傳入時，系統可透過 `wake_event.set()` 發出物理中斷喚醒心跳引擎。
3.  **防衛性休眠**: AI 在今日 API 額度（RPD 上限 500）吃緊時，可設定極高的睡眠時間，直接進入防衛性休眠狀態（暫時不處理對話感知）。

---

## 4. 表情符號翻譯與替換 (Application Emojis)

為了讓 AI 能靈活運用 Discord 伺服器內的自定義表情包，而不因寫死表情 ID 導致格式破裂，系統設計了翻譯義眼機制：

1.  **讀入對照表**: 讀取 `data/hihi/emojis.json` (代碼對照) 與 `emoji_meanings.json` (語意說明)。
2.  **輸入端 (語意化)**: 傳送給 AI 的歷史紀錄中，所有的自訂表情符號 `<:emoji_name:id>` 會被轉換為文字符號如 `[emoji_name]`，使大腦能輕易理解表情的語意。
3.  **輸出端 (實體化)**: 當 AI 輸出 `[表情代碼]` 時，Discord 傳送模組會自動將其替換為實際的 `<:emoji_name:id>`，呈現精美的表情圖案。
