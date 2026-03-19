## 1. 專案基礎設定

- [x] 1.1 Package dependencies：更新 `package.json`，移除 react/react-dom/@vitejs/plugin-react，加入 vue/vue-router/@vitejs/plugin-vue，執行 npm install
- [ ] 1.2 Vite configuration for Vue：更新 `vite.config.js`，將 plugin 從 react 改為 vue，保留 dev proxy 設定
- [ ] 1.3 更新 `index.html` 的 mount point 和 script entry（從 main.jsx 改為 main.js）

## 2. 路由與入口

- [ ] 2.1 使用 Vue Router hash mode 取代手寫 routing：建立 `src/router.js` 實現 Vue Router hash mode routing（createWebHashHistory），定義 `/`、`/new`、`/jobs/:id`、`/login` 四條路由
- [ ] 2.2 建立 `src/main.js` Vue app entry，掛載 router 和 App 元件
- [ ] 2.3 Token 驗證移至 Vue Router navigation guard：在 router 加入 beforeEach guard 實現 token authentication via navigation guard，未登入時導向 `/login`

## 3. 共用元件（Vue 3 SFC component architecture，使用 Vue 3 Composition API（script setup））

- [ ] [P] 3.1 改寫 `StatusBadge.vue`（Vue 3 SFC component architecture + script setup Composition API）
- [ ] [P] 3.2 改寫 `TokenGate.vue`（改為獨立頁面元件，對應 `/login` 路由）

## 4. 頁面元件（Vue 3 SFC component architecture，使用 Vue 3 Composition API（script setup））

- [ ] [P] 4.1 改寫 `Dashboard.vue`（Vue 3 SFC component architecture + script setup Composition API）
- [ ] [P] 4.2 改寫 `NewJob.vue`（Vue 3 SFC component architecture + script setup Composition API）
- [ ] [P] 4.3 改寫 `JobDetail.vue`，包含 SSE log streaming in Vue（EventSource 連線、解析 JSON 事件、log filter buttons 篩選功能）

## 5. App 外殼

- [ ] 5.1 建立 `App.vue`（header + router-view），保留現有 header 樣式和導航

## 6. 搬移靜態資源

- [ ] [P] 6.1 api.js 原封保留：搬移 `api.js`（無需修改，純 fetch + EventSource）
- [ ] [P] 6.2 app.css 直接搬移：搬移 `app.css`（無需修改）

## 7. 清理與驗證

- [ ] 7.1 刪除所有 React 相關檔案（*.jsx、舊 main.jsx）
- [ ] 7.2 驗證 `npm run build` 成功且無錯誤
- [ ] 7.3 驗證 `npm run dev` 能啟動並正確 proxy 到後端
