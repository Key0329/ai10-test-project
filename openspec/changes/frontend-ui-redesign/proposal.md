## Why

目前前端介面採用全深色 terminal 風格（全 monospace 字體、#0a0a0b 背景、極低對比度邊框），雖然功能完整但視覺上偏「工程師工具」感。需要提升介面質感，改為 GitHub 風格的深淺混搭設計，讓畫面簡單俐落且具備一定的設計感。

## What Changes

- 將頁面主體從深色改為淺色背景（白底 + 淺灰次背景）
- 字體策略從全 monospace 改為 sans-serif（UI 元素）+ monospace（程式碼/log）混搭
- Log viewer 保持深色背景，維持技術感
- 配色系統全面更新：淺色底、深色文字、精緻邊框與 subtle shadow
- 所有頁面（Dashboard、NewJob、JobDetail、TokenGate）的視覺樣式統一調整
- 不引入 UI 框架，維持手寫 CSS

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

（無 — 此變更僅涉及視覺樣式調整，不改變任何 spec 層級的行為需求）

## Impact

- 受影響的程式碼：
  - `frontend/src/app.css` — 全局樣式重寫（配色、字體、元件樣式）
  - `frontend/index.html` — 字體引用更新
  - `frontend/src/App.vue` — header 樣式可能微調
  - `frontend/src/pages/Dashboard.vue` — 卡片、統計區塊樣式
  - `frontend/src/pages/NewJob.vue` — 表單樣式
  - `frontend/src/pages/JobDetail.vue` — detail meta + log viewer 樣式
  - `frontend/src/components/StatusBadge.vue` — badge 配色
  - `frontend/src/components/TokenGate.vue` — 登入頁樣式
- 無 API、路由、依賴項變更
