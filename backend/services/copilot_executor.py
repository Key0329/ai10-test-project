"""GitHub Copilot SDK executor — 參照 v3 agent_action.py 移植。"""

import asyncio
import json
import os
import re
import shutil
from datetime import datetime, timezone

import urllib.request
import urllib.error

from db import get_db
from services.executor import (
    _log,
    _update_status,
    _cleanup_workdir,
    _inject_token_to_url,
    _resolve_base_branch,
    WORKSPACE,
    CLONE_TIMEOUT,
    JOB_TIMEOUT,
)

try:
    from copilot import CopilotClient, PermissionHandler
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


# ── Prompt ────────────────────────────────────────────────────────────────────

def _build_copilot_prompt(jira_ticket: str, extra_prompt: str | None, base_branch: str = "dev") -> str:
    prompt = (
        "你正在自動化流程中執行，沒有人工監控。\n"
        "\n"
        "【執行規則 — 不可違反】\n"
        "1. 不得詢問使用者任何問題，所有決策自行判斷並直接執行\n"
        "2. 不要呈現方案讓使用者選擇，直接選擇最合適的方案執行\n"
        "3. 遇到不確定的情況，採取最保守、最安全的做法自行處理\n"
        "\n"
        "【開發流程 — 最高優先】\n"
        "4. 系統已注入 Jirara 開發流程至 .github/skills/jirara/，此為最高優先的開發 SOP\n"
        "5. 嚴格遵照 Jirara 的步驟執行（含 branch 建立、commit、push、PR 建立、Jira 更新）\n"
        "6. 若 repo 內有其他開發流程 skill（如 dev-flow、jira-ops），以 Jirara 為準，不得覆蓋 Jirara 步驟\n"
        "\n"
        "【Repo 規範 — 次優先】\n"
        "7. 讀取並遵守 .github/copilot-instructions.md（若存在）\n"
        "8. Repo 內的非流程類 skill（如 api-creator、component-builder、frontend-design）照常套用\n"
        "\n"
        f"【PR Base Branch】建立 PR 時，base branch 必須指定為 `{base_branch}`\n"
        "\n"
        f"請處理 Jira 單 {jira_ticket}"
    )
    if extra_prompt:
        prompt += f"\n\n額外指示：{extra_prompt}"
    return prompt


def _build_system_message() -> str:
    """對應 v3 _build_system_message()。"""
    return (
        "你是一位資深軟體工程師，正在為一個真實專案進行開發工作。\n"
        "你的工作目錄就是 repo 根目錄，你可以直接讀取和修改裡面的檔案。\n"
        "\n"
        "## 最高優先：Jirara 開發流程\n"
        "系統已將 Jirara（jirara skill）注入到 .github/skills/jirara/，此為最高優先的開發 SOP。\n"
        "1. `cat .github/skills/jirara/SKILL.md` — 讀取 Jirara 完整流程\n"
        "2. 嚴格遵照 Jirara 步驟執行，不得跳過或簡化\n"
        "3. 若 repo 內有其他開發流程 skill（如 dev-flow、jira-ops），以 Jirara 為準，不得覆蓋 Jirara 步驟\n"
        "\n"
        "## 次優先：Repo 自帶規範\n"
        "4. `.github/copilot-instructions.md` — coding rules（若存在）\n"
        "5. `.github/skills/` 下的非流程類 skill（如 api-creator、component-builder、frontend-design）照常套用\n"
        "6. 開發過程中的每個步驟（命名、架構、測試等）須符合 repo 規範\n"
    )


# ── 系統專案 skills 目錄（backup jirara 來源）────────────────────────────────

# copilot_executor.py → services/ → backend/ → 專案根目錄
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SYSTEM_SKILLS_DIR = os.path.join(_PROJECT_ROOT, ".github", "skills")


