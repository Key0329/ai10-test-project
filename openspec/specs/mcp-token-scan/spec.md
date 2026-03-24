# mcp-token-scan Specification

## Purpose

TBD - created by archiving change 'dynamic-mcp-token-input'. Update Purpose after archive.

## Requirements

### Requirement: Scan repo .mcp.json via GitHub API

The system SHALL provide a `POST /api/v1/mcp/scan` endpoint that fetches `.mcp.json` from a remote GitHub repository using the GitHub Contents API, without performing a full git clone.

The endpoint SHALL accept `repo_url`, `branch` (optional), and `github_token` as input. It SHALL return the list of MCP server names and the list of `${VAR_NAME}` references that are not defined in the server environment.

#### Scenario: Repo has .mcp.json with undefined variables

- **WHEN** the scan endpoint is called with a valid repo URL and the repo contains a `.mcp.json` referencing `${SENTRY_TOKEN}` and `${API_KEY}`, neither of which is defined
- **THEN** the response SHALL include `missing_vars: ["API_KEY", "SENTRY_TOKEN"]` (sorted) and `servers` listing all MCP server names

#### Scenario: Repo has .mcp.json with all variables defined

- **WHEN** the scan endpoint is called and all `${VAR}` references in the `.mcp.json` resolve to defined environment variables
- **THEN** the response SHALL include `missing_vars: []`

#### Scenario: Repo has no .mcp.json

- **WHEN** the scan endpoint is called and the repo does not contain a `.mcp.json` file
- **THEN** the response SHALL return `missing_vars: []` and `servers: []`

#### Scenario: Branch specified

- **WHEN** the scan endpoint is called with a `branch` parameter
- **THEN** the GitHub API call SHALL fetch `.mcp.json` from that specific branch


<!-- @trace
source: dynamic-mcp-token-input
updated: 2026-03-24
code:
  - backend/models/job.py
  - backend/services/mcp_loader.py
  - backend/routers/mcp.py
  - frontend/src/api.js
  - .github/skills/jirara/SKILL.md
  - .github/skills/jirara/jirara.md
  - backend/services/copilot_executor.py
  - backend/services/executor.py
  - backend/routers/jobs.py
  - frontend/src/pages/NewJob.vue
tests:
  - backend/tests/test_env_overrides.py
  - backend/tests/test_mcp_loader.py
-->

---
### Requirement: Frontend auto-scans on repo selection

The NewJob form SHALL automatically call the scan endpoint when the user selects or changes the repository URL. The call SHALL be debounced to avoid excessive API requests.

#### Scenario: User selects a repo with token-requiring MCP

- **WHEN** the user selects a repo URL and the scan returns `missing_vars: ["SENTRY_TOKEN"]`
- **THEN** the form SHALL display a password input field labeled `SENTRY_TOKEN`

#### Scenario: User selects a repo with no token requirements

- **WHEN** the user selects a repo URL and the scan returns `missing_vars: []`
- **THEN** the form SHALL NOT display any additional token input fields

#### Scenario: Scan fails or repo is private without token

- **WHEN** the scan API call fails (network error, 404, auth error)
- **THEN** the form SHALL silently skip token field generation without blocking job submission

<!-- @trace
source: dynamic-mcp-token-input
updated: 2026-03-24
code:
  - backend/models/job.py
  - backend/services/mcp_loader.py
  - backend/routers/mcp.py
  - frontend/src/api.js
  - .github/skills/jirara/SKILL.md
  - .github/skills/jirara/jirara.md
  - backend/services/copilot_executor.py
  - backend/services/executor.py
  - backend/routers/jobs.py
  - frontend/src/pages/NewJob.vue
tests:
  - backend/tests/test_env_overrides.py
  - backend/tests/test_mcp_loader.py
-->