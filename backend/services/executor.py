"""Claude Code CLI executor — runs claude -p as subprocess."""

import asyncio
import json
import os
import re
import shutil
import signal
from datetime import datetime, timezone

from db import get_db

# Config
WORKSPACE = os.path.expanduser(os.getenv("WORKSPACE", "~/claude-workspace"))
CLONE_TIMEOUT = int(os.getenv("CLONE_TIMEOUT", "120"))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "1800"))  # 30 min
MAX_TURNS = os.getenv("MAX_TURNS", "50")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "sonnet")

# Jirara skill path — resolved from project root
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
JIRARA_SKILL_PATH = os.getenv(
    "JIRARA_SKILL_PATH",
    os.path.join(_PROJECT_ROOT, ".claude", "skills", "jirara.md"),
)

os.makedirs(WORKSPACE, exist_ok=True)


def validate_jirara_skill(path: str) -> None:
    """Raise RuntimeError if the Jirara skill file does not exist."""
    if not os.path.isfile(path):
        raise RuntimeError(
            f"Jirara skill file not found: {path}"
        )


def build_prompt(jira_ticket: str, extra_prompt: str | None) -> str:
    """Build the user prompt for Claude Code."""
    prompt = f"請處理 Jira 單 {jira_ticket}"
    if extra_prompt:
        prompt += f"\n\n額外指示：{extra_prompt}"
    return prompt


def build_claude_command(claude_bin: str, prompt: str) -> list[str]:
    """Build the CLI argument list for Claude Code."""
    return [
        claude_bin,
        "-p",
        "--verbose",
        "--dangerously-skip-permissions",
        "--output-format", "stream-json",
        "--max-turns", MAX_TURNS,
        "--fallback-model", FALLBACK_MODEL,
        "--append-system-prompt-file",
        JIRARA_SKILL_PATH,
        prompt,
    ]


# Validate on module load
validate_jirara_skill(JIRARA_SKILL_PATH)


