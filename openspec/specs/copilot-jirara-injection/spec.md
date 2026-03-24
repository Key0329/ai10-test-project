# copilot-jirara-injection Specification

## Purpose

TBD - created by archiving change 'force-jirara-workflow'. Update Purpose after archive.

## Requirements

### Requirement: Force inject system Jirara skill into Copilot work directory

The Copilot executor SHALL inject the system Jirara skill into the cloned repository's `.github/skills/jirara/` directory, overwriting any existing content at that path. The injection SHALL use the system's `.github/skills/jirara/` as the source.

#### Scenario: Target repo has no jirara directory

- **WHEN** the cloned repository does not have `.github/skills/jirara/`
- **THEN** the executor SHALL create the directory and copy the system Jirara skill files into it

#### Scenario: Target repo already has jirara directory

- **WHEN** the cloned repository already has `.github/skills/jirara/`
- **THEN** the executor SHALL remove the existing directory and replace it with the system Jirara skill files

#### Scenario: Injection source path

- **WHEN** the executor resolves the Jirara source
- **THEN** the path SHALL be dynamically resolved from the project root's `.github/skills/jirara/` directory


<!-- @trace
source: force-jirara-workflow
updated: 2026-03-24
code:
  - .github/skills/jirara/SKILL.md
  - .github/skills/jirara/jirara.md
  - backend/services/queue.py
  - backend/models/job.py
  - backend/routers/jobs.py
-->

---
### Requirement: Copilot prompt prioritizes Jirara over repo dev-flow skills

The Copilot executor's system message and user prompt SHALL include explicit instructions that the Jirara workflow is the authoritative development process. Any repo-provided development flow skills SHALL NOT override Jirara steps. Non-flow skills from the repo SHALL remain active.

#### Scenario: Prompt includes Jirara priority instruction

- **WHEN** the Copilot executor builds the system message via `_build_system_message()`
- **THEN** the message SHALL include an instruction that Jirara is the primary development workflow and takes precedence over repo-provided flow skills

#### Scenario: Prompt includes Jirara priority in user prompt

- **WHEN** the Copilot executor builds the user prompt via `_build_copilot_prompt()`
- **THEN** the prompt SHALL reference Jirara as the mandatory workflow to follow

#### Scenario: Repo non-flow skills remain active in Copilot mode

- **WHEN** the cloned repository contains non-flow skills (e.g., `api-creator`, `component-builder`, `frontend-design`)
- **THEN** the Copilot system message SHALL instruct that these skills remain available and active alongside Jirara

<!-- @trace
source: force-jirara-workflow
updated: 2026-03-24
code:
  - .github/skills/jirara/SKILL.md
  - .github/skills/jirara/jirara.md
  - backend/services/queue.py
  - backend/models/job.py
  - backend/routers/jobs.py
-->