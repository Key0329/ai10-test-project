## ADDED Requirements

### Requirement: Dynamic MCP token input fields

The NewJob form SHALL display dynamic password input fields for each missing environment variable detected by the MCP scan. Each field SHALL be labeled with the variable name (e.g., `SENTRY_TOKEN`) and the values SHALL be included as `env_overrides` in the job submission payload.

#### Scenario: Multiple missing variables

- **WHEN** the scan returns `missing_vars: ["API_KEY", "SENTRY_TOKEN"]`
- **THEN** the form SHALL display two password input fields labeled `API_KEY` and `SENTRY_TOKEN`

#### Scenario: User fills in token and submits

- **WHEN** the user fills in `SENTRY_TOKEN` = `abc123` and submits the job
- **THEN** the job payload SHALL include `env_overrides: {"SENTRY_TOKEN": "abc123"}`

#### Scenario: Both modes show token fields

- **WHEN** the user is in Claude Code mode or Copilot mode and the scan detects missing variables
- **THEN** the dynamic token input fields SHALL be displayed regardless of mode
