## ADDED Requirements

### Requirement: Classify MCP tool calls as mcp event type

The executor SHALL classify tool_use blocks whose `name` starts with `mcp__` as `event_type` = `mcp` and prefix the display message with `[mcp]` instead of `[tool]`.

#### Scenario: MCP tool call detected

- **WHEN** an assistant event contains a tool_use block with name `mcp__github__create_pr`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp` and message prefixed with `[mcp]`

#### Scenario: Multiple tool_use blocks with mixed types

- **WHEN** an assistant event contains both a regular tool_use (e.g., `Bash`) and an MCP tool_use (e.g., `mcp__github__list_prs`)
- **THEN** the log entry SHALL use the highest priority event_type (`mcp` > `skill` > `assistant`)

### Requirement: Classify Skill tool calls as skill event type

The executor SHALL classify tool_use blocks whose `name` is `Skill` as `event_type` = `skill` and prefix the display message with `[skill]` instead of `[tool]`.

#### Scenario: Skill tool call detected

- **WHEN** an assistant event contains a tool_use block with name `Skill`
- **THEN** the log entry SHALL be stored with `event_type` = `skill` and message prefixed with `[skill]`

### Requirement: Preserve backward compatibility for existing event types

The executor SHALL continue to classify non-MCP, non-Skill tool_use blocks as `event_type` = `assistant` with the `[tool]` prefix.

#### Scenario: Regular tool call unchanged

- **WHEN** an assistant event contains a tool_use block with name `Bash`
- **THEN** the log entry SHALL be stored with `event_type` = `assistant` and message prefixed with `[tool]`
