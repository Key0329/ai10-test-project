## 1. 資料庫與資料模型

- [x] [P] 1.1 在 `backend/db.py` 的 `CREATE_JOBS_TABLE` 加入 parent_job_id 為 nullable 欄位，並新增 database migration for parent_job_id 函數（參照 `_migrate_job_logs` 模式），在 `init_db` 中呼叫
- [x] [P] 1.2 在 `backend/models/job.py` 的 `JobResponse` 新增 `parent_job_id: Optional[str] = None` 欄位，實現 parent job ID tracking

## 2. Rerun API

- [x] 2.1 在 `backend/routers/jobs.py` 新增 `POST /api/v1/jobs/{id}/rerun` 作為 rerun API 為獨立端點，複製原 Job 參數建立新 Job（rerun 建立新 Job 而非 reset 原 Job），設定 `parent_job_id`，驗證原 Job 狀態須為 completed/failed（rerun blocked for active job），檢查同 ticket 無 active Job（rerun blocked when same ticket already active），處理 rerun of non-existent job 回傳 404
- [x] 2.2 更新 `create_job` 與 `get_job` 等現有端點的 `JobResponse` 建構，補上 `parent_job_id` 欄位（first job has no parent / rerun job has parent reference）

## 3. Rerun Chain 查詢

- [x] 3.1 在 `backend/routers/jobs.py` 新增 `GET /api/v1/jobs/{id}/chain` rerun chain query 端點，回傳該 Job 所屬 rerun chain 的所有 Job（從首輪到最新），各含 job_id 與 status

## 4. 前端 API 與 UI

- [x] [P] 4.1 在 `frontend/src/api.js` 新增 `rerunJob(jobId)` rerun API client function
- [x] 4.2 在 `frontend/src/pages/JobDetail.vue` 新增 rerun button on JobDetail page，僅在 completed/failed 狀態顯示，點擊後呼叫 rerunJob 並導向新 Job 頁面，處理 409 duplicate 錯誤顯示（rerun button visible / hidden / successful rerun navigation / rerun blocked by duplicate）
- [x] 4.3 在 `frontend/src/pages/JobDetail.vue` 實作 rerun chain navigation，顯示輪次編號與前後輪連結（前端輪次導航以連結串顯示）（first run with no reruns / rerun job shows run number and parent link / parent job with child shows next link）

## 5. 測試

- [x] [P] 5.1 撰寫 rerun API endpoint 測試：成功 rerun（completed/failed）、active job 拒絕、duplicate ticket 拒絕、不存在 job 404
- [x] [P] 5.2 撰寫 rerun chain query 測試：單一 Job 無 chain、多輪 rerun chain 正確排序
- [x] [P] 5.3 撰寫 database migration for parent_job_id 測試：既有資料庫升級、全新資料庫建立
