# job-execution-summary Specification

## Purpose

TBD - created by archiving change 'log-summary-and-theme'. Update Purpose after archive.

## Requirements

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


<!-- @trace
source: dynamic-repo-mcp
updated: 2026-03-24
code:
  - backend/services/executor.py
  - setup.sh
  - frontend/src/pages/NewJob.vue
  - dev.sh
  - frontend/.DS_Store
  - .DS_Store
  - backend/services/copilot_executor.py
  - backend/db.py
  - SETUP-TROUBLESHOOTING.md
  - backend/services/mcp_loader.py
tests:
  - backend/tests/test_mcp_loader.py
  - backend/tests/test_copilot_mcp_classify.py
-->

---
### Requirement: Parse token and cost data from result event

The executor SHALL extract `total_cost_usd`, `usage.input_tokens`, `usage.output_tokens`, `usage.cache_read_input_tokens`, and `num_turns` from the `result` event metadata JSON.

#### Scenario: All fields present in result metadata

- **WHEN** the `result` event metadata contains `total_cost_usd` and `usage` object
- **THEN** the summary SHALL display formatted values for cost, input tokens, output tokens, cache read tokens, and turns

#### Scenario: Partial fields in result metadata

- **WHEN** any field is missing from the result metadata
- **THEN** the summary SHALL display `N/A` for the missing field


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
### Requirement: Collect MCP server names from logs

The executor SHALL query all log entries with `event_type` = `mcp` for the job and extract unique MCP server names using the `mcp__<server>__` prefix pattern. This requirement SHALL apply to both the Claude Code executor and the Copilot executor.

#### Scenario: Job used MCP tools

- **WHEN** the job logs contain entries with `event_type` = `mcp` and messages matching `mcp__github__*`
- **THEN** the summary SHALL list `github` in the MCP servers section

#### Scenario: Job used no MCP tools

- **WHEN** the job logs contain no entries with `event_type` = `mcp`
- **THEN** the summary SHALL display `(none)` for MCP servers


<!-- @trace
source: dynamic-repo-mcp
updated: 2026-03-24
code:
  - backend/services/executor.py
  - setup.sh
  - frontend/src/pages/NewJob.vue
  - dev.sh
  - frontend/.DS_Store
  - .DS_Store
  - backend/services/copilot_executor.py
  - backend/db.py
  - SETUP-TROUBLESHOOTING.md
  - backend/services/mcp_loader.py
tests:
  - backend/tests/test_mcp_loader.py
  - backend/tests/test_copilot_mcp_classify.py
-->

---
### Requirement: Collect skill names from logs

The executor SHALL query all log entries with `event_type` = `skill` for the job and extract unique skill names from the message content.

#### Scenario: Job used skills

- **WHEN** the job logs contain entries with `event_type` = `skill` referencing `Skill: commit`
- **THEN** the summary SHALL list `commit` in the skills section

#### Scenario: Job used no skills

- **WHEN** the job logs contain no entries with `event_type` = `skill`
- **THEN** the summary SHALL display `(none)` for skills

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
### Requirement: Copilot executor classifies MCP tool events

The Copilot executor SHALL detect MCP tool calls in `tool.execution_start` and `tool.execution_complete` events by checking if the `tool_name` starts with `mcp__`. When detected, the log entry SHALL be stored with `event_type` = `mcp` instead of `assistant`.

#### Scenario: Copilot tool event is MCP tool

- **WHEN** a `tool.execution_start` event has `tool_name` starting with `mcp__`
- **THEN** the log entry SHALL be stored with `event_type` = `mcp`

#### Scenario: Copilot tool event is not MCP tool

- **WHEN** a `tool.execution_start` event has `tool_name` that does not start with `mcp__`
- **THEN** the log entry SHALL be stored with `event_type` = `assistant`

<!-- @trace
source: dynamic-repo-mcp
updated: 2026-03-24
code:
  - backend/services/executor.py
  - setup.sh
  - frontend/src/pages/NewJob.vue
  - dev.sh
  - frontend/.DS_Store
  - .DS_Store
  - backend/services/copilot_executor.py
  - backend/db.py
  - SETUP-TROUBLESHOOTING.md
  - backend/services/mcp_loader.py
tests:
  - backend/tests/test_mcp_loader.py
  - backend/tests/test_copilot_mcp_classify.py
-->