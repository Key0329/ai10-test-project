## Why

每次 Job 執行都會 `git clone` 到 `~/claude-workspace/` 下的獨立目錄，但 Job 結束後這些目錄永遠不會被清理。隨著 Job 數量累積（尤其有 rerun 機制後），磁碟空間會被大量佔用。這些 work_dir 在 Job 結束後不再被使用——所有重要資訊（logs、PR、Jira Comment）都已保存在其他地方。

## What Changes

- Job 執行結束後（不論 completed / failed / cancelled）自動刪除 `work_dir`
- 刪除失敗時記錄 log，不影響 Job 狀態（非致命錯誤）

## Capabilities

### New Capabilities

- `workdir-cleanup`: Job 完成後自動清理 clone 目錄

### Modified Capabilities

（無）

## Impact

- 受影響的程式碼：`backend/services/executor.py` — 在 `execute_job` 結尾加入 cleanup 邏輯
- 不影響 API、前端、Queue、DB schema
