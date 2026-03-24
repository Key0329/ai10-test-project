## Context

目前 Job 模型有一個 `priority` 欄位（1-5，預設 3），用於 queue 排序。但前端已在 `NewJob.vue` 將整段 priority UI 用 HTML 註解隱藏，所有 job 都以預設值 3 送出，queue 實際行為等同純 FIFO。後端仍在 `queue.py`、`jobs.py` 中維護 priority 排序與 queue_position 計算邏輯。

## Goals / Non-Goals

**Goals:**

- 移除 priority 欄位及相關排序邏輯，簡化為純 FIFO queue
- 清理前端被註解的 priority UI 程式碼
- 更新 spec 與文件以反映新行為

**Non-Goals:**

- 不重構 queue worker 架構（只移除 priority 排序）
- 不變更 DB migration 框架（使用現有 pattern）
- 不移除 queue 機制本身

## Decisions

### 純 FIFO 排序取代 priority 排序

Queue 排序從 `ORDER BY priority ASC, created_at ASC` 改為 `ORDER BY created_at ASC`。Queue position 計算也對應簡化為只比較 `created_at`。

**替代方案**：保留 priority 欄位但硬編碼為 3 — 不採用，因為這只是隱藏複雜度而非消除。

### DB 欄位處理：容許殘留

SQLite 不支援 `DROP COLUMN`（3.35.0 以下），且此專案使用簡易 migration pattern。採用「不刪欄位、不寫入、不讀取」策略：後端不再寫入或讀取 `priority`，schema 中保留欄位但不使用。新建 DB 的 CREATE TABLE 也移除該欄位。

**替代方案**：用 `ALTER TABLE ... DROP COLUMN` — 不採用，因為需要確認 SQLite 版本且增加 migration 風險。

### Model 與 API 清理

`JobCreate` 移除 `priority` 欄位。`JobResponse` 移除 `priority`。INSERT 語句移除 `priority`。這是 breaking change，但因為前端本來就沒在送 priority（UI 被隱藏），實際影響為零。

## Risks / Trade-offs

- [Risk] 外部呼叫者可能依賴 `priority` 參數 → 此為內部工具，無外部 API 消費者，風險極低
- [Risk] 舊 DB 中殘留的 `priority` 欄位 → 不影響運作，SQLite 會忽略未使用的欄位
