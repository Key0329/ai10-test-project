# sop-injection Specification

## Purpose

TBD - created by archiving change 'centralize-jirara-workflow'. Update Purpose after archive.

## Requirements

### Requirement: Inject Jirara skill via append-system-prompt-file

The executor SHALL invoke Claude Code CLI with `--append-system-prompt-file` flag pointing to the Jirara skill file (`jirara.md`), so that the centralized SOP is injected into every job execution without modifying the cloned repository. The executor SHALL also include `--max-turns` and `--fallback-model` flags in the CLI command to provide agent turn limits and model fallback capability.

The executor prompt SHALL include an explicit instruction that the Jirara workflow takes precedence over any repository-provided development flow skills (e.g., `dev-flow`, `jira-ops`). Repository-provided non-flow skills (e.g., `api-creator`, `component-builder`) SHALL remain active alongside Jirara.

#### Scenario: Successful Jirara injection

- **WHEN** executor dispatches a job
- **THEN** the Claude Code subprocess command SHALL include `--append-system-prompt-file <path-to-jirara.md>` as arguments

#### Scenario: Jirara file path resolution

- **WHEN** executor constructs the Claude Code command
- **THEN** the path to `jirara.md` SHALL be resolved dynamically from the project root (not hardcoded), using the project's `.github/skills/jirara/jirara.md` relative path

#### Scenario: Jirara priority over repo dev-flow skills

- **WHEN** the cloned repository contains its own development flow skill (e.g., `.claude/skills/dev-flow/`)
- **THEN** the executor prompt SHALL instruct that Jirara is the authoritative development workflow and repo-provided flow skills SHALL NOT override Jirara steps

#### Scenario: Repo non-flow skills remain active

- **WHEN** the cloned repository contains non-flow skills (e.g., `api-creator`, `component-builder`)
- **THEN** those skills SHALL remain available and active alongside Jirara without interference

#### Scenario: Max turns limit included

- **WHEN** executor builds the Claude Code command via `build_claude_command`
- **THEN** the argument list SHALL include `--max-turns` followed by the configured limit value (default: 50)

#### Scenario: Max turns configurable via environment

- **WHEN** the environment variable `MAX_TURNS` is set to `80`
- **THEN** the executor SHALL use `80` as the `--max-turns` value instead of the default

#### Scenario: Fallback model included

- **WHEN** executor builds the Claude Code command via `build_claude_command`
- **THEN** the argument list SHALL include `--fallback-model` followed by the configured model name (default: `sonnet`)

#### Scenario: Fallback model configurable via environment

- **WHEN** the environment variable `FALLBACK_MODEL` is set to `haiku`
- **THEN** the executor SHALL use `haiku` as the `--fallback-model` value instead of the default


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
### Requirement: Validate Jirara file existence on startup

The executor SHALL verify that the Jirara skill file exists at the resolved path before accepting any jobs. If the file is missing, the executor SHALL raise a clear error during initialization.

#### Scenario: Jirara file exists

- **WHEN** the executor initializes and the Jirara file exists at the resolved path
- **THEN** the executor SHALL proceed normally

#### Scenario: Jirara file missing

- **WHEN** the executor initializes and the Jirara file does NOT exist at the resolved path
- **THEN** the executor SHALL raise a RuntimeError with a message indicating the missing file path


<!-- @trace
source: centralize-jirara-workflow
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

---
### Requirement: Simplified executor prompt

The executor prompt SHALL contain only the Jira ticket instruction. The prompt SHALL NOT include callback API instructions, as completion reporting is handled by the Jirara skill's own mechanisms (Jira comment and Teams notification).

#### Scenario: Prompt content for a standard job

- **WHEN** executor builds the prompt for a job with jira_ticket "JRA-123" and no extra_prompt
- **THEN** the prompt SHALL be "請處理 Jira 單 JRA-123" without any callback URL or callback body instructions

#### Scenario: Prompt content with extra_prompt

- **WHEN** executor builds the prompt for a job with jira_ticket "JRA-123" and extra_prompt "注意：只修改 frontend"
- **THEN** the prompt SHALL be "請處理 Jira 單 JRA-123" followed by the extra_prompt content, without any callback instructions


<!-- @trace
source: centralize-jirara-workflow
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

---
### Requirement: Backward compatibility with repo CLAUDE.md

The injection mechanism SHALL NOT interfere with any existing CLAUDE.md in the cloned repository. Claude Code's native CLAUDE.md loading SHALL remain active alongside the injected Jirara SOP.

#### Scenario: Repo with existing CLAUDE.md

- **WHEN** the cloned repository contains a CLAUDE.md with team-specific rules
- **THEN** Claude Code SHALL load both the repo's CLAUDE.md (automatically) and the Jirara SOP (via --append-system-prompt-file), with no conflicts

#### Scenario: Repo without CLAUDE.md

- **WHEN** the cloned repository does not contain a CLAUDE.md
- **THEN** Claude Code SHALL still receive the Jirara SOP via --append-system-prompt-file and operate according to its workflow


<!-- @trace
source: centralize-jirara-workflow
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

---
### Requirement: Update system-spec.md for uv and Jirara workflow

The system specification document SHALL be updated to reflect: (1) Python package management via uv instead of pip, (2) development SOP delivered via Jirara skill injection instead of per-repo CLAUDE.md, and (3) adjusted deployment steps.

#### Scenario: Documentation reflects uv usage

- **WHEN** a reader consults system-spec.md for setup instructions
- **THEN** the document SHALL reference `uv` for Python dependency installation and `pyproject.toml` as the dependency definition file

#### Scenario: Documentation reflects Jirara workflow

- **WHEN** a reader consults system-spec.md section 5 (Claude Code execution details)
- **THEN** the document SHALL describe the `--append-system-prompt-file` injection mechanism and reference the Jirara skill as the centralized SOP source

<!-- @trace
source: centralize-jirara-workflow
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