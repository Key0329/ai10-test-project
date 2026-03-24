## MODIFIED Requirements

### Requirement: Emit execution summary log on job completion

The executor SHALL insert a system log entry into `job_logs` when a job finishes (both completed and failed), containing a formatted summary of token usage, cost, MCP servers used, and skills used. This requirement SHALL apply to both the Claude Code executor and the Copilot executor.

#### Scenario: Summary log after successful job

- **WHEN** a job completes with exit code 0
- **THEN** the executor SHALL insert a log entry with `event_type` = `system` and `stream` = `system` containing input tokens, output tokens, total cost USD, number of turns, list of MCP servers, and list of skills

#### Scenario: Summary log after failed job

- **WHEN** a job fails with non-zero exit code but has a `result` event in metadata
- **THEN** the executor SHALL still insert the summary log with available data

#### Scenario: Missing result metadata

- **WHEN** a job finishes but no `result` event exists in `job_logs`
- **THEN** the executor SHALL skip summary emission without error

#### Scenario: Copilot executor emits MCP summary

- **WHEN** a Copilot mode job completes and log entries with `event_type` = `mcp` exist
- **THEN** the Copilot executor SHALL collect unique MCP server names from those log entries and include them in the summary, using the same format as the Claude Code executor

---

### Requirement: Collect MCP server names from logs

The executor SHALL query all log entries with `event_type` = `mcp` for the job and extract unique MCP server names using the `mcp__<server>__` prefix pattern. This requirement SHALL apply to both the Claude Code executor and the Copilot executor.

#### Scenario: Job used MCP tools

- **WHEN** the job logs contain entries with `event_type` = `mcp` and messages matching `mcp__github__*`
- **THEN** the summary SHALL list `github` in the MCP servers section

#### Scenario: Job used no MCP tools

- **WHEN** the job logs contain no entries with `event_type` = `mcp`
- **THEN** the summary SHALL display `(none)` for MCP servers

## ADDED Requirements

### Requirement: Copilot executor classifies MCP tool events

The Copilot executor SHALL detect MCP tool calls in `tool.execution_start` and `tool.execution_complete` events by checking if the `tool_name` starts with `mcp__`. When detected, the log entry SHALL be stored with `event_type` = `mcp` instead of `assistant`.

#### Scenario: Copilot tool event is MCP tool

- **WHEN** a `tool.execution_start` event has `tool_name` starting with `mcp__`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp`

#### Scenario: Copilot tool event is not MCP tool

- **WHEN** a `tool.execution_start` event has `tool_name` that does not start with `mcp__`
- **THEN** the log entry SHALL be stored with `event_type` = `assistant`
