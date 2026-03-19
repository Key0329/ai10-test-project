## 1. 資料庫 Schema 擴展

- [x] 1.1 job_logs 表新增 event_type 和 metadata 欄位：在 `db.py` 新增 `event_type TEXT DEFAULT 'raw'` 和 `metadata TEXT`（extended job_logs schema），確保向下相容既有 log 資料

## 2. Executor CLI 命令更新

- [x] [P] 2.1 在 `build_claude_command` 中加入 `--output-format stream-json` 旗標（stream JSON output from Claude CLI）
- [x] [P] 2.2 max-turns 設為 50 搭配現有 timeout 作為雙重保護：新增 `MAX_TURNS` 環境變數（預設 50），在 `build_claude_command` 中加入 `--max-turns` 旗標（max turns limit / configurable via environment）
- [x] [P] 2.3 fallback-model 使用 sonnet 作為降級目標：新增 `FALLBACK_MODEL` 環境變數（預設 `sonnet`），在 `build_claude_command` 中加入 `--fallback-model` 旗標（fallback model / configurable via environment）
- [x] [P] 2.4 更新 `.env.example` 加入 `MAX_TURNS` 和 `FALLBACK_MODEL` 範例

## 3. Executor 輸出解析

- [x] 3.1 重構 `_stream_output` 為 JSON 事件解析模式：嘗試 parse 每行 JSON 並提取 `type` 欄位作為 `event_type`，失敗時 fallback 為 raw 文字（parse and classify JSON events）
- [x] 3.2 更新 `_log` 函式簽名，支援 `event_type` 和 `metadata` 參數寫入新欄位

## 4. SSE 端點調整

- [x] 4.1 更新 `routers/jobs.py` 的 SSE log 端點，回傳 `event_type` 和 `metadata` 欄位供前端使用

## 5. 前端 Log 顯示（使用 stream-json 輸出格式取代原始文字）

- [x] 5.1 更新 `JobDetail.jsx` 解析 SSE 事件中的 `event_type` 欄位
- [x] 5.2 前端 log 分類顯示：加入篩選功能（全部 / assistant 回應 / tool 操作 / 系統訊息）

## 6. 測試與文件

- [x] [P] 6.1 撰寫 `build_claude_command` 單元測試，驗證 inject Jirara skill via append-system-prompt-file 以及新增的三個旗標
- [x] [P] 6.2 撰寫 `_stream_output` 單元測試，驗證 JSON 解析與 fallback 行為（parse and classify JSON events / backward compatibility with existing logs）
- [x] 6.3 更新 `docs/system-spec.md` 說明新增的 CLI 旗標和結構化輸出機制