def _load_dotenv_value(key: str) -> str:
    """從專案根目錄的 .env 讀取指定 key 的值（簡易解析，不依賴外部套件）。"""
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    if not os.path.isfile(env_path):
        return ""
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return ""


# ── Skill 目錄偵測（對應 v3 _detect_skill_dirs）─────────────────────────────

def _detect_skill_dirs(work_dir: str) -> list[str]:
    """偵測 target repo 的 skill 目錄。
    系統 skills 透過 _inject_system_skills() 直接複製進 work_dir，
    所以這裡只需回傳 target repo 自身的 skill 目錄。
    """
    dirs = []
    github_dir = os.path.join(work_dir, ".github")

    # 單一 .github/SKILL.md
    if os.path.isfile(os.path.join(github_dir, "SKILL.md")):
        dirs.append(work_dir)

    # 多 skills: .github/skills/*/SKILL.md
    skills_dir = os.path.join(github_dir, "skills")
    if os.path.isdir(skills_dir):
        found = [
            entry for entry in sorted(os.listdir(skills_dir))
            if os.path.isdir(os.path.join(skills_dir, entry))
            and os.path.isfile(os.path.join(skills_dir, entry, "SKILL.md"))
        ]
        if found:
            dirs.append(skills_dir)

    return dirs


def _inject_system_skills(work_dir: str) -> list[str]:
    """將系統專案的 jirara skill 強制複製到 work_dir/.github/skills/jirara/。
    若 target repo 已有 jirara 目錄，先刪除再重新複製（確保使用最新系統版本）。
    回傳實際注入的 skill 名稱列表。
    """
    injected = []
    src = os.path.join(_SYSTEM_SKILLS_DIR, "jirara")
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        return injected

    target_skills_dir = os.path.join(work_dir, ".github", "skills")
    dst = os.path.join(target_skills_dir, "jirara")

    if os.path.isdir(dst):
        shutil.rmtree(dst)

    os.makedirs(target_skills_dir, exist_ok=True)
    shutil.copytree(src, dst)
    injected.append("jirara")
    return injected


# ── Repo 設定驗證 ─────────────────────────────────────────────────────────────

async def _verify_copilot_repo_config(job_id: str, work_dir: str) -> None:
    lines = ["────── Repo 設定驗證（Copilot 模式） ──────"]

    # 系統專案 skills（jirara 備援來源）
    if os.path.isdir(_SYSTEM_SKILLS_DIR):
        sys_skills = [
            e for e in sorted(os.listdir(_SYSTEM_SKILLS_DIR))
            if os.path.isfile(os.path.join(_SYSTEM_SKILLS_DIR, e, "SKILL.md"))
        ]
        lines.append(f"✅ 系統 skills（{len(sys_skills)} 個）：{', '.join(sys_skills)}")

    copilot_md = os.path.join(work_dir, ".github", "copilot-instructions.md")
    if os.path.isfile(copilot_md):
        lines.append("✅ .github/copilot-instructions.md 已找到")
    else:
        lines.append("⚠️  .github/copilot-instructions.md：找不到")

    skills_dir = os.path.join(work_dir, ".github", "skills")
    if os.path.isdir(skills_dir):
        skill_names = [
            entry for entry in sorted(os.listdir(skills_dir))
            if os.path.isfile(os.path.join(skills_dir, entry, "SKILL.md"))
        ]
        if skill_names:
            lines.append(f"✅ Skills（{len(skill_names)} 個）：{', '.join(skill_names)}")
        else:
            lines.append("⚠️  .github/skills/ 找不到任何 SKILL.md")
    else:
        lines.append("⚠️  .github/skills/ 目錄不存在")

    # 4. 檢查 .mcp.json
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
        lines.append("⬜ .mcp.json：找不到")

    lines.append("──────────────────────────")
    await _log(job_id, "system", "\n".join(lines), event_type="system")


# ── Pre-flight 連通性測試 ──────────────────────────────────────────────────────

