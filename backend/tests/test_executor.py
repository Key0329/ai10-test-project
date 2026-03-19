"""Tests for executor CLI command construction and prompt building."""

import os

import pytest


class TestBuildPrompt:
    """Verify simplified executor prompt (no callback instructions)."""

    def test_standard_prompt_contains_jira_ticket(self):
        from services.executor import build_prompt

        prompt = build_prompt("JRA-123", None)
        assert "JRA-123" in prompt

    def test_standard_prompt_no_callback(self):
        from services.executor import build_prompt

        prompt = build_prompt("JRA-123", None)
        assert "callback" not in prompt.lower()
        assert "curl" not in prompt.lower()

    def test_prompt_with_extra_prompt(self):
        from services.executor import build_prompt

        prompt = build_prompt("JRA-123", "注意：只修改 frontend")
        assert "JRA-123" in prompt
        assert "注意：只修改 frontend" in prompt
        assert "callback" not in prompt.lower()

    def test_prompt_without_extra_prompt_has_no_extra_section(self):
        from services.executor import build_prompt

        prompt = build_prompt("JRA-123", None)
        assert "額外指示" not in prompt


class TestBuildClaudeCommand:
    """Verify CLI command includes --append-system-prompt-file with jirara.md."""

    def test_command_includes_append_system_prompt_file(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt text")
        assert "--append-system-prompt-file" in cmd

    def test_command_jirara_path_ends_with_jirara_md(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt text")
        idx = cmd.index("--append-system-prompt-file")
        jirara_path = cmd[idx + 1]
        assert jirara_path.endswith("jirara.md")

    def test_command_includes_print_mode_and_dangerous_flag(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt text")
        assert "-p" in cmd
        assert "--verbose" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_command_includes_prompt_as_last_arg(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "my prompt")
        assert cmd[-1] == "my prompt"

    def test_command_includes_output_format_stream_json(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt")
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "stream-json"

    def test_command_includes_max_turns(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt")
        idx = cmd.index("--max-turns")
        assert cmd[idx + 1] == "50"

    def test_command_includes_fallback_model(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt")
        idx = cmd.index("--fallback-model")
        assert cmd[idx + 1] == "sonnet"


class TestJiraraFileValidation:
    """Verify Jirara skill file path resolution and startup validation."""

    def test_jirara_path_is_absolute(self):
        from services.executor import JIRARA_SKILL_PATH

        assert os.path.isabs(JIRARA_SKILL_PATH)

    def test_jirara_path_ends_with_expected_suffix(self):
        from services.executor import JIRARA_SKILL_PATH

        expected_suffix = os.path.join(".claude", "skills", "jirara.md")
        assert JIRARA_SKILL_PATH.endswith(expected_suffix)

    def test_validate_jirara_raises_on_missing_file(self):
        from services.executor import validate_jirara_skill

        with pytest.raises(RuntimeError, match="jirara"):
            validate_jirara_skill("/nonexistent/path/jirara.md")

    def test_validate_jirara_passes_on_existing_file(self, tmp_path):
        from services.executor import validate_jirara_skill

        fake_jirara = tmp_path / "jirara.md"
        fake_jirara.write_text("# Jirara")
        # Should not raise
        validate_jirara_skill(str(fake_jirara))


class TestBackwardCompatibility:
    """Verify executor does not modify cloned repo content."""

    def test_command_does_not_reference_claude_md(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt text")
        cmd_str = " ".join(cmd)
        assert "CLAUDE.md" not in cmd_str

    def test_command_has_no_file_copy_operations(self):
        from services.executor import build_claude_command

        cmd = build_claude_command("/usr/bin/claude", "prompt text")
        cmd_str = " ".join(cmd)
        assert "cp " not in cmd_str
        assert "mv " not in cmd_str
