## 1. 分離 Jira email 的儲存層

- [x] 1.1 在 `useCredentials.js` 中，將 `jira_email` 的初始化從 `sessionStorage.getItem` 改為 `localStorage.getItem`
- [x] 1.2 在 `save()` 函數中，將 `jira_email` 的寫入從 `sessionStorage.setItem` 改為 `localStorage.setItem`（credential storage strategy）

## 2. 驗證

- [x] 2.1 手動驗證：輸入 Jira email 後關閉分頁再重開，確認 email 仍存在
- [x] 2.2 手動驗證：輸入 GitHub token 和 Jira API token 後關閉分頁再重開，確認兩者已清除
