## ADDED Requirements

### Requirement: MCP section displays supplemental role label

The NewJob form MCP configuration section SHALL display a label indicating that repo `.mcp.json` is automatically loaded and the section is for supplemental MCP servers only. The label text SHALL read "額外 MCP（補充 repo 設定）".

#### Scenario: Copilot mode MCP section header

- **WHEN** the user selects Copilot mode in the NewJob form
- **THEN** the MCP section header SHALL display "額外 MCP（補充 repo 設定）"

#### Scenario: Claude Code mode MCP info

- **WHEN** the user selects Claude Code mode in the NewJob form
- **THEN** the form SHALL display an informational text stating that MCP configuration is loaded from the repo `.mcp.json` by the CLI automatically
