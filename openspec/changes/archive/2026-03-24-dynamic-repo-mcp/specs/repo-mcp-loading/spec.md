## ADDED Requirements

### Requirement: Load MCP configuration from repo .mcp.json

The system SHALL read the `.mcp.json` file from the root of a cloned repository and parse the `mcpServers` object. If the file does not exist or fails to parse, the system SHALL return an empty configuration without error.

#### Scenario: Repo has valid .mcp.json

- **WHEN** the cloned repo contains a `.mcp.json` with a valid `mcpServers` object
- **THEN** the system SHALL return all server definitions from the `mcpServers` object

#### Scenario: Repo has no .mcp.json

- **WHEN** the cloned repo does not contain a `.mcp.json` file
- **THEN** the system SHALL return an empty configuration

#### Scenario: Repo has malformed .mcp.json

- **WHEN** the cloned repo contains a `.mcp.json` that fails JSON parsing
- **THEN** the system SHALL log a warning and return an empty configuration

---

### Requirement: Convert .mcp.json format to Copilot SDK format

The system SHALL convert `.mcp.json` server definitions to Copilot SDK `mcp_servers` format using the following mapping:

- `type: "stdio"` SHALL map to `type: "local"`
- `type: "sse"` or `type: "streamable-http"` SHALL map to `type: "http"`
- `command` and `args` fields SHALL be preserved
- `tools` field SHALL default to `["*"]` when not specified
- `env` field SHALL be preserved when present

#### Scenario: Convert stdio server to local

- **WHEN** a `.mcp.json` entry has `type: "stdio"` with `command: "npx"` and `args: ["-y", "@some/mcp"]`
- **THEN** the converted output SHALL have `type: "local"`, `command: "npx"`, `args: ["-y", "@some/mcp"]`, and `tools: ["*"]`

#### Scenario: Convert sse server to http

- **WHEN** a `.mcp.json` entry has `type: "sse"` with `url: "http://localhost:3000/mcp"`
- **THEN** the converted output SHALL have `type: "http"` and `url: "http://localhost:3000/mcp"`

---

### Requirement: Expand environment variable references

The system SHALL expand `${VAR_NAME}` references in `args`, `env` values, and `url` fields using actual environment variables or provided overrides.

#### Scenario: Environment variable defined

- **WHEN** a server arg contains `${SENTRY_TOKEN}` and the environment variable `SENTRY_TOKEN` is set to `abc123`
- **THEN** the expanded arg SHALL contain `abc123`

#### Scenario: Environment variable undefined

- **WHEN** a server arg contains `${MISSING_VAR}` and the environment variable is not set
- **THEN** the system SHALL preserve the `${MISSING_VAR}` literal and report it via missing env var detection

---

### Requirement: Detect missing environment variables

The system SHALL scan all `${VAR_NAME}` references in server definitions and report which environment variables are not defined.

#### Scenario: All variables defined

- **WHEN** all `${VAR_NAME}` references resolve to defined environment variables
- **THEN** the detection SHALL return an empty list

#### Scenario: Some variables missing

- **WHEN** `${API_KEY}` is referenced but not defined in the environment
- **THEN** the detection SHALL return a list containing `API_KEY`

---

### Requirement: Merge repo MCP config with supplemental MCP

The Copilot executor SHALL merge repo `.mcp.json` configuration (primary) with user-selected supplemental MCP from the built-in registry (secondary). When both sources define a server with the same name, the repo version SHALL take priority.

#### Scenario: Repo and supplemental have no overlap

- **WHEN** repo defines `context7` and user supplements `figma`
- **THEN** the final config SHALL contain both `context7` and `figma`

#### Scenario: Repo and supplemental have overlapping server name

- **WHEN** repo defines `context7` with specific args and user supplements `context7` from the built-in registry
- **THEN** the final config SHALL use the repo version of `context7`

---

### Requirement: Log .mcp.json detection in repo verification

Both the Claude Code executor and Copilot executor SHALL log the `.mcp.json` detection result during repo verification, including the number of MCP servers found and their names.

#### Scenario: .mcp.json detected with servers

- **WHEN** the cloned repo contains a `.mcp.json` with 3 MCP servers named `context7`, `sentry`, `figma`
- **THEN** the verification log SHALL include a message indicating 3 MCP servers found and list their names

#### Scenario: .mcp.json not found

- **WHEN** the cloned repo does not contain a `.mcp.json`
- **THEN** the verification log SHALL include a message indicating no `.mcp.json` was found
