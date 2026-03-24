## 1. Model 與 API 清理

- [x] [P] 1.1 移除 `JobCreate` model 中的 `priority` 欄位（backend/models/job.py）
- [x] [P] 1.2 移除 `JobResponse` model 中的 `priority` 欄位（backend/models/job.py）

## 2. 純 FIFO 排序取代 priority 排序 — 移除 priority-based queue ordering，實作 FIFO queue ordering

- [x] 2.1 實作 FIFO queue ordering：修改 queue.py 排序為 `ORDER BY created_at ASC`，移除 priority-based queue ordering
- [x] 2.2 修改 jobs.py `POST /jobs` 的 INSERT 語句，移除 priority 寫入
- [x] 2.3 修改 jobs.py `POST /jobs` 的 queue_position 計算，改為純 FIFO 計數
- [x] [P] 2.4 修改 jobs.py rerun endpoint 的 INSERT 與 queue_position，移除 priority（Rerun API endpoint）

## 3. 前端清理

- [x] [P] 3.1 移除 NewJob.vue 中被註解的 priority HTML 與 form.priority 初始值

## 4. DB schema 處理（DB 欄位處理：容許殘留）

- [x] [P] 4.1 移除 db.py CREATE TABLE 中的 priority 欄位定義（新建 DB 不再有此欄位）

## 5. 文件更新

- [x] [P] 5.1 更新 docs/system-spec.md 移除 priority 相關描述

## 6. 測試

- [x] 6.1 更新現有 rerun 相關測試，移除 priority 斷言
- [x] 6.2 驗證 queue FIFO 排序行為正確
