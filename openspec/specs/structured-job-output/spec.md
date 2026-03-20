# structured-job-output Specification

## Purpose

Executor outputs structured JSON event streams from Claude Code CLI, enabling classification, storage, and filtered display of tool calls, assistant messages, token usage, and cost data.

## Requirements

### Requirement: Stream JSON output from Claude CLI

The executor SHALL invoke Claude Code CLI with `--output-format stream-json` flag, producing one JSON object per line on stdout.

#### Scenario: CLI command includes stream-json flag

- **WHEN** executor builds the Claude Code command via `build_claude_command`
- **THEN** the argument list SHALL include `--output-format` followed by `stream-json`

#### Scenario: Output is line-delimited JSON

- **WHEN** Claude Code runs with `--output-format stream-json`
- **THEN** each line of stdout SHALL be a valid JSON object containing at minimum a `type` field


<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - .env.example
  - backend/uv.lock
  - docs/system-spec.md
  - backend/pyproject.toml
  - backend/services/executor.py
tests:
  - backend/tests/test_executor.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
-->


<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - backend/services/executor.py
  - backend/db.py
  - frontend/src/pages/JobDetail.jsx
  - .env.example
  - frontend/src/api.js
  - backend/uv.lock
  - docs/system-spec.md
  - backend/routers/jobs.py
  - backend/pyproject.toml
tests:
  - backend/tests/__init__.py
  - backend/tests/test_stream_output.py
  - backend/tests/conftest.py
  - backend/tests/test_db.py
  - backend/tests/test_executor.py
-->

---
### Requirement: Parse and classify JSON events

The executor SHALL attempt to parse each stdout line as JSON and extract the `type` field as `event_type`. If parsing fails, the line SHALL be stored with `event_type` set to `raw`.

#### Scenario: Valid JSON line

- **WHEN** a stdout line is valid JSON with `type` field value `assistant`
- **THEN** the executor SHALL store the log entry with `event_type` = `assistant` and the full JSON as `metadata`

#### Scenario: Non-JSON line (stderr or malformed)

- **WHEN** a stdout or stderr line is not valid JSON
- **THEN** the executor SHALL store the log entry with `event_type` = `raw` and `metadata` = NULL


<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - .env.example
  - backend/uv.lock
  - docs/system-spec.md
  - backend/pyproject.toml
  - backend/services/executor.py
tests:
  - backend/tests/test_executor.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
-->


<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - backend/services/executor.py
  - backend/db.py
  - frontend/src/pages/JobDetail.jsx
  - .env.example
  - frontend/src/api.js
  - backend/uv.lock
  - docs/system-spec.md
  - backend/routers/jobs.py
  - backend/pyproject.toml
tests:
  - backend/tests/__init__.py
  - backend/tests/test_stream_output.py
  - backend/tests/conftest.py
  - backend/tests/test_db.py
  - backend/tests/test_executor.py
-->

---
### Requirement: Extended job_logs schema

The `job_logs` table SHALL include `event_type` (TEXT, default `raw`) and `metadata` (TEXT, nullable) columns to support structured event storage.

#### Scenario: New log entry with structured data

- **WHEN** a structured JSON event is stored
- **THEN** the `event_type` column SHALL contain the event type string and `metadata` SHALL contain the full JSON string

#### Scenario: Backward compatibility with existing logs

- **WHEN** the database contains log entries created before this change
- **THEN** those entries SHALL have `event_type` = `raw` and `metadata` = NULL, and the system SHALL continue to function normally


<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - .env.example
  - backend/uv.lock
  - docs/system-spec.md
  - backend/pyproject.toml
  - backend/services/executor.py
tests:
  - backend/tests/test_executor.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
-->

<!-- @trace
source: enhance-executor-cli-flags
updated: 2026-03-19
code:
  - backend/services/executor.py
  - backend/db.py
  - frontend/src/pages/JobDetail.jsx
  - .env.example
  - frontend/src/api.js
  - backend/uv.lock
  - docs/system-spec.md
  - backend/routers/jobs.py
  - backend/pyproject.toml
