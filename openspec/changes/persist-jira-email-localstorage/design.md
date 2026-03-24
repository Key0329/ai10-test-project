## Context

目前 `useCredentials.js` composable 將三個憑證（GitHub token、Jira API token、Jira email）統一存放在 sessionStorage，關閉分頁即清除。使用者反映每次重開都要重新輸入 Jira email 很不方便，而 email 不屬於機密資訊，適合持久化。

現有程式碼結構：
- `useCredentials.js` 使用統一的 `save()` 函數同時寫入三個值到 sessionStorage
- 初始化時從 sessionStorage 讀取

## Goals / Non-Goals

**Goals:**

- Jira email 改用 localStorage 持久化儲存，關閉瀏覽器後仍保留
- GitHub token 與 Jira API token 維持 sessionStorage，不降低安全性

**Non-Goals:**

- 不加入「記住我」checkbox 或其他 UI 變更
- 不改變 token 傳遞給後端的方式

## Decisions

### 分離 Jira email 的儲存層

在 `useCredentials.js` 中，將 Jira email 的讀取和寫入改用 `localStorage`，其餘兩個 token 維持 `sessionStorage`。不需要額外的抽象層，直接在 `save()` 和初始化區塊分別呼叫不同的 storage API。

**理由**：變動範圍最小，只改一個檔案中的幾行，不影響其他元件的使用方式。

## Risks / Trade-offs

- [風險] localStorage 資料不會自動過期 → 影響低，email 不是機密資訊，且使用者可隨時在 Dashboard 修改覆蓋
