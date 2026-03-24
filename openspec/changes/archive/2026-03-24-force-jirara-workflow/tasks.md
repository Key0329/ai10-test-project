## 1. Claude Code：使用 --append-system-prompt-file 注入 jirara

- [x] [P] 1.1 Jirara 檔案路徑：從專案根目錄動態解析 — 在 `executor.py` 新增 `_PROJECT_ROOT` 和 jirara 路徑常數（Jirara file path resolution）
- [x] [P] 1.2 修改 `build_claude_command()` 加入 `--append-system-prompt-file` 參數，實作 inject Jirara skill via append-system-prompt-file
- [x] 1.3 修改 `build_prompt()` 加入 jirara 優先於 repo dev-flow skills 的指令（Jirara priority over repo dev-flow skills），同時保留 repo non-flow skills remain active

## 2. Copilot SDK：強制覆蓋注入 + prompt 指定優先級

- [x] [P] 2.1 修改 `_inject_system_skills()` 實作 force inject system Jirara skill into Copilot work directory：移除「已存在則跳過」邏輯，改為強制刪除後重新複製（injection source path 從 _PROJECT_ROOT 動態解析）
- [x] [P] 2.2 修改 `_build_system_message()` 加入 Copilot prompt prioritizes Jirara over repo dev-flow skills 指令，同時保留 repo non-flow skills remain active in Copilot mode
- [x] [P] 2.3 修改 `_build_copilot_prompt()` 加入 Jirara priority in user prompt 指令

## 3. 驗證

- [x] 3.1 手動測試 Claude Code 模式：確認 `--append-system-prompt-file` 參數正確帶入
- [x] 3.2 手動測試 Copilot 模式：確認強制覆蓋注入且 prompt 包含 jirara 優先指令
