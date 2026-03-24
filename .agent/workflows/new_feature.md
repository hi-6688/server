---
description: 開發新功能的標準流程，確保架構一致性與品質
---
請完全依照以下步驟執行：

### 第一階段：需求理解
1. **確認需求**：詢問使用者具體要做什麼功能，釐清範圍。
2. **閱讀相關文件**：根據功能類型，閱讀對應的 `docs/` 手冊：
   - 前端相關 → `docs/FRONTEND_ARCH.md`
   - 後端相關 → `docs/BACKEND_API.md`
   - VM 通訊相關 → `docs/VM_ARCHITECTURE.md`
   - Discord Bot → `docs/HiHi_Proposal.md`

### 第二階段：架構規劃
3. **提出實作方案**：列出需要新增/修改的檔案與邏輯，**等待使用者確認再動手**。
4. **建立功能分支**：
// turbo
```bash
git checkout -b feature/<功能名稱>
```

### 第三階段：分步實作
5. **後端優先**：先寫 API / 資料模型 / 路由。
6. **前端其次**：再寫 UI 元件，參考現有元件的風格。
7. **整合測試**：用 `curl` 測試 API，請使用者在瀏覽器確認 UI。
8. **每一步都等使用者確認**，不要一次做完所有事。

### 第四階段：收尾
9. **同步文件**：執行 `/sync_docs` 更新架構手冊。
10. **Commit**：
// turbo
```bash
git add -A && git commit -m "feat(<範圍>): <簡短描述>"
```
11. **合併回 dev**：（若功能完成且穩定）
```bash
git checkout dev && git merge feature/<功能名稱>
```
