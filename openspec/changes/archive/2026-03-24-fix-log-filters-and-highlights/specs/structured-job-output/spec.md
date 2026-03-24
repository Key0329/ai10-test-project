## ADDED Requirements

### Requirement: Copilot executor tool event classification

The Copilot executor SHALL classify tool execution events with the same event_type scheme as the Claude Code executor.

#### Scenario: Copilot tool execution start for regular tool

- **WHEN** a `tool.execution_start` event is received for a non-MCP tool
- **THEN** the log entry SHALL be stored with `event_type` = `tool_use`

#### Scenario: Copilot tool execution complete for regular tool

- **WHEN** a `tool.execution_complete` event is received for a non-MCP tool with a result
- **THEN** the log entry SHALL be stored with `event_type` = `tool_result`

#### Scenario: Copilot tool execution progress

- **WHEN** a `tool.execution_progress` event is received for a non-MCP tool
- **THEN** the log entry SHALL be stored with `event_type` = `tool_use`

#### Scenario: Copilot MCP tool events unchanged

- **WHEN** a `tool.execution_start` event is received for a tool whose name starts with `mcp__`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp` (unchanged behavior)

---

## MODIFIED Requirements

### Requirement: Preserve backward compatibility for existing event types

The executor SHALL classify non-MCP, non-Skill tool_use blocks as `event_type` = `tool_use` with the `[tool]` prefix. User events (tool results) SHALL be classified as `event_type` = `tool_result`. Pure assistant text (no tool_use blocks) SHALL remain `event_type` = `assistant`.

#### Scenario: Regular tool call classified as tool_use

- **WHEN** an assistant event contains only tool_use blocks (no text blocks) with name `Bash`
- **THEN** the log entry SHALL be stored with `event_type` = `tool_use` and message prefixed with `[tool]`

#### Scenario: Tool result classified as tool_result

- **WHEN** a user event (tool result) is received
- **THEN** the log entry SHALL be stored with `event_type` = `tool_result`

#### Scenario: Pure assistant text remains assistant

- **WHEN** an assistant event contains only text blocks (no tool_use blocks)
- **THEN** the log entry SHALL be stored with `event_type` = `assistant`

#### Scenario: Mixed text and tool_use blocks

- **WHEN** an assistant event contains both text blocks and non-MCP, non-Skill tool_use blocks
- **THEN** the log entry SHALL be stored with `event_type` = `tool_use` (tool operations take priority over text)

#### Scenario: MCP and Skill priority unchanged

- **WHEN** an assistant event contains MCP tool_use blocks (name starts with `mcp__`)
- **THEN** the log entry SHALL be stored with `event_type` = `mcp` (highest priority, unchanged behavior)

---

### Requirement: Classify MCP tool calls as mcp event type

The executor SHALL classify tool_use blocks whose `name` starts with `mcp__` as `event_type` = `mcp` and prefix the display message with `[mcp]` instead of `[tool]`.

#### Scenario: MCP tool call detected

- **WHEN** an assistant event contains a tool_use block with name `mcp__github__create_pr`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp` and message prefixed with `[mcp]`

#### Scenario: Multiple tool_use blocks with mixed types

- **WHEN** an assistant event contains both a regular tool_use (e.g., `Bash`) and an MCP tool_use (e.g., `mcp__github__list_prs`)
- **THEN** the log entry SHALL use the highest priority event_type (`mcp` > `skill` > `tool_use` > `assistant`)