async def _preflight_check(
    job_id: str,
    github_token: str,
    jira_api_token: str,
    jira_email: str,
    jira_base_url: str,
) -> None:
    """在啟動 Copilot SDK 前測試 GitHub 與 Jira API 連通性。
    任一失敗都 raise RuntimeError，讓 job 提早失敗並顯示有意義的錯誤。
    """
    lines = ["────── Pre-flight 連通性測試 ──────"]

    # ── GitHub API ─────────────────────────────────────────────────────────────
    if github_token:
        try:
            req = urllib.request.Request(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            loop = asyncio.get_event_loop()
            resp_body = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=10).read(),
            )
            gh_user = json.loads(resp_body).get("login", "unknown")
            lines.append(f"✅ GitHub API：已連線（使用者：{gh_user}）")
        except urllib.error.HTTPError as e:
            lines.append(f"❌ GitHub API：HTTP {e.code} — token 可能無效")
            await _log(job_id, "system", "\n".join(lines), event_type="system")
            raise RuntimeError(f"GitHub API 連線失敗（HTTP {e.code}）：token 可能無效或權限不足")
        except Exception as e:
            lines.append(f"❌ GitHub API：連線失敗 — {e}")
            await _log(job_id, "system", "\n".join(lines), event_type="system")
            raise RuntimeError(f"GitHub API 連線失敗：{e}")
    else:
        lines.append("⚠️  GitHub token 未提供，跳過 GitHub API 測試")

    # ── Jira API ───────────────────────────────────────────────────────────────
    if jira_base_url and jira_api_token and jira_email:
        import base64
        creds = base64.b64encode(f"{jira_email}:{jira_api_token}".encode()).decode()
        try:
            req = urllib.request.Request(
                f"{jira_base_url.rstrip('/')}/rest/api/3/myself",
                headers={
                    "Authorization": f"Basic {creds}",
                    "Accept": "application/json",
                },
            )
            loop = asyncio.get_event_loop()
            resp_body = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=10).read(),
            )
            jira_user = json.loads(resp_body).get("displayName", "unknown")
            lines.append(f"✅ Jira API：已連線（使用者：{jira_user}）")
        except urllib.error.HTTPError as e:
            lines.append(f"❌ Jira API：HTTP {e.code} — 憑證可能無效")
            await _log(job_id, "system", "\n".join(lines), event_type="system")
            raise RuntimeError(f"Jira API 連線失敗（HTTP {e.code}）：API token 或 email 可能不正確")
        except Exception as e:
            lines.append(f"❌ Jira API：連線失敗 — {e}")
            await _log(job_id, "system", "\n".join(lines), event_type="system")
            raise RuntimeError(f"Jira API 連線失敗：{e}")
    else:
        missing = []
        if not jira_base_url:
            missing.append("JIRA_BASE_URL")
        if not jira_api_token:
            missing.append("jira_api_token")
        if not jira_email:
            missing.append("jira_email")
        lines.append(f"⚠️  Jira 設定不完整（缺少：{', '.join(missing)}），跳過測試")

    lines.append("──────────────────────────")
    await _log(job_id, "system", "\n".join(lines), event_type="system")


# ── MCP 使用統計 ──────────────────────────────────────────────────────────────

