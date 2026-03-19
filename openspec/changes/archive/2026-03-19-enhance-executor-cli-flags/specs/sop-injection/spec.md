## MODIFIED Requirements

### Requirement: Inject Jirara skill via append-system-prompt-file

The executor SHALL invoke Claude Code CLI with `--append-system-prompt-file` flag pointing to the Jirara skill file (`jirara.md`), so that the centralized SOP is injected into every job execution without modifying the cloned repository. The executor SHALL also include `--max-turns` and `--fallback-model` flags in the CLI command to provide agent turn limits and model fallback capability.

#### Scenario: Successful Jirara injection

- **WHEN** executor dispatches a job
- **THEN** the Claude Code subprocess command SHALL include `--append-system-prompt-file <path-to-jirara.md>` as arguments

#### Scenario: Jirara file path resolution

- **WHEN** executor constructs the Claude Code command
- **THEN** the path to `jirara.md` SHALL be resolved dynamically from the project root (not hardcoded), using the project's `.claude/skills/jirara.md` relative path

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
