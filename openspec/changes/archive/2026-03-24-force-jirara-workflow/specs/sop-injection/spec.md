## MODIFIED Requirements

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
