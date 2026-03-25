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

os.makedirs(WORKSPACE, exist_ok=True)

# ── Jirara SOP 路徑（從專案根目錄動態解析）────────────────────────────────────
# executor.py → services/ → backend/ → 專案根目錄
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_JIRARA_SKILL_FILE = os.path.join(_PROJECT_ROOT, ".github", "skills", "jirara", "SKILL.md")


async def _resolve_base_branch(work_dir: str, requested_branch: str | None) -> str:
    """決定 PR 的 base branch：使用者指定 > dev > lab > main。
    clone 後透過 git branch -r 確認 remote 分支是否存在。
    """
    if requested_branch:
        return requested_branch

    # 使用 list form 避免 shell injection
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", work_dir, "branch", "-r",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    remote_branches = stdout.decode()

    for candidate in ("dev", "lab", "main", "master"):
        if f"origin/{candidate}" in remote_branches:
            return candidate

    return "main"


def build_prompt(jira_ticket: str, extra_prompt: str | None, base_branch: str = "dev") -> str:
    """Build the user prompt for Claude Code."""
    # 強制自主執行 + 嚴格遵守 repo 內規範
    autonomous_header = (
        "你正在自動化流程中執行，沒有人工監控。\n"
        "\n"
        "【執行規則 — 不可違反】\n"
        "1. 不得詢問使用者任何問題或等待輸入，所有決策自行判斷並直接執行\n"
        "2. 不要呈現方案讓使用者選擇，直接選擇最合適的方案執行\n"
        "3. 遇到不確定的情況，採取最保守、最安全的做法自行處理\n"
        "\n"
        "【開發流程 — 最高優先】\n"
        "4. 系統已透過 system prompt 注入 Jirara 開發流程（SKILL.md），此流程為最高優先的開發 SOP\n"
        "5. 嚴格遵照 Jirara 的步驟執行（含 branch 建立、commit、push、PR 建立、Jira 更新）\n"
        "6. 若 repo 內有其他開發流程 skill（如 dev-flow、jira-ops），以 Jirara 為準，不得覆蓋 Jirara 步驟\n"
        "\n"
        "【Repo 規範 — 次優先】\n"
        "7. 讀取並遵守 target repo 的 CLAUDE.md（若存在）\n"
        "8. Repo 內的非流程類 skill（如 api-creator、component-builder、frontend-design）照常套用\n"
        "9. 開發過程中的每個步驟（命名、架構、測試等）須符合 repo 規範\n"
        "\n"
        "\n"
    )
    prompt = autonomous_header + f"請處理 Jira 單 {jira_ticket}"
    prompt += f"\n\n【PR Base Branch】建立 PR 時，base branch 必須指定為 `{base_branch}`"
    if extra_prompt:
        prompt += f"\n\n額外指示：{extra_prompt}"
    return prompt