async def _log(
    job_id: str,
    stream: str,
    message: str,
    event_type: str = "raw",
    metadata: str | None = None,
):
    """Write a log line to DB."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO job_logs (job_id, timestamp, stream, message, event_type, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, datetime.now(timezone.utc).isoformat(), stream, message, event_type, metadata),
        )
        await db.commit()
    finally:
        await db.close()


async def _update_status(job_id: str, status: str, **kwargs):
    """Update job status in DB."""
    db = await get_db()
    try:
        sets = ["status = ?"]
        vals = [status]
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(job_id)
        await db.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals
        )
        await db.commit()
    finally:
        await db.close()


def _extract_display_message(event_type: str, parsed: dict) -> tuple[str, str | None]:
    """Extract a human-readable message and refined event_type from a stream-json event.

    Returns (refined_event_type, display_message).
    For assistant events with MCP/Skill tool_use, event_type is refined
    with priority: mcp > skill > assistant.
    """
    if event_type == "assistant":
        msg = parsed.get("message", {})
        contents = msg.get("content", []) if isinstance(msg, dict) else []
        parts = []
        has_mcp = False
        has_skill = False
        for block in contents:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {})
                desc = inp.get("description", inp.get("command", inp.get("pattern", "")))
                if isinstance(desc, str) and len(desc) > 120:
                    desc = desc[:120] + "..."
                if name.startswith("mcp__"):
                    has_mcp = True
                    prefix = "[mcp]"
                elif name == "Skill":
                    has_skill = True
                    prefix = "[skill]"
                else:
                    prefix = "[tool]"
                parts.append(f"{prefix} {name}: {desc}" if desc else f"{prefix} {name}")
        refined = "mcp" if has_mcp else "skill" if has_skill else "assistant"
        return refined, "\n".join(parts) if parts else None
    if event_type == "user":
        result = parsed.get("tool_use_result", "")
        if isinstance(result, dict):
            result = result.get("stdout", "") or result.get("stderr", "")
        if isinstance(result, str) and len(result) > 200:
            result = result[:200] + "..."
        return event_type, result or None
    if event_type == "system":
        subtype = parsed.get("subtype", "")
        if subtype == "init":
            model = parsed.get("model", "?")
            return event_type, f"Session initialized (model: {model})"
        return event_type, parsed.get("message", None)
    if event_type == "result":
        subtype = parsed.get("subtype", "")
        result_text = parsed.get("result", "")
        if isinstance(result_text, str) and len(result_text) > 300:
            result_text = result_text[:300] + "..."
        return event_type, f"[{subtype}] {result_text}" if result_text else None
    return event_type, None


async def _stream_output(job_id: str, stream_name: str, stream):
    """Read subprocess output line by line, parse JSON events, and store in DB."""
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            event_type = parsed.get("type") if isinstance(parsed, dict) else None
            if event_type:
                refined_type, display = _extract_display_message(event_type, parsed)
                display = display or f"[{event_type}]"
                await _log(job_id, stream_name, display, event_type=refined_type, metadata=text)
            else:
                await _log(job_id, stream_name, text)
        except (json.JSONDecodeError, ValueError):
            await _log(job_id, stream_name, text)


async def _emit_summary(job_id: str):
    """Emit an execution summary log with token/cost/MCP/skills data."""
    db = await get_db()
    try:
        # 1. Find result event metadata
        cursor = await db.execute(
            "SELECT metadata FROM job_logs WHERE job_id = ? AND event_type = 'result' ORDER BY id DESC LIMIT 1",
            (job_id,),
        )
        row = await cursor.fetchone()
        if not row or not row["metadata"]:
            return  # No result event — skip summary

        try:
            result_data = json.loads(row["metadata"])
        except (json.JSONDecodeError, TypeError):
            return

        # 2. Parse token/cost data
        usage = result_data.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        cache_read = usage.get("cache_read_input_tokens")
        cost = result_data.get("total_cost_usd")
        turns = result_data.get("num_turns")

        def _fmt(val):
            if val is None:
                return "N/A"
            if isinstance(val, float):
                return f"{val:.4f}"
            return f"{val:,}" if isinstance(val, int) else str(val)

        # 3. Collect MCP server names
        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = ? AND event_type = 'mcp'",
            (job_id,),
        )
        mcp_rows = await cursor.fetchall()
        mcp_servers = set()
        for r in mcp_rows:
            match = re.search(r"mcp__(\w+)__", r["message"])
            if match:
                mcp_servers.add(match.group(1))
        mcp_str = ", ".join(sorted(mcp_servers)) if mcp_servers else "(none)"

        # 4. Collect skill names
        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = ? AND event_type = 'skill'",
            (job_id,),
        )
        skill_rows = await cursor.fetchall()
        skills = set()
        for r in skill_rows:
            match = re.search(r"\[skill\] Skill:\s*(\S+)", r["message"])
            if match:
                skills.add(match.group(1))
        skills_str = ", ".join(sorted(skills)) if skills else "(none)"

        # 5. Build summary
        summary = (
            f"────── 執行摘要 ──────\n"
            f"Token：input {_fmt(input_tokens)} / output {_fmt(output_tokens)}"
            f" / cache read {_fmt(cache_read)}\n"
            f"成本：${_fmt(cost)}\n"
            f"Turns：{_fmt(turns)}\n"
            f"MCP：{mcp_str}\n"
            f"Skills：{skills_str}\n"
            f"──────────────────────"
        )

        await _log(job_id, "system", summary, event_type="system")
    finally:
        await db.close()


async def execute_job(job_id: str, repo_url: str, jira_ticket: str,
                      branch: str | None, extra_prompt: str | None):
    """Full execution: clone → claude -p → report result."""

    work_dir = os.path.join(WORKSPACE, f"{jira_ticket}-{job_id.split('-')[-1]}")
    now = datetime.now(timezone.utc).isoformat()

    try:
        # ── Step 1: Clone ──
        await _update_status(job_id, "cloning", started_at=now, work_dir=work_dir)
        await _log(job_id, "system", f"Cloning {repo_url} into {work_dir}")

        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd += ["-b", branch]
        clone_cmd += [repo_url, work_dir]

        proc = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=CLONE_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"git clone timed out ({CLONE_TIMEOUT}s)")

        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        await _log(job_id, "system", "Clone complete")

        # ── Step 2: Run Claude Code ──
        await _update_status(job_id, "running")

        # Find claude binary
        claude_bin = shutil.which("claude")
        if not claude_bin:
            # Common paths on macOS
            for p in ["/opt/homebrew/bin/claude", "/usr/local/bin/claude"]:
                if os.path.exists(p):
                    claude_bin = p
                    break
        if not claude_bin:
            raise RuntimeError("claude CLI not found in PATH")

        prompt = build_prompt(jira_ticket, extra_prompt)
        claude_cmd = build_claude_command(claude_bin, prompt)

        await _log(job_id, "system", f"Running claude -p in {work_dir}")
        await _log(job_id, "system", f"Prompt: {prompt[:500]}")

        proc = await asyncio.create_subprocess_exec(
            *claude_cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        # Stream output concurrently
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _stream_output(job_id, "stdout", proc.stdout),
                    _stream_output(job_id, "stderr", proc.stderr),
                    proc.wait(),
                ),
                timeout=JOB_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.send_signal(signal.SIGTERM)
            await asyncio.sleep(5)
            if proc.returncode is None:
                proc.kill()
            raise RuntimeError(f"Job timed out ({JOB_TIMEOUT}s)")

        exit_code = proc.returncode
        await _log(job_id, "system", f"Claude exited with code {exit_code}")

        # Emit execution summary before final status update
        await _emit_summary(job_id)

        if exit_code == 0:
            await _update_status(
                job_id, "completed",
                exit_code=exit_code,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            await _update_status(
                job_id, "failed",
                exit_code=exit_code,
                error_message=f"Claude exited with code {exit_code}",
                finished_at=datetime.now(timezone.utc).isoformat(),
            )

    except Exception as e:
        await _log(job_id, "error", str(e))
        await _update_status(
            job_id, "failed",
            error_message=str(e),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
