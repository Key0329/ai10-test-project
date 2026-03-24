## Why

使用者每次關閉瀏覽器分頁後，都必須重新輸入 Jira email，造成不便。Jira email 不屬於機密資訊，適合使用 localStorage 持久化儲存，減少重複輸入的摩擦。GitHub token 和 Jira API token 因安全考量維持 sessionStorage。

## What Changes

- 將 Jira email 的儲存方式從 sessionStorage 改為 localStorage
- GitHub token 和 Jira API token 維持 sessionStorage 不變

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `vue-frontend`: credential 儲存策略調整 — Jira email 改用 localStorage 持久化

## Impact

- 受影響程式碼：`frontend/src/composables/useCredentials.js`
- 無 API 變更、無後端變更
