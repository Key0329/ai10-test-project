## MODIFIED Requirements

### Requirement: MCP section displays supplemental role label

The NewJob form SHALL display a data-driven MCP detection summary when the repo scan detects MCP servers. The summary SHALL show the number of detected servers and their names. When no servers are detected or no scan has been performed, the MCP section SHALL NOT be displayed.

#### Scenario: Repo has MCP servers

- **WHEN** the scan returns servers `["context7", "sentry", "figma"]`
- **THEN** the form SHALL display a summary reading "偵測到 3 個 MCP servers：context7, sentry, figma"

#### Scenario: Repo has no MCP servers

- **WHEN** the scan returns `servers: []`
- **THEN** the form SHALL NOT display any MCP summary section

#### Scenario: Scan not yet performed

- **WHEN** no repo URL has been selected or the scan has not completed
- **THEN** the form SHALL NOT display any MCP summary section

#### Scenario: Summary is engine-agnostic

- **WHEN** the user is in Claude Code mode or Copilot mode and the scan returns servers
- **THEN** the MCP summary SHALL be displayed identically regardless of engine mode

## REMOVED Requirements

### Requirement: Dynamic MCP token input fields

**Reason**: The built-in MCP selection UI (checkbox list, connection test, token input for system-provided MCPs) is removed. Token input for repo `.mcp.json` environment variables remains in the `mcp-token-scan` capability scope, not here.

**Migration**: Token input for MCP servers is handled exclusively through the repo `.mcp.json` scan flow (env_overrides). No separate built-in MCP token UI is needed.

#### Scenario: Built-in MCP UI no longer appears

- **WHEN** the user opens the NewJob form in any engine mode
- **THEN** the form SHALL NOT display checkboxes, connection test indicators, or token input fields for system-provided built-in MCPs
