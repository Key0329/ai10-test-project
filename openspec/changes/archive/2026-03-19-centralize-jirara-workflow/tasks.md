## 1. Executor 核心改造

- [x] 1.1 [P] 修改 executor.py：使用 --append-system-prompt-file 注入 Jirara skill，將 jirara.md 路徑以絕對路徑傳入 Claude Code CLI 呼叫（對應設計決策「使用 --append-system-prompt-file 注入 Jirara」與「Jirara 檔案路徑使用絕對路徑」）
- [x] 1.2 [P] 修改 executor.py：簡化 executor prompt，移除 callback API 相關指令，僅保留 Jira 單號指令與 extra_prompt（對應設計決策「保留 callback router 但不主動呼叫」）
- [x] 1.3 修改 executor.py：新增 validate Jirara file existence on startup 邏輯，在模組載入時驗證 jirara.md 檔案存在，不存在則 raise RuntimeError（對應設計決策「直接使用含 frontmatter 的 jirara.md」）

## 2. 測試

- [x] 2.1 撰寫測試：驗證 inject Jirara skill via append-system-prompt-file 的 CLI 參數組裝正確
- [x] 2.2 撰寫測試：驗證 simplified executor prompt 不包含 callback 指令，且正確處理 extra_prompt
- [x] 2.3 撰寫測試：驗證 Jirara 檔案不存在時拋出正確錯誤
- [x] 2.4 撰寫測試：驗證 backward compatibility with repo CLAUDE.md（確認 CLI 指令未修改 cloned repo 內容）

## 3. 文件更新

- [x] 3.1 [P] Update system-spec.md for uv and Jirara workflow：更新技術選型表格、Section 5 執行細節、Section 8 部署步驟
- [x] 3.2 [P] 更新 .env.example：如有需要新增 Jirara 相關環境變數說明