def build_claude_command(claude_bin: str, prompt: str, jirara_path: str = "") -> list[str]:
    """Build the CLI argument list for Claude Code.

    透過 --append-system-prompt-file 注入系統 jirara SOP，
    確保所有任務都走 jirara 開發流程，不依賴 repo 是否自帶 skill。
    """
    cmd = [
        claude_bin,
        "-p",
        "--verbose",
        "--dangerously-skip-permissions",
        "--output-format", "stream-json",
        "--max-turns", MAX_TURNS,
        "--fallback-model", FALLBACK_MODEL,
    ]
    if jirara_path and os.path.isfile(jirara_path):
        cmd += ["--append-system-prompt-file", jirara_path]
    cmd.append(prompt)
    return cmd


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
    For assistant events with tool_use blocks, event_type is refined
    with priority: mcp > skill > tool_use > assistant.
    For user events (tool results), event_type is refined to "tool_result".
    """
    if event_type == "assistant":
        msg = parsed.get("message", {})
        contents = msg.get("content", []) if isinstance(msg, dict) else []
        parts = []
        has_mcp = False
        has_skill = False
        has_tool = False
        for block in contents:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {})
                desc = inp.get("description", inp.get("command", inp.get("pattern", "")))
                # Skill tool: extract skill name from input
                if name == "Skill" and not desc:
                    desc = inp.get("skill", "")
                if isinstance(desc, str) and len(desc) > 120:
                    desc = desc[:120] + "..."
                if name.startswith("mcp__"):
                    has_mcp = True
                    prefix = "[mcp]"
                elif name == "Skill":
                    has_skill = True
                    prefix = "[skill]"
                else:
                    has_tool = True
                    prefix = "[tool]"
                parts.append(f"{prefix} {name}: {desc}" if desc else f"{prefix} {name}")
        refined = "mcp" if has_mcp else "skill" if has_skill else "tool_use" if has_tool else "assistant"
        return refined, "\n".join(parts) if parts else None
    if event_type == "user":
        result = parsed.get("tool_use_result", "")
        if isinstance(result, dict):
            result = result.get("stdout", "") or result.get("stderr", "")
        if isinstance(result, str) and len(result) > 200:
            result = result[:200] + "..."
        return "tool_result", result or None
    if event_type == "system":
        subtype = parsed.get("subtype", "")
        if subtype == "init":
            model = parsed.get("model", "?")
            return event_type, f"Session initialized (model: {model})"
        return event_type, parsed.get("message", None)
    if event_type == "result":
        subtype = parsed.get("subtype", "")
        result_text = parsed.get("result", "")
        if isinstance(result_text, str) and len(result_text) > 2000:
            result_text = result_text[:2000] + "..."
        return event_type, f"[{subtype}] {result_text}" if result_text else None
    return event_type, None


async def _stream_output(job_id: str, stream_name: str, stream):
    """Read subprocess output line by line, parse JSON events, and store in DB."""
    while True:
        try:
            line = await stream.readline()
        except ValueError:
            # 單行超過 StreamReader limit（理論上不應發生，limit 已設為 10MB）
            await _log(job_id, stream_name, "[line too long, skipped]", event_type="raw")
            continue
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


def _read_skill_content(skills_dir: str, skill_name: str) -> tuple[str, str]:
    """讀取 skill 的 description 和完整內容。Returns (description, full_content)."""
    skill_dir = os.path.join(skills_dir, skill_name)
    candidates = []
    if os.path.isdir(skill_dir):
        candidates = [os.path.join(skill_dir, f) for f in os.listdir(skill_dir) if f.endswith(".md")]
    else:
        flat = os.path.join(skills_dir, f"{skill_name}.md")
        if os.path.isfile(flat):
            candidates = [flat]

    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            description = ""
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
            return description, content
        except OSError:
            pass
    return "", ""


def _extract_skill_keywords(skill_content: str) -> list[str]:
    """從 skill 內容中抽取關鍵 code pattern（程式碼區塊內的關鍵字）。"""
    keywords = []
    in_code_block = False
    for line in skill_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block and stripped:
            # 取有意義的 token（過濾太短或太泛的）
            for token in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{3,}', stripped):
                if token not in {"const", "type", "import", "export", "from", "return",
                                  "function", "async", "await", "interface", "class"}:
                    keywords.append(token)
    return list(dict.fromkeys(keywords))[:20]  # 去重，最多取 20 個


def _read_skill_description(skills_dir: str, skill_name: str) -> str:
    """從 SKILL.md 讀取 skill 的 description frontmatter 或第一行說明。"""
    skill_dir = os.path.join(skills_dir, skill_name)
    candidates = []
    if os.path.isdir(skill_dir):
        candidates = [os.path.join(skill_dir, f) for f in os.listdir(skill_dir) if f.endswith(".md")]
    else:
        flat = os.path.join(skills_dir, f"{skill_name}.md")
        if os.path.isfile(flat):
            candidates = [flat]

    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read(1000)
            # 嘗試讀 frontmatter description
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if desc:
                        return desc
            # fallback：取第一個非空、非 frontmatter 的行
            in_frontmatter = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if not in_frontmatter and stripped and not stripped.startswith("#"):
                    return stripped[:100]
        except OSError:
            pass
    return ""


async def _emit_compliance_check(job_id: str, work_dir: str):
    """執行完成後，交叉比對 repo 規範（CLAUDE.md & skills）是否有實際被調用。"""
    db = await get_db()
    try:
        lines = ["────── 規範合規檢查 ──────"]

        # 1. CLAUDE.md — 確認 repo 有 CLAUDE.md 且 CC 有成功啟動
        claude_md_path = None
        for p in ["CLAUDE.md", ".claude/CLAUDE.md"]:
            if os.path.isfile(os.path.join(work_dir, p)):
                claude_md_path = p
                break

        cursor = await db.execute(
            "SELECT id FROM job_logs WHERE job_id = ? AND event_type = 'system' AND message LIKE '%Session initialized%'",
            (job_id,),
        )
        cc_started = await cursor.fetchone() is not None

        if claude_md_path and cc_started:
            lines.append(f"✅ CLAUDE.md 已載入（{claude_md_path}）")
        elif claude_md_path and not cc_started:
            lines.append(f"⚠️  CLAUDE.md 存在（{claude_md_path}）但 CC 未成功啟動")
        else:
            lines.append("⬜ CLAUDE.md：repo 內找不到，CC 以預設行為執行")

        # 2. Skills — 取得 repo 內的 skill 清單，與實際調用次數交叉比對
        skills_dir = os.path.join(work_dir, ".claude", "skills")
        repo_skills = []  # list of skill names in order
        if os.path.isdir(skills_dir):
            for entry in sorted(os.listdir(skills_dir)):
                entry_path = os.path.join(skills_dir, entry)
                if os.path.isdir(entry_path):
                    if any(f.endswith(".md") for f in os.listdir(entry_path)):
                        repo_skills.append(entry)
                elif entry.endswith(".md"):
                    repo_skills.append(entry[:-3])

        # 取得實際被調用的 skills 及次數
        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = ? AND event_type = 'skill'",
            (job_id,),
        )
        skill_rows = await cursor.fetchall()
        invoked_counts: dict[str, int] = {}
        for r in skill_rows:
            match = re.search(r"\[skill\] Skill:\s*(\S+)", r["message"])
            if match:
                key = match.group(1).lower()
                invoked_counts[key] = invoked_counts.get(key, 0) + 1

        # 3. 取得 git diff（本次任務的所有改動）
        diff_content = ""
        try:
            diff_proc = await asyncio.create_subprocess_exec(
                "git", "diff", "HEAD",
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            diff_stdout, _ = await asyncio.wait_for(diff_proc.communicate(), timeout=30)
            diff_content = diff_stdout.decode("utf-8", errors="replace")
        except Exception:
            pass

        if not diff_content:
            # fallback：取最後一個 commit 的 diff
            try:
                diff_proc = await asyncio.create_subprocess_exec(
                    "git", "show", "--stat", "HEAD",
                    cwd=work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                diff_stdout, _ = await asyncio.wait_for(diff_proc.communicate(), timeout=30)
                diff_content = diff_stdout.decode("utf-8", errors="replace")
            except Exception:
                pass

        if repo_skills:
            lines.append(f"\nRepo Skills 合規驗收（共 {len(repo_skills)} 個）：")
            for skill in repo_skills:
                desc, skill_content = _read_skill_content(skills_dir, skill)
                desc_str = f"  # {desc}" if desc else ""

                if not diff_content:
                    lines.append(f"  ⬜ {skill}（無法取得 diff，跳過驗收）{desc_str}")
                    continue

                # 從 skill 內容抽取關鍵 patterns，掃 diff 是否有出現
                keywords = _extract_skill_keywords(skill_content)
                matched = [kw for kw in keywords if kw in diff_content]

                if matched:
                    lines.append(f"  ✅ {skill} — 改動中偵測到規範 pattern（{', '.join(matched[:5])}）{desc_str}")
                else:
                    lines.append(f"  ⚠️  {skill} — 改動中未偵測到規範 pattern{desc_str}")
        else:
            lines.append("⬜ Skills：repo 內找不到 .claude/skills/")

        lines.append("\n──────────────────────────")
        await _log(job_id, "system", "\n".join(lines), event_type="system")
    finally:
        await db.close()


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


def _cleanup_workdir(work_dir: str) -> bool:
    """Delete work directory. Returns True on success, False on failure. Non-fatal."""
    if not os.path.exists(work_dir):
        return True
    try:
        shutil.rmtree(work_dir)
        return True
    except Exception:
        return False


async def _verify_repo_config(job_id: str, work_dir: str) -> None:
    """驗證 clone 下來的 repo 是否有 CLAUDE.md 與 .claude/skills/，並記錄到 log。"""
    lines = ["────── Repo 設定驗證 ──────"]

    # 1. 找所有 CLAUDE.md（根目錄 + .claude/）
    claude_md_paths = []
    for candidate in [
        os.path.join(work_dir, "CLAUDE.md"),
        os.path.join(work_dir, ".claude", "CLAUDE.md"),
    ]:
        if os.path.isfile(candidate):
            rel = os.path.relpath(candidate, work_dir)
            claude_md_paths.append(rel)

    if claude_md_paths:
        lines.append(f"✅ CLAUDE.md：{', '.join(claude_md_paths)}")
    else:
        lines.append("⚠️  CLAUDE.md：找不到（Claude 將以預設行為執行）")

    # 2. 找 .claude/skills/ 下的所有 skill（支援 folder/SKILL.md 與直接放 .md 兩種格式）
    skills_dir = os.path.join(work_dir, ".claude", "skills")
    if os.path.isdir(skills_dir):
        skill_names = []
        for entry in sorted(os.listdir(skills_dir)):
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                # folder 格式：skills/jirara/SKILL.md 或 skills/jirara/*.md
                md_files = [f for f in os.listdir(entry_path) if f.endswith(".md")]
                if md_files:
                    skill_names.append(entry)
            elif entry.endswith(".md"):
                # 直接放 .md 格式
                skill_names.append(entry)
        if skill_names:
            lines.append(f"✅ Skills（{len(skill_names)} 個）：{', '.join(skill_names)}")
        else:
            lines.append("⚠️  .claude/skills/ 存在但沒有找到任何 skill")
    else:
        lines.append("⚠️  Skills：找不到 .claude/skills/ 目錄")

    # 3. 檢查 .mcp.json
    mcp_json_path = os.path.join(work_dir, ".mcp.json")
    if os.path.isfile(mcp_json_path):
        try:
            with open(mcp_json_path, encoding="utf-8") as f:
                mcp_data = json.load(f)
            servers = mcp_data.get("mcpServers", {})
            if servers:
                lines.append(f"✅ .mcp.json（{len(servers)} 個 MCP servers）：{', '.join(servers.keys())}")
            else:
                lines.append("⚠️  .mcp.json 存在但 mcpServers 為空")
        except (json.JSONDecodeError, OSError):
            lines.append("⚠️  .mcp.json 存在但解析失敗")
    else:
        lines.append("⬜ .mcp.json：找不到（Claude Code 將不載入 MCP servers）")

    lines.append("──────────────────────────")
    await _log(job_id, "system", "\n".join(lines), event_type="system")


def _inject_token_to_url(repo_url: str, token: str) -> str:
    """將 GitHub token 注入 HTTPS clone URL。
    https://github.com/org/repo.git → https://x-access-token:{token}@github.com/org/repo.git
    """
    if repo_url.startswith("https://"):
        return repo_url.replace("https://", f"https://x-access-token:{token}@", 1)
    return repo_url


async def execute_job(job_id: str, repo_url: str, jira_ticket: str,
                      branch: str | None, extra_prompt: str | None,
                      github_token: str = "", jira_api_token: str = "", jira_email: str = "",
                      env_overrides: dict[str, str] | None = None):
    """Full execution: clone → claude -p → report result."""

    work_dir = os.path.join(WORKSPACE, f"{jira_ticket}-{job_id.split('-')[-1]}")
    now = datetime.now(timezone.utc).isoformat()

    try:
        await _log(job_id, "system", "🤖 執行引擎：Claude Code", event_type="system")

        # ── Step 1: Clone ──
        await _update_status(job_id, "cloning", started_at=now, work_dir=work_dir)

        # 注入 token 到 URL，log 顯示遮罩版本
        authenticated_url = _inject_token_to_url(repo_url, github_token) if github_token else repo_url
        masked_url = repo_url.replace("https://", "https://x-access-token:***@", 1) if github_token else repo_url
        await _log(job_id, "system", f"Cloning {masked_url} into {work_dir}")

        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd += ["-b", branch]
        clone_cmd += [authenticated_url, work_dir]

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

        # ── Step 1.5: 驗證 repo 的 CLAUDE.md 與 skills ──
        await _verify_repo_config(job_id, work_dir)

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

        base_branch = await _resolve_base_branch(work_dir, branch)
        await _log(job_id, "system", f"[PR base branch] {base_branch}")
        prompt = build_prompt(jira_ticket, extra_prompt, base_branch)
        claude_cmd = build_claude_command(claude_bin, prompt, _JIRARA_SKILL_FILE)

        await _log(job_id, "system", f"Running claude -p in {work_dir}")
        await _log(job_id, "system", f"Prompt: {prompt[:500]}")

        # 明確排除三個 credential key，確保只吃使用者在前端輸入的值
        _credential_keys = {"GITHUB_TOKEN", "JIRA_API_TOKEN", "JIRA_EMAIL"}
        base_env = {k: v for k, v in os.environ.items() if k not in _credential_keys}
        proc = await asyncio.create_subprocess_exec(
            *claude_cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,  # 10MB：避免 claude 大型輸出觸發 StreamReader 上限
            env={
                **base_env,
                **(env_overrides or {}),
                "GITHUB_TOKEN": github_token,
                "JIRA_API_TOKEN": jira_api_token,
                "JIRA_EMAIL": jira_email,
            },
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

        # Emit execution summary and compliance check before final status update
        await _emit_summary(job_id)
        await _emit_compliance_check(job_id, work_dir)
        await _log(job_id, "system", "done", event_type="done")

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
    finally:
        if not _cleanup_workdir(work_dir):
            await _log(job_id, "system", f"Warning: failed to clean up {work_dir}")
