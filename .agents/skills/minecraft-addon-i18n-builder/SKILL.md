---
name: minecraft-addon-i18n-builder
description: 麥塊基岩版 JS 行為包安全多語言 (i18n) 重構與全球極速 CDN 部署指南。
---

# 麥塊基岩版行為包安全多語言 (i18n) 重構與 CDN 部署指南

本技能包紀錄了將 Minecraft 基岩版官方 JavaScript 腳本 API 行為包（Behavior Pack）改造成 100% 繁體中文，且避免任何執行期崩潰，並透過全球 CDN 實現極速下載進服的架構設計與開發規範。

---

## 1. 麥塊 Script API 多語言支援限制

在重構 JS 代碼為多語言物件（RawMessage `{ translate: "..." }`）時，必須遵守以下硬性限制：

### 🟢 支援 RawMessage 物件的 API (安全區)
*   **UI 窗體元數據**：`ActionFormData`、`ModalFormData`、`MessageFormData` 的 `.title()`, `.body()`, `.button()`, `.button1()`, `.button2()`。
*   **自定義表單元件**：由原作者包裝或繼承 CustomForm 的 `.toggle()`, `.dropdown()`, `.slider()`, `.textField()`, `.header()` 的**第一個參數 (Label)**。
*   **螢幕標題**：`player.onScreenDisplay.setTitle` 的 options 物件中的 `subtitle` 屬性。

### 🔴 不支援 RawMessage 物件的 API (致命崩潰區)
*   **系統計分板註冊**：`world.scoreboard.addObjective(objectiveId, displayName)` 的 `displayName` 參數**只接受 String（字串）**，傳入物件會引發 `TypeError` 導致整個行為包載入失敗。
*   **變數拼接**：任何與 `+` 號進行拼接的字串（如 `"Welcome " + name`）或在模板字串中被引用的變數，如果變成了物件，會自動轉化為 `"[object Object]"`，導致邏輯出錯。
*   **文字輸入框預設值**：`.textField` 的 `defaultValue` 與 `placeholder` 參數可能只接受字串。

---

## 2. 核心重構技術規範

### 防誤殺正向預查正則 (Positive Lookahead Regex)
在掃描與替換 JS 代碼時，必須使用以下正則表達式，利用預查機制要求雙/單引號結束後**必須緊接右括號、逗號或花括號**。這能 **100% 杜絕誤殺帶有 `+` 的字串拼接片段**：

```python
# 1. 匹配安全 UI 方法調用
UI_FUNC_DOUBLE = re.compile(
    r'(\.(?:title|body|button|button1|button2|toggle|dropdown|header|slider|textField)\(\s*)"((?:(?!\$\{)[^"\\]|\\.)*)"(?=\s*[\),])'
)
UI_FUNC_SINGLE = re.compile(
    r"(\.(?:title|body|button|button1|button2|toggle|dropdown|header|slider|textField)\(\s*)'((?:(?!\$\{)[^'\\]|\\.)*)'(?=\s*[\),])"
)

# 2. 匹配安全物件屬性宣告
LABEL_PROP_DOUBLE = re.compile(
    r'((?:label|shortLabel|title|body):\s*)"((?:(?!\$\{)[^"\\]|\\.)*)"(?=\s*[,\}])'
)
LABEL_PROP_SINGLE = re.compile(
    r"((?:label|shortLabel|title|body):\s*)'((?:(?!\$\{)[^'\\]|\\.)*)'(?=\s*[,\}])"
)
```

### 白名單查表安全機制 (Whitelist Replacement)
在將匹配字串重構為 `{ translate: "..." }` 時，**禁止使用無差別強制代換**，必須採用「白名單查表機制」：
```python
def make_replacer_func(translations, lang_keys):
    def repl(m):
        prefix = m.group(1)
        raw_text = m.group(2)
        norm = raw_text.replace("\r\n", "\n").replace("\n", "\\n")
        # 僅在翻譯字典中存在此靜態 UI 字串時才替換，否則安全保留原字串
        if norm in translations:
            t_key = lang_keys[norm]
            return f'{prefix}{{ translate: "{t_key}" }}'
        return m.group(0)
    return repl
```

---

## 3. 全球 CDN 部署規範

*   **加速 CDN 網址格式**：必須使用 **`jsDelivr`** 來對 GitHub 倉庫的資源包進行全球代理與 CDN 加速，格式為：
    `https://cdn.jsdelivr.net/gh/<GitHub帳號>/<倉庫名稱>@<分支名>/<資源包路徑.zip>`
*   **同步世界註冊表**：必須同時在伺服器的 `cdn_config.json` 中配置，並同步更新 `worlds/<世界名稱>/world_resource_packs.json` 與 `world_behavior_packs.json` 內對應的版本號，確保玩家進服時自動高速下載。
