## Context

現有前端為 React 18 + Vite 6 專案，共 860 行、9 個檔案。使用手寫 hash-based routing、原生 fetch API、EventSource SSE 串流。無狀態管理庫（僅 useState）。Vite 已作為 bundler 使用，dev proxy 設定指向 `http://localhost:8000`。

## Goals / Non-Goals

**Goals:**

- 將前端框架從 React 替換為 Vue 3 + Vue Router
- 保持所有現有功能不變（Dashboard、New Job、Job Detail、Token Gate、SSE log 串流）
- 保留 Vite 作為 bundler 和 dev proxy 設定
- 保留 `api.js`（純 JS）和 `app.css` 幾乎不修改

**Non-Goals:**

- 不引入 Pinia、VueUse 或其他額外函式庫
- 不重新設計 UI 或調整樣式
- 不修改後端 API 或 SSE 端點
- 不新增功能

## Decisions

### 使用 Vue Router hash mode 取代手寫 routing

現有 `App.jsx` 手寫 hash routing（監聽 `hashchange`、手動判斷路徑）。改用 Vue Router 的 `createWebHashHistory` 提供標準化路由，支援路由參數（`:id`）、navigation guard（未來可用於 token 驗證）。

**替代方案**：繼續手寫 hash routing 到 Vue 版本。但 Vue Router 是 Vue 生態標準，3 個頁面已值得使用，且不增加額外複雜度。

### 使用 Vue 3 Composition API（script setup）

所有元件統一使用 `<script setup>` 語法。現有 React 元件使用 hooks（useState、useEffect、useRef），與 Composition API（ref、onMounted、watch）概念一對一對應，轉換直接。

**替代方案**：Options API。但 Composition API 是 Vue 3 推薦寫法，更接近 React hooks 的模式，團隊轉換成本更低。

### api.js 原封保留

`api.js` 是純 JavaScript（fetch + EventSource），不依賴 React。直接搬移到 Vue 專案中，不需修改。

### app.css 直接搬移

樣式使用 class name（如 `.app`、`.header`、`.log-viewer`），不依賴 CSS-in-JS 或 CSS modules。Vue SFC 的 template 使用相同的 class name 即可。

### Token 驗證移至 Vue Router navigation guard

現有 `TokenGate` 元件包裹整個 App，未登入時攔截。在 Vue 版本中，將 token 檢查移至 Vue Router 的 `beforeEach` guard，未登入時導向 `/login` 頁面。`TokenGate` 改為獨立頁面而非包裹元件。

## Risks / Trade-offs

- **遷移期間前端不可用** → 前端規模小（860 行），一次性完成遷移，不需要漸進式遷移策略
- **Vue Router 路由結構變更** → hash mode 對外表現一致（`#/`、`#/new`、`#/jobs/:id`），使用者無感
- **SSE EventSource 相容性** → `api.js` 不依賴框架，搬移後行為完全一致
