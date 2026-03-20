## MODIFIED Requirements

### Requirement: Light-dark mixed theme with dual font strategy

The frontend SHALL use a blue-gray background (`#e8ecf1`) for all UI areas except the log viewer, which SHALL remain dark (#1a1b1e). UI elements (headers, buttons, labels) SHALL use a sans-serif font stack (system-ui, -apple-system, sans-serif), while code-oriented content (ticket IDs, repository URLs, log output) SHALL use a monospace font stack. Surface, border, and muted text colors SHALL use a cold-tone palette consistent with the blue-gray background.

#### Scenario: Page background is blue-gray

- **WHEN** any page (Dashboard, NewJob, JobDetail, TokenGate) is rendered
- **THEN** the page background SHALL be blue-gray (`#e8ecf1`)

#### Scenario: Surface elements use cold-tone white

- **WHEN** cards, forms, or stat elements are rendered
- **THEN** the surface background SHALL be `#f4f6f9` and borders SHALL be `#d0d5dd`

#### Scenario: Log viewer remains dark

- **WHEN** the JobDetail page log viewer is rendered
- **THEN** the log viewer background SHALL be dark (#1a1b1e)

#### Scenario: UI text uses sans-serif

- **WHEN** a header, button, label, or descriptive text element is rendered
- **THEN** the font-family SHALL be system-ui, -apple-system, sans-serif

#### Scenario: Code content uses monospace

- **WHEN** a ticket ID, repository URL, or log line is rendered
- **THEN** the font-family SHALL be a monospace font stack

## ADDED Requirements

### Requirement: MCP and Skill log line colors

The log viewer SHALL render log entries with `event_type` = `mcp` in cyan (`#5ec4d0`) and entries with `event_type` = `skill` in gold (`#e0a854`), with corresponding colored tag labels.

#### Scenario: MCP log line color

- **WHEN** a log entry with `event_type` = `mcp` is rendered in the log viewer
- **THEN** the log line text SHALL be cyan (`#5ec4d0`) and the tag label SHALL display `MCP` with a cyan background

#### Scenario: Skill log line color

- **WHEN** a log entry with `event_type` = `skill` is rendered in the log viewer
- **THEN** the log line text SHALL be gold (`#e0a854`) and the tag label SHALL display `SKL` with a gold background

### Requirement: Log filter includes MCP and Skill options

The log viewer filter buttons SHALL include MCP and Skill options in addition to the existing All, Assistant, Tools, and System filters.

#### Scenario: MCP filter active

- **WHEN** the user clicks the MCP filter button
- **THEN** only log entries with `event_type` = `mcp` SHALL be displayed

#### Scenario: Skill filter active

- **WHEN** the user clicks the Skill filter button
- **THEN** only log entries with `event_type` = `skill` SHALL be displayed
