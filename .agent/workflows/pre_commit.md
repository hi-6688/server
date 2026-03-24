---
description: 提交前的自動化檢查，確保程式碼品質與文件同步
---
// turbo-all
在 Commit 之前，依序執行以下檢查：

### 1. 檢查 Git 狀態
```bash
cd /home/terraria/servers && git status
```
確認變更的檔案範圍合理，沒有意外的檔案被改到。

### 2. 確認無敏感資訊洩漏
```bash
cd /home/terraria/servers && git diff --cached | grep -iE "(password|token|secret|api_key)" || echo "✅ 未發現敏感資訊"
```
如果發現敏感資訊，**立即停止並通知使用者**。

### 3. 檢查 Python 語法
```bash
cd /home/terraria/servers && python3 -m py_compile web_interface/api.py && echo "✅ api.py 語法正確"
```

### 4. 確認文件是否需要同步
檢查本次修改是否涉及以下任一項，若是則提醒使用者是否要先跑 `/sync_docs`：
- 新增/刪除/移動了檔案
- 修改了 API 路由
- 修改了前端元件結構
- 修改了 VM 通訊邏輯

### 5. 回報結果
將所有檢查結果彙報給使用者，確認後再執行 `git commit`。
