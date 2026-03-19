## ADDED Requirements

### Requirement: Light-dark mixed theme with dual font strategy

The frontend SHALL use a light background for all UI areas except the log viewer, which SHALL remain dark (#0d1117). UI elements (headers, buttons, labels) SHALL use a sans-serif font stack (system-ui, -apple-system, sans-serif), while code-oriented content (ticket IDs, repository URLs, log output) SHALL use a monospace font stack.

#### Scenario: Page background is light

- **WHEN** any page (Dashboard, NewJob, JobDetail, TokenGate) is rendered
- **THEN** the page background SHALL be light (#ffffff or #f6f8fa)

#### Scenario: Log viewer remains dark

- **WHEN** the JobDetail page log viewer is rendered
- **THEN** the log viewer background SHALL be dark (#0d1117)

#### Scenario: UI text uses sans-serif

- **WHEN** a header, button, label, or descriptive text element is rendered
- **THEN** the font-family SHALL be system-ui, -apple-system, sans-serif

#### Scenario: Code content uses monospace

- **WHEN** a ticket ID, repository URL, or log line is rendered
- **THEN** the font-family SHALL be a monospace font stack
