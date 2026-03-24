# log-milestone-highlights Specification

## Purpose

TBD - created by archiving change 'fix-log-filters-and-highlights'. Update Purpose after archive.

## Requirements

### Requirement: Milestone log entries receive visual emphasis

The frontend log viewer SHALL apply a distinct visual style (accent-colored left border, semi-transparent accent background, bold text) to log entries that match milestone patterns.

#### Scenario: Clone complete message is highlighted

- **WHEN** a log entry with `stream` = `system` and message containing `Clone complete` is rendered in the log viewer
- **THEN** the entry SHALL display with the milestone visual style (accent left border, highlighted background)

#### Scenario: Session initialized message is highlighted

- **WHEN** a log entry with `event_type` = `system` and message containing `Session initialized` is rendered
- **THEN** the entry SHALL display with the milestone visual style

#### Scenario: Execution complete message is highlighted

- **WHEN** a log entry with `stream` = `system` and message containing `exited with code` or `執行完成` is rendered
- **THEN** the entry SHALL display with the milestone visual style

#### Scenario: Non-milestone system message is not highlighted

- **WHEN** a log entry with `stream` = `system` and message `Prompt: ...` is rendered
- **THEN** the entry SHALL display with normal system styling, not milestone styling


<!-- @trace
source: fix-log-filters-and-highlights
updated: 2026-03-24
code:
  - backend/services/copilot_executor.py
  - backend/services/executor.py
  - .github/prompts/spectra-propose.prompt.md
  - .agents/skills/spectra-propose/SKILL.md
  - .github/skills/spectra-propose/SKILL.md
  - frontend/src/pages/JobDetail.vue
  - frontend/src/app.css
tests:
  - backend/tests/test_executor.py
  - backend/tests/test_event_classify.py
  - backend/tests/test_stream_output.py
-->

---
### Requirement: Sticky progress bar shows latest milestone

The log viewer SHALL display a sticky bar at the top that shows the most recent milestone message and elapsed time. The bar SHALL remain visible while the user scrolls through logs.

#### Scenario: Sticky bar updates on new milestone

- **WHEN** a new log entry matching a milestone pattern is received during streaming
- **THEN** the sticky bar SHALL update to show that milestone's message and current elapsed time

#### Scenario: Sticky bar persists during scroll

- **WHEN** the user scrolls down through log entries
- **THEN** the sticky bar SHALL remain fixed at the top of the log viewer viewport

#### Scenario: No milestone yet

- **WHEN** no milestone log entries have been received (e.g., job just started)
- **THEN** the sticky bar SHALL display a default message such as "Waiting for output..."

#### Scenario: Sticky bar shows elapsed time

- **WHEN** the sticky bar displays a milestone message
- **THEN** the bar SHALL also show the elapsed time since job creation in the format used by the existing `elapsed()` function

<!-- @trace
source: fix-log-filters-and-highlights
updated: 2026-03-24
code:
  - backend/services/copilot_executor.py
  - backend/services/executor.py
  - .github/prompts/spectra-propose.prompt.md
  - .agents/skills/spectra-propose/SKILL.md
  - .github/skills/spectra-propose/SKILL.md
  - frontend/src/pages/JobDetail.vue
  - frontend/src/app.css
tests:
  - backend/tests/test_executor.py
  - backend/tests/test_event_classify.py
  - backend/tests/test_stream_output.py
-->