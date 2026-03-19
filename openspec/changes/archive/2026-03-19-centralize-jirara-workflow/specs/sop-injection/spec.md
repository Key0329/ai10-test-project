## ADDED Requirements

### Requirement: Inject Jirara skill via append-system-prompt-file

The executor SHALL invoke Claude Code CLI with `--append-system-prompt-file` flag pointing to the Jirara skill file (`jirara.md`), so that the centralized SOP is injected into every job execution without modifying the cloned repository.

#### Scenario: Successful Jirara injection

- **WHEN** executor dispatches a job
- **THEN** the Claude Code subprocess command SHALL include `--append-system-prompt-file <path-to-jirara.md>` as arguments

#### Scenario: Jirara file path resolution

- **WHEN** executor constructs the Claude Code command
- **THEN** the path to `jirara.md` SHALL be resolved dynamically from the project root (not hardcoded), using the project's `.claude/skills/jirara.md` relative path

### Requirement: Validate Jirara file existence on startup

The executor SHALL verify that the Jirara skill file exists at the resolved path before accepting any jobs. If the file is missing, the executor SHALL raise a clear error during initialization.

#### Scenario: Jirara file exists

- **WHEN** the executor initializes and the Jirara file exists at the resolved path
- **THEN** the executor SHALL proceed normally

#### Scenario: Jirara file missing

- **WHEN** the executor initializes and the Jirara file does NOT exist at the resolved path
- **THEN** the executor SHALL raise a RuntimeError with a message indicating the missing file path

### Requirement: Simplified executor prompt

The executor prompt SHALL contain only the Jira ticket instruction. The prompt SHALL NOT include callback API instructions, as completion reporting is handled by the Jirara skill's own mechanisms (Jira comment and Teams notification).

#### Scenario: Prompt content for a standard job

- **WHEN** executor builds the prompt for a job with jira_ticket "JRA-123" and no extra_prompt
- **THEN** the prompt SHALL be "請處理 Jira 單 JRA-123" without any callback URL or callback body instructions

#### Scenario: Prompt content with extra_prompt

- **WHEN** executor builds the prompt for a job with jira_ticket "JRA-123" and extra_prompt "注意：只修改 frontend"
- **THEN** the prompt SHALL be "請處理 Jira 單 JRA-123" followed by the extra_prompt content, without any callback instructions

### Requirement: Backward compatibility with repo CLAUDE.md

The injection mechanism SHALL NOT interfere with any existing CLAUDE.md in the cloned repository. Claude Code's native CLAUDE.md loading SHALL remain active alongside the injected Jirara SOP.

#### Scenario: Repo with existing CLAUDE.md

- **WHEN** the cloned repository contains a CLAUDE.md with team-specific rules
- **THEN** Claude Code SHALL load both the repo's CLAUDE.md (automatically) and the Jirara SOP (via --append-system-prompt-file), with no conflicts

#### Scenario: Repo without CLAUDE.md

- **WHEN** the cloned repository does not contain a CLAUDE.md
- **THEN** Claude Code SHALL still receive the Jirara SOP via --append-system-prompt-file and operate according to its workflow

### Requirement: Update system-spec.md for uv and Jirara workflow

The system specification document SHALL be updated to reflect: (1) Python package management via uv instead of pip, (2) development SOP delivered via Jirara skill injection instead of per-repo CLAUDE.md, and (3) adjusted deployment steps.

#### Scenario: Documentation reflects uv usage

- **WHEN** a reader consults system-spec.md for setup instructions
- **THEN** the document SHALL reference `uv` for Python dependency installation and `pyproject.toml` as the dependency definition file

#### Scenario: Documentation reflects Jirara workflow

- **WHEN** a reader consults system-spec.md section 5 (Claude Code execution details)
- **THEN** the document SHALL describe the `--append-system-prompt-file` injection mechanism and reference the Jirara skill as the centralized SOP source