tests:
  - backend/tests/__init__.py
  - backend/tests/test_stream_output.py
  - backend/tests/conftest.py
  - backend/tests/test_db.py
  - backend/tests/test_executor.py
-->

---
### Requirement: Classify MCP tool calls as mcp event type

The executor SHALL classify tool_use blocks whose `name` starts with `mcp__` as `event_type` = `mcp` and prefix the display message with `[mcp]` instead of `[tool]`.

#### Scenario: MCP tool call detected

- **WHEN** an assistant event contains a tool_use block with name `mcp__github__create_pr`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp` and message prefixed with `[mcp]`

#### Scenario: Multiple tool_use blocks with mixed types

- **WHEN** an assistant event contains both a regular tool_use (e.g., `Bash`) and an MCP tool_use (e.g., `mcp__github__list_prs`)
- **THEN** the log entry SHALL use the highest priority event_type (`mcp` > `skill` > `assistant`)


<!-- @trace
source: log-summary-and-theme
updated: 2026-03-20
code:
  - backend/services/queue.py
  - frontend/src/api.js
  - backend/models/job.py
  - backend/db.py
  - frontend/src/app.css
  - backend/jirara.db
  - backend/routers/jobs.py
  - backend/services/executor.py
  - frontend/src/pages/JobDetail.vue
  - .env.example
tests:
  - backend/tests/test_rerun_api.py
  - backend/tests/test_rerun_db.py
  - backend/tests/test_rerun_models.py
  - backend/tests/test_rerun_chain.py
  - backend/tests/test_emit_summary.py
  - backend/tests/test_event_classify.py
-->

---
### Requirement: Classify Skill tool calls as skill event type

The executor SHALL classify tool_use blocks whose `name` is `Skill` as `event_type` = `skill` and prefix the display message with `[skill]` instead of `[tool]`.

#### Scenario: Skill tool call detected

- **WHEN** an assistant event contains a tool_use block with name `Skill`
- **THEN** the log entry SHALL be stored with `event_type` = `skill` and message prefixed with `[skill]`


<!-- @trace
source: log-summary-and-theme
updated: 2026-03-20
code:
  - backend/services/queue.py
  - frontend/src/api.js
  - backend/models/job.py
  - backend/db.py
  - frontend/src/app.css
  - backend/jirara.db
  - backend/routers/jobs.py
  - backend/services/executor.py
  - frontend/src/pages/JobDetail.vue
  - .env.example
tests:
  - backend/tests/test_rerun_api.py
  - backend/tests/test_rerun_db.py
  - backend/tests/test_rerun_models.py
  - backend/tests/test_rerun_chain.py
  - backend/tests/test_emit_summary.py
  - backend/tests/test_event_classify.py
-->

---
### Requirement: Preserve backward compatibility for existing event types

The executor SHALL continue to classify non-MCP, non-Skill tool_use blocks as `event_type` = `assistant` with the `[tool]` prefix.

#### Scenario: Regular tool call unchanged

- **WHEN** an assistant event contains a tool_use block with name `Bash`
- **THEN** the log entry SHALL be stored with `event_type` = `assistant` and message prefixed with `[tool]`

<!-- @trace
source: log-summary-and-theme
updated: 2026-03-20
code:
  - backend/services/queue.py
  - frontend/src/api.js
  - backend/models/job.py
  - backend/db.py
  - frontend/src/app.css
  - backend/jirara.db
  - backend/routers/jobs.py
  - backend/services/executor.py
  - frontend/src/pages/JobDetail.vue
  - .env.example
tests:
  - backend/tests/test_rerun_api.py
  - backend/tests/test_rerun_db.py
  - backend/tests/test_rerun_models.py
  - backend/tests/test_rerun_chain.py
  - backend/tests/test_emit_summary.py
  - backend/tests/test_event_classify.py
-->