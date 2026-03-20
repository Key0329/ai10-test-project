## 1. 實作

- [x] 1.1 在 `backend/services/executor.py` 的 `execute_job` 結尾加入在 finally 區塊執行 cleanup，實現 automatic work directory cleanup after job execution，使用 `os.path.exists` 檢查後 `shutil.rmtree(work_dir)` 刪除，cleanup 失敗為非致命錯誤（try/except 包住，記 log 不改變 job 狀態）

## 2. 測試

- [x] 1.2 撰寫測試驗證：cleanup after successful job、cleanup after failed job、cleanup when work_dir does not exist、cleanup failure is non-fatal（清理失敗為非致命錯誤：cleanup fails due to permission error 時 job status preserved after cleanup failure）
