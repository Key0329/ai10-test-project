## ADDED Requirements

### Requirement: Vue 3 SFC component architecture

All frontend page and shared components SHALL be implemented as Vue 3 Single File Components (`.vue`) using `<script setup>` Composition API syntax.

#### Scenario: Page components are Vue SFCs

- **WHEN** the frontend source is inspected
- **THEN** Dashboard, NewJob, and JobDetail SHALL each be a `.vue` file using `<script setup>`

#### Scenario: Shared components are Vue SFCs

- **WHEN** the frontend source is inspected
- **THEN** TokenGate and StatusBadge SHALL each be a `.vue` file using `<script setup>`

---

### Requirement: Vue Router hash mode routing

The frontend SHALL use Vue Router with `createWebHashHistory` to handle client-side routing. Routes SHALL match the existing hash-based URL structure.

#### Scenario: Route definitions

- **WHEN** the Vue Router is configured
- **THEN** the following routes SHALL be defined: `/` (Dashboard), `/new` (NewJob), `/jobs/:id` (JobDetail), `/login` (TokenGate)

#### Scenario: Job detail route parameter

- **WHEN** the user navigates to `#/jobs/JRA-123-1710000000`
- **THEN** Vue Router SHALL parse `JRA-123-1710000000` as the `id` route parameter and render the JobDetail component

#### Scenario: Default route

- **WHEN** the user visits the app with no hash or `#/`
- **THEN** the Dashboard component SHALL be rendered

---

### Requirement: Token authentication via navigation guard

The frontend SHALL use a Vue Router `beforeEach` navigation guard to check for a stored authentication token. Unauthenticated users SHALL be redirected to the login route.

#### Scenario: No token stored

- **WHEN** a user navigates to any route and no token exists in localStorage
- **THEN** the router SHALL redirect to the `/login` route

#### Scenario: Token exists

- **WHEN** a user navigates to any route and a valid token exists in localStorage
- **THEN** the router SHALL allow navigation to proceed normally

#### Scenario: Login route accessible without token

- **WHEN** a user is on the `/login` route with no token
- **THEN** the router SHALL NOT redirect (avoiding infinite loop)

---

### Requirement: SSE log streaming in Vue

The JobDetail component SHALL consume Server-Sent Events for real-time log streaming, parsing structured JSON events and supporting log type filtering.

#### Scenario: SSE connection established

- **WHEN** the JobDetail component mounts for an active job
- **THEN** it SHALL establish an EventSource connection to `/api/v1/jobs/{id}/logs`

#### Scenario: SSE connection cleanup

- **WHEN** the JobDetail component unmounts or the job finishes
- **THEN** the EventSource connection SHALL be closed

#### Scenario: Log filter buttons

- **WHEN** the user clicks a filter button (All / Assistant / Tools / System)
- **THEN** only log entries matching the selected event_type SHALL be displayed

---

### Requirement: Vite configuration for Vue

The Vite configuration SHALL use `@vitejs/plugin-vue` instead of `@vitejs/plugin-react`, with the existing dev proxy settings preserved.

#### Scenario: Vite plugin

- **WHEN** the Vite config is inspected
- **THEN** it SHALL use `@vitejs/plugin-vue` as the sole framework plugin

#### Scenario: Dev proxy preserved

- **WHEN** the Vite dev server runs
- **THEN** requests to `/api` SHALL be proxied to `http://localhost:8000`

---

### Requirement: Package dependencies

The `package.json` SHALL list `vue` and `vue-router` as dependencies, replacing `react` and `react-dom`. Vite SHALL remain as the build tool.

#### Scenario: Vue dependencies present

- **WHEN** `package.json` is inspected
- **THEN** `vue` and `vue-router` SHALL be listed under dependencies

#### Scenario: React dependencies removed

- **WHEN** `package.json` is inspected
- **THEN** `react`, `react-dom`, and `@vitejs/plugin-react` SHALL NOT be present
