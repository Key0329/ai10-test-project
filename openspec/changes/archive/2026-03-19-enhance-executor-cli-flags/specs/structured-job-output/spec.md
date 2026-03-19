## ADDED Requirements

### Requirement: Stream JSON output from Claude CLI

The executor SHALL invoke Claude Code CLI with `--output-format stream-json` flag, producing one JSON object per line on stdout.

#### Scenario: CLI command includes stream-json flag

- **WHEN** executor builds the Claude Code command via `build_claude_command`
- **THEN** the argument list SHALL include `--output-format` followed by `stream-json`

#### Scenario: Output is line-delimited JSON

- **WHEN** Claude Code runs with `--output-format stream-json`
- **THEN** each line of stdout SHALL be a valid JSON object containing at minimum a `type` field

---

### Requirement: Parse and classify JSON events

The executor SHALL attempt to parse each stdout line as JSON and extract the `type` field as `event_type`. If parsing fails, the line SHALL be stored with `event_type` set to `raw`.

#### Scenario: Valid JSON line

- **WHEN** a stdout line is valid JSON with `type` field value `assistant`
- **THEN** the executor SHALL store the log entry with `event_type` = `assistant` and the full JSON as `metadata`

#### Scenario: Non-JSON line (stderr or malformed)

- **WHEN** a stdout or stderr line is not valid JSON
- **THEN** the executor SHALL store the log entry with `event_type` = `raw` and `metadata` = NULL

---

### Requirement: Extended job_logs schema

The `job_logs` table SHALL include `event_type` (TEXT, default `raw`) and `metadata` (TEXT, nullable) columns to support structured event storage.

#### Scenario: New log entry with structured data

- **WHEN** a structured JSON event is stored
- **THEN** the `event_type` column SHALL contain the event type string and `metadata` SHALL contain the full JSON string

#### Scenario: Backward compatibility with existing logs

- **WHEN** the database contains log entries created before this change
- **THEN** those entries SHALL have `event_type` = `raw` and `metadata` = NULL, and the system SHALL continue to function normally
