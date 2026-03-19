## Context

目前前端採用全深色 terminal 風格（`#0a0a0b` 背景、全 monospace 字體、極低對比度），架構為 Vue 3 + Vite + vue-router，純手寫 CSS（`app.css` 約 180 行）。共 4 個頁面：Dashboard、NewJob、JobDetail、TokenGate，2 個共用元件：StatusBadge、TokenGate。

此變更僅涉及視覺樣式層，不改動任何功能邏輯、API 呼叫、路由或元件結構。

## Goals / Non-Goals

**Goals:**

- 將主體區域改為淺色背景，提升閱讀性
- 採用 sans-serif + monospace 混合字體策略，拉開內容層次
- Log viewer 保持深色背景，維持技術感
- 更新配色系統：淺色底、精緻邊框、subtle shadow
- 維持手寫 CSS，不引入 UI 框架

**Non-Goals:**

- 不改動元件結構或新增 .vue 檔案
- 不改動功能邏輯、API、路由
- 不引入 Tailwind、UI library 或其他 CSS 框架
- 不做 responsive 大改（維持現有 media query）
- 不加入深色/淺色主題切換功能

## Decisions

### 配色系統

採用 GitHub 風格淺色配色：

```
背景：#ffffff（主）/ #f6f8fa（次，頁面底）
文字：#1f2328（主）/ #656d76（次）/ #8b949e（hint）
邊框：#d1d9e0
強調：#2563eb（藍）/ #1a7f37（綠）/ #cf222e（紅）/ #bf8700（黃）
Log viewer：維持 #0d1117 深色底 + 現有 log 行色碼
```

**理由：** GitHub 的配色經過大量驗證，閱讀性好、專業感強，且深色 log viewer 與淺色 UI 的對比能自然劃分「操作區」與「輸出區」。

### 字體策略

```
UI 層（header、按鈕、label、說明）→ system-ui, -apple-system, sans-serif
Code 層（ticket ID、repo URL、log viewer）→ 'SF Mono', 'Fira Code', monospace
```

**理由：** Sans-serif 用於 UI 元素讓畫面更現代；monospace 保留在程式碼性質的內容上維持可讀性與技術感。不額外引入 web font（如 Inter），使用系統字體確保零額外載入。

### 卡片樣式

從「低對比度邊框」改為「subtle shadow + 細邊框」：

```css
border: 1px solid #d1d9e0;
border-radius: 8px;
background: #ffffff;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
```

hover 時加深 shadow 而非改 border，提供更自然的互動回饋。

**理由：** Shadow 比純邊框提供更好的深度層次感，且在淺色背景上效果更明顯。

### Log viewer 保持深色

Log viewer 維持 `#0d1117` 背景，tag 色碼保持不變。這是唯一的深色區塊。

**理由：** Log 本質是終端輸出，深色背景是最自然的呈現方式，也能與淺色主體形成清楚的視覺分區。

### 修改範圍限定

所有樣式變更集中在 `app.css` + `index.html`（字體 fallback），各 `.vue` 檔案中的 inline style 配合 CSS 變數即可自動生效，盡量不改動 template。

**理由：** 集中修改降低變更風險，CSS 變數機制讓改動自動傳播到各元件。

## Risks / Trade-offs

- **[風險] inline style 中硬編碼的顏色不會隨 CSS 變數更新** → 需逐一檢查各 .vue 檔中的 `style="color: var(--...)"` 是否仍然適用於淺色背景，部分可能需要更新變數名或值。
- **[風險] 深色 log viewer 與淺色背景的接合處可能突兀** → 使用 border-radius + 內縮 padding 讓過渡自然。
- **[取捨] 不加入主題切換** → 簡化實作，但未來若需深色模式需重新設計 CSS 變數結構。目前為內部工具，不需要此功能。
