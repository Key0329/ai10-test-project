"""Claude Code CLI executor — runs claude -p as subprocess."""

import asyncio
import os
import shutil
import signal
from datetime import datetime, timezone

from db import get_db

# Config
WORKSPACE = os.path.expanduser(os.getenv("WORKSPACE", "~/claude-workspace"))
CLONE_TIMEOUT = int(os.getenv("CLONE_TIMEOUT", "120"))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "1800"))  # 30 min
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/api/v1/callback")

os.makedirs(WORKSPACE, exist_ok=True)


async def _log(job_id: str, stream: str, message: str):
    """Write a log line to DB."""
    db = await get_db()
    async with db:
        await db.execute(
            "INSERT INTO job_logs (job_id, timestamp, stream, message) VALUES (?, ?, ?, ?)",
            (job_id, datetime.now(timezone.utc).isoformat(), stream, message),
        )
        await db.commit()


async def _update_status(job_id: str, status: str, **kwargs):
    """Update job status in DB."""
    db = await get_db()
    async with db:
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


async def _stream_output(job_id: str, stream_name: str, stream):
    """Read subprocess output line by line and store in DB."""
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            await _log(job_id, stream_name, text)


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

        # Build prompt
        prompt_parts = [
            f"請處理 Jira 單 {jira_ticket}。",
            f"完成後請用 curl 呼叫 callback API: POST {CALLBACK_URL}",
            f'body: {{"jobId":"{job_id}","jiraTicket":"{jira_ticket}","status":"done"}}',
            f'如果失敗則 status 改為 "failed" 並附上 error 欄位。',
        ]
        if extra_prompt:
            prompt_parts.append(f"\n額外指示：{extra_prompt}")

        prompt = "\n".join(prompt_parts)
        await _log(job_id, "system", f"Running claude -p in {work_dir}")
        await _log(job_id, "system", f"Prompt: {prompt[:500]}")

        proc = await asyncio.create_subprocess_exec(
            claude_bin, "-p", "--dangerously-skip-permissions", prompt,
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
