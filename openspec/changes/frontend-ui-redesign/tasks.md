## 1. 配色系統與字體策略

- [x] 1.1 更新 `app.css` 的 CSS 變數，實現 Light-dark mixed theme with dual font strategy（淺色配色、背景、文字、邊框、強調色）
- [x] 1.2 更新 `app.css` 的字體策略，UI 元素改為 system-ui sans-serif，code 元素保留 monospace
- [x] 1.3 更新 `index.html` 的 body 基礎樣式（背景色、字體 fallback）

## 2. 全局元件樣式

- [x] [P] 2.1 更新 `app.css` 中 header 樣式（淺色底、sans-serif 字體）
- [x] [P] 2.2 更新 `app.css` 中 nav-btn 按鈕樣式適配淺色主題
- [x] [P] 2.3 更新 `app.css` 中卡片樣式，套用 subtle shadow + 細邊框（配色系統 + 卡片樣式）
- [x] [P] 2.4 更新 `app.css` 中表單元素樣式（input、select、textarea、btn）適配淺色主題
- [x] [P] 2.5 更新 `app.css` 中 status badge 配色適配淺色背景
- [x] [P] 2.6 更新 `app.css` 中 stat-card、filter-btn 樣式適配淺色主題
- [x] [P] 2.7 更新 `app.css` 中 alert、empty state 樣式適配淺色主題
- [x] [P] 2.8 更新 `app.css` 中 detail page meta 區塊樣式適配淺色主題
- [x] [P] 2.9 更新 `app.css` 中 token-gate 頁面樣式適配淺色主題

## 3. Log viewer 保持深色

- [x] 3.1 確認 `app.css` 中 log-viewer 維持深色背景（#0d1117），調整邊框與圓角讓深淺過渡自然（Log viewer 保持深色）

## 4. Vue 元件 inline style 修正

- [x] [P] 4.1 檢查並更新 `Dashboard.vue` 中 inline style 的硬編碼顏色，改用 CSS 變數
- [x] [P] 4.2 檢查並更新 `JobDetail.vue` 中 inline style 的硬編碼顏色，改用 CSS 變數
- [x] [P] 4.3 檢查並更新 `NewJob.vue` 中 inline style 的硬編碼顏色，改用 CSS 變數

## 5. 修改範圍限定驗證

- [x] 5.1 啟動 dev server 驗證所有頁面在淺色主題下的視覺一致性
