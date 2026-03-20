## Context

`executor.py` 的 `execute_job` 每次執行會在 `~/claude-workspace/` 下建立 `{jira_ticket}-{timestamp}` 目錄做 git clone。Job 結束後目錄永遠不清理，rerun 機制更加速了累積速度。

## Goals / Non-Goals

**Goals:**

- Job 結束後自動刪除 work_dir，釋放磁碟空間

**Non-Goals:**

- 定期清理排程（不需要，即時清理就夠了）
- SQLite logs 清理（logs 很小，不在此範圍）
- 清理歷史遺留的 work_dir（啟動時掃描舊目錄——未來再做）

## Decisions

### 在 finally 區塊執行 cleanup

在 `execute_job` 的最外層 `try/except` 後加 `finally` 區塊執行 `shutil.rmtree(work_dir)`，確保不論成功、失敗、取消都會清理。

**理由：** `finally` 保證一定會執行，不需要在 completed/failed/exception 每個分支都加清理邏輯。

**替代方案：** 在每個狀態更新後分別清理——重複且容易遺漏。

### 清理失敗為非致命錯誤

`shutil.rmtree` 失敗時（權限問題、檔案被鎖）只記 log，不改變 job 狀態。

**理由：** 清理是附帶操作，不該影響 job 的成功/失敗判定。用 `try/except` 包住 rmtree，記一筆 warning log。

## Risks / Trade-offs

- **work_dir 不存在**（clone 階段就失敗）→ `shutil.rmtree` 前先 `os.path.exists` 檢查
- **檔案被其他 process 鎖住** → 記 log 跳過，下次手動清理即可
