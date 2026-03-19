## Why

團隊更熟悉 Vue 生態系，且後續前端會持續擴展功能。現有 React 前端僅 860 行、9 個檔案，趁規模小時遷移成本最低。遷移至 Vue 3 + Vue Router 可提升團隊維護效率與開發體驗。

## What Changes

- **BREAKING** `frontend/` 目錄重建為 Vue 3 + Vite 專案
- 3 個頁面元件（Dashboard、NewJob、JobDetail）從 JSX 改寫為 Vue SFC（`.vue`）
- 2 個共用元件（TokenGate、StatusBadge）從 JSX 改寫為 Vue SFC
- 手寫 hash-based routing 改用 Vue Router（hash mode）
- `api.js` 搬移（純 fetch + EventSource，無框架依賴，幾乎不需修改）
- `app.css` 直接搬移
- `package.json` 依賴從 react/react-dom 替換為 vue/vue-router
- 不引入 Pinia 或 VueUse（目前不需要，之後按需加入）

## Capabilities

### New Capabilities

- `vue-frontend`: Vue 3 SFC 前端架構，包含 Vue Router hash mode 路由、頁面元件、共用元件

### Modified Capabilities

（無——後端 API、SSE 端點、資料庫結構完全不變）

## Impact

- 影響的程式碼：
  - `frontend/src/` — 全部檔案重寫（App、pages、components、main entry）
  - `frontend/package.json` — 依賴替換
  - `frontend/vite.config.js` — 從 React plugin 改為 Vue plugin
  - `frontend/index.html` — mount point 調整
- 不影響：`backend/`、`docs/`、`.env.example`、`setup.sh`