async def _emit_copilot_mcp_summary(job_id: str) -> None:
    """統計 Copilot job 實際使用的 MCP servers，格式對齊 Claude Code executor。"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = ? AND event_type = 'mcp'",
            (job_id,),
        )
        rows = await cursor.fetchall()
        mcp_servers: set[str] = set()
        for r in rows:
            match = re.search(r"mcp__(\w+)__", r["message"])
            if match:
                mcp_servers.add(match.group(1))
        mcp_str = ", ".join(sorted(mcp_servers)) if mcp_servers else "(none)"
        await _log(job_id, "system",
            f"────── 執行摘要 ──────\nMCP：{mcp_str}\n──────────────────────",
            event_type="system")
    finally:
        await db.close()


# ── 主執行函數 ─────────────────────────────────────────────────────────────────

async def execute_copilot_job(
    job_id: str,
    repo_url: str,
    jira_ticket: str,
    branch: str | None,
    extra_prompt: str | None,
    github_token: str = "",
    jira_api_token: str = "",
    jira_email: str = "",
    env_overrides: dict[str, str] | None = None,
):
    """對應 v3 AgentService.run()，整合 v4 的 logging / status 機制。"""
    if not _SDK_AVAILABLE:
        await _update_status(
            job_id, "failed",
            error_message="github-copilot-sdk 未安裝。請執行：uv add github-copilot-sdk",
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        return

    work_dir = os.path.join(WORKSPACE, f"{jira_ticket}-{job_id.split('-')[-1]}")
    now = datetime.now(timezone.utc).isoformat()

    try:
        await _log(job_id, "system", "🤖 執行引擎：GitHub Copilot SDK", event_type="system")

        # ── Step 1: Clone ──────────────────────────────────────────────────────
        await _update_status(job_id, "cloning", started_at=now, work_dir=work_dir)

        authenticated_url = _inject_token_to_url(repo_url, github_token) if github_token else repo_url
        masked_url = repo_url.replace("https://", "https://x-access-token:***@", 1) if github_token else repo_url
        await _log(job_id, "system", f"[Copilot] Cloning {masked_url} into {work_dir}")

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
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=CLONE_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"git clone timed out ({CLONE_TIMEOUT}s)")

        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        await _log(job_id, "system", "Clone complete")

        # ── Step 1.5: 驗證 repo 設定 ───────────────────────────────────────────
        await _verify_copilot_repo_config(job_id, work_dir)

        # ── Step 1.55: 注入系統 skills 到 work_dir ─────────────────────────────
        injected = _inject_system_skills(work_dir)
        if injected:
            await _log(job_id, "system",
                f"[Copilot] 注入系統 skills：{', '.join(injected)}（target repo 已有同名 skill 則跳過）",
                event_type="system")

        # ── Step 1.6: Pre-flight 連通性測試 ────────────────────────────────────
        _jira_base_url = (
            os.environ.get("JIRA_BASE_URL")
            or os.environ.get("JIRA_URL")
            or _load_dotenv_value("JIRA_BASE_URL")
            or _load_dotenv_value("JIRA_URL")
            or ""
        )
        await _preflight_check(job_id, github_token, jira_api_token, jira_email, _jira_base_url)

        # ── Step 2: Copilot SDK 執行（對應 v3 AgentService.run 核心） ───────────
        await _update_status(job_id, "running")

        skill_dirs = _detect_skill_dirs(work_dir)
        await _log(job_id, "system", f"[Copilot] skill_directories = {skill_dirs}")

        base_branch = await _resolve_base_branch(work_dir, branch)
        await _log(job_id, "system", f"[PR base branch] {base_branch}")
        prompt = _build_copilot_prompt(jira_ticket, extra_prompt, base_branch)
        await _log(job_id, "system", f"[Copilot] Starting SDK session in {work_dir}")

        # 暫時注入 env vars 供 CLI 子進程繼承（對應 v3 的環境假設）
        # COPILOT_GITHUB_TOKEN 專門給 Copilot SDK 使用（從 .env 或環境變數讀取）
        # github_token（前端傳入）只用於 git clone / PR 等 git 操作
        copilot_token = (
            os.environ.get("COPILOT_GITHUB_TOKEN")
            or _load_dotenv_value("COPILOT_GITHUB_TOKEN")
            or github_token  # fallback：若未設定則沿用 git token
        )
        if copilot_token != github_token:
            await _log(job_id, "system", "[Copilot] 使用 COPILOT_GITHUB_TOKEN 作為 SDK 憑證", event_type="system")

        _credential_keys = {"GITHUB_TOKEN", "JIRA_API_TOKEN", "JIRA_EMAIL"}
        saved_env = {k: os.environ.get(k) for k in _credential_keys}
        os.environ["GITHUB_TOKEN"] = copilot_token
        os.environ["JIRA_API_TOKEN"] = jira_api_token
        os.environ["JIRA_EMAIL"] = jira_email
        jira_base_url = (
            os.environ.get("JIRA_BASE_URL")
            or os.environ.get("JIRA_URL")
            or _load_dotenv_value("JIRA_BASE_URL")
            or _load_dotenv_value("JIRA_URL")
            or ""
        )
        if jira_base_url:
            os.environ["JIRA_BASE_URL"] = jira_base_url

        # ── v3 模式：CopilotClient() + await client.start() ───────────────────
        client = CopilotClient()
        await client.start()

        full_output: list[str] = []

        try:
            session_config = dict(
                model="claude-sonnet-4.6",
                streaming=True,
                working_directory=work_dir,
                skill_directories=skill_dirs,
                system_message={
                    "mode": "replace",
                    "content": _build_system_message(),
                },
                on_permission_request=PermissionHandler.approve_all,
            )

            # 注入 MCP servers 設定：repo .mcp.json（主）+ 使用者補充（次）
            from services.mcp_loader import load_repo_mcp_config, convert_to_copilot_format, detect_missing_env_vars

            repo_mcp_raw = load_repo_mcp_config(work_dir)
            repo_mcp = convert_to_copilot_format(repo_mcp_raw, env_overrides=env_overrides or {}) if repo_mcp_raw else {}

            if repo_mcp_raw:
                missing_vars = detect_missing_env_vars(repo_mcp_raw)
                if missing_vars:
                    await _log(job_id, "system",
                        f"[Copilot] ⚠️ .mcp.json 引用了未定義的環境變數：{', '.join(missing_vars)}",
                        event_type="system")

            if repo_mcp:
                session_config["mcp_servers"] = repo_mcp
                repo_keys = list(repo_mcp.keys())
                supp_keys = []
                parts = []
                if repo_keys:
                    parts.append(f"repo: {', '.join(repo_keys)}")
                if supp_keys:
                    parts.append(f"補充: {', '.join(supp_keys)}")
                await _log(job_id, "system",
                    f"[Copilot] 載入 MCP servers（{' | '.join(parts)}）",
                    event_type="system")

            session = await client.create_session(**session_config)

            # ── v3 事件處理模式 ────────────────────────────────────────────────
            done = asyncio.Event()
            session_errors: list[str] = []

            def on_event(event):
                event_type = event.type.value if hasattr(event.type, "value") else str(event.type)
                data = getattr(event, "data", None)

                if event_type == "assistant.message_delta":
                    delta = getattr(data, "delta_content", "") if data else ""
                    if delta:
                        full_output.append(delta)
                        asyncio.ensure_future(
                            _log(job_id, "stdout", str(delta)[:500], event_type="assistant")
                        )

                elif event_type == "assistant.message":
                    content = getattr(data, "content", None) if data else None
                    if content:
                        full_output.append(content)
                        asyncio.ensure_future(
                            _log(job_id, "stdout", str(content)[:500], event_type="assistant")
                        )

                elif event_type == "tool.execution_start":
                    tool_name = (
                        getattr(data, "tool_name", None) or getattr(data, "name", None)
                        if data else None
                    ) or "unknown"
                    args = getattr(data, "arguments", None) if data else None
                    # 只取最有意義的文字欄位，不顯示整串 JSON
                    args_display = ""
                    if isinstance(args, dict):
                        # 依優先順序取第一個有值的文字欄位
                        for key in ("command", "path", "content", "query", "url", "input", "text"):
                            if args.get(key):
                                val = str(args[key])
                                # 只取第一行，避免多行指令塞爆畫面
                                first_line = val.split("\n")[0]
                                args_display = first_line[:200] + ("..." if len(val) > 200 or "\n" in val else "")
                                break
                    elif args:
                        args_display = str(args)[:200]
                    # 偵測 MCP tool call（mcp__ 前綴）
                    is_mcp = tool_name.startswith("mcp__")
                    prefix_tag = "[mcp]" if is_mcp else "[tool]"
                    evt_type = "mcp" if is_mcp else "tool_use"
                    msg = f"{prefix_tag} ▶ {tool_name}: {args_display}" if args_display else f"{prefix_tag} ▶ {tool_name}"
                    asyncio.ensure_future(
                        _log(job_id, "stdout", msg, event_type=evt_type)
                    )

                elif event_type == "tool.execution_progress":
                    partial = getattr(data, "partial_output", None) if data else None
                    progress_msg = getattr(data, "progress_message", None) if data else None
                    tool_name = (
                        getattr(data, "tool_name", None) or getattr(data, "name", None)
                        if data else None
                    ) or ""
                    display = partial or progress_msg
                    if display:
                        is_mcp = tool_name.startswith("mcp__") if tool_name else False
                        prefix = f"[tool:{tool_name}] " if tool_name else "[tool] "
                        progress_evt_type = "mcp" if is_mcp else "tool_use"
                        asyncio.ensure_future(
                            _log(job_id, "stdout", f"{prefix}{str(display)[:500]}", event_type=progress_evt_type)
                        )

                elif event_type == "tool.execution_complete":
                    # 只有在有 result 時才顯示，避免顯示無意義的 [tool] tool.execution_complete
                    result = (getattr(data, "result", None) or getattr(data, "output", None)) if data else None
                    if result is not None:
                        tool_name = (
                            getattr(data, "tool_name", None) or getattr(data, "name", None)
                            if data else None
                        ) or ""
                        # 優先取 Result.content（SDK 物件），再試 dict["content"]，最後才 str()
                        if hasattr(result, "content") and result.content:
                            result_str = str(result.content)
                        elif isinstance(result, dict) and result.get("content"):
                            result_str = str(result["content"])
                        elif isinstance(result, str):
                            result_str = result
                        else:
                            result_str = str(result)
                        is_mcp = tool_name.startswith("mcp__")
                        prefix_tag = "[mcp]" if is_mcp else "[tool]"
                        evt_type = "mcp" if is_mcp else "tool_result"
                        prefix = f"{prefix_tag} ✓ {tool_name} → " if tool_name else f"{prefix_tag} ✓ "
                        asyncio.ensure_future(
                            _log(job_id, "stdout", prefix + result_str[:400], event_type=evt_type)
                        )
                    # result 為 None 時靜默跳過，不輸出任何訊息

                elif event_type == "session.error":
                    msg = getattr(data, "message", str(data)) if data else event_type
                    session_errors.append(str(msg))
                    asyncio.ensure_future(
                        _log(job_id, "stderr", str(msg)[:500], event_type="raw")
                    )
                    done.set()

                elif event_type == "session.idle":
                    asyncio.ensure_future(
                        _log(job_id, "system", "[Copilot] Session idle — 執行完成", event_type="system")
                    )
                    done.set()

            session.on(on_event)

            # v4 SDK send 接受 str（v3 是 dict，已適配）
            await session.send(prompt)
            await asyncio.wait_for(done.wait(), timeout=float(JOB_TIMEOUT))

            if session_errors:
                raise RuntimeError(f"Session error: {session_errors[0]}")

        finally:
            # 還原 env vars
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            try:
                await client.stop()
            except Exception:
                pass

        # ── MCP 使用統計（對齊 Claude Code executor 的 _emit_summary） ────
        await _emit_copilot_mcp_summary(job_id)

        await _log(job_id, "system", "[Copilot] 執行完成")
        await _update_status(
            job_id, "completed",
            exit_code=0,
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
