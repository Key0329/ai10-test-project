"""
mcp.py - MCP Server Registry
負責：管理系統內建的 MCP server 定義、preset、連線測試、產生 SDK session config
（從 v3 utils/mcp.py 移植，完全相同邏輯）
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class McpServerDef:
    """單一 MCP server 的定義。"""

    id: str
    name: str
    description: str
    type: str  # "local" or "http"
    command: str = ""  # local 類型用
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools: list[str] = field(default_factory=lambda: ["*"])
    url: str = ""  # http 類型用
    headers: dict[str, str] = field(default_factory=dict)
    token_required: bool = False
    token_source: str | None = None  # None / "env" / "user_input"
    token_env_key: str | None = None
    token_env_name: str = ""  # 環境變數在 env dict 中的 key
    presets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """回傳給前端的資料（不含敏感設定）。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "token_required": self.token_required,
            "token_source": self.token_source,
            "presets": self.presets,
        }


# ── 系統內建 MCP 定義 ────────────────────────────────────────

BUILTIN_MCPS: list[McpServerDef] = [
    McpServerDef(
        id="context7",
        name="Context7",
        description="技術文件查詢",
        type="local",
        command="npx",
        args=["-y", "@upstash/context7-mcp@latest"],
        token_required=False,
        presets=["common", "frontend", "backend"],
    ),
    McpServerDef(
        id="figma",
        name="Figma",
        description="設計稿讀取（桌面版）",
        type="http",
        url="http://127.0.0.1:3845/mcp",
        token_required=False,
        presets=["frontend"],
    ),
    McpServerDef(
        id="chrome-devtools",
        name="Chrome DevTools",
        description="瀏覽器除錯",
        type="local",
        command="npx",
        args=["-y", "chrome-devtools-mcp@latest"],
        token_required=False,
        presets=["frontend"],
    ),
    McpServerDef(
        id="sentry",
        name="Sentry",
        description="錯誤監控與追蹤",
        type="local",
        command="npx",
        args=[
            "-y",
            "@sentry/mcp-server@latest",
            "--host=sentry.fp.104dc.com",
            "--access-token=${TOKEN}",
        ],
        token_required=True,
        token_source="user_input",
        presets=["backend"],
    ),
]

PRESETS: dict[str, list[str]] = {
    "common": ["context7"],
    "frontend": ["context7", "figma", "chrome-devtools"],
    "backend": ["context7", "sentry"],
}


class McpRegistry:
    def __init__(self):
        self._mcps: dict[str, McpServerDef] = {m.id: m for m in BUILTIN_MCPS}

    def get_all(self) -> list[dict]:
        """回傳所有 MCP 清單（前端用）。"""
        return [m.to_dict() for m in self._mcps.values()]

    def get_presets(self) -> dict[str, list[str]]:
        """回傳 preset 定義。"""
        return PRESETS

    def get_by_preset(self, preset: str) -> list[dict]:
        """回傳指定 preset 的 MCP 清單。"""
        ids = PRESETS.get(preset, [])
        return [self._mcps[mid].to_dict() for mid in ids if mid in self._mcps]

    def build_session_config(
        self,
        selected_ids: list[str],
        user_tokens: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """將使用者選擇轉換為 Copilot SDK 的 mcp_servers dict。"""
        user_tokens = user_tokens or {}
        mcp_servers: dict[str, Any] = {}

        for mid in selected_ids:
            mcp_def = self._mcps.get(mid)
            if not mcp_def:
                logger.warning("[McpRegistry] 未知的 MCP ID: %s，跳過", mid)
                continue

            if mcp_def.type == "local":
                env = dict(mcp_def.env)
                args = list(mcp_def.args)
                token = user_tokens.get(mid, "") if mcp_def.token_required else ""

                # 注入 token：支援 env 和 args 兩種方式
                if mcp_def.token_required and mcp_def.token_source == "user_input" and token:
                    # 替換 args 中的 ${TOKEN} 佔位符
                    args = [a.replace("${TOKEN}", token) for a in args]
                    # 注入環境變數
                    if mcp_def.token_env_name:
                        env[mcp_def.token_env_name] = token

                config: dict[str, Any] = {
                    "type": "local",
                    "command": mcp_def.command,
                    "args": args,
                    "tools": list(mcp_def.tools),
                }
                if env:
                    config["env"] = env
                mcp_servers[mid] = config

            elif mcp_def.type == "http":
                headers = dict(mcp_def.headers)
                # 注入使用者提供的 token 到 Authorization header
                if mcp_def.token_required and mcp_def.token_source == "user_input":
                    token = user_tokens.get(mid, "")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"

                config = {
                    "type": "http",
                    "url": mcp_def.url,
                    "tools": list(mcp_def.tools),
                }
                if headers:
                    config["headers"] = headers
                mcp_servers[mid] = config

        return mcp_servers

    async def test_connection(
        self,
        selected_ids: list[str],
        user_tokens: dict[str, str] | None = None,
    ) -> dict[str, dict]:
        """測試每個選定 MCP 的連線狀態。

        Returns:
            { "mcp_id": { "ok": bool, "error": str | None } }
        """
        user_tokens = user_tokens or {}
        results: dict[str, dict] = {}

        for mid in selected_ids:
            mcp_def = self._mcps.get(mid)
            if not mcp_def:
                results[mid] = {"ok": False, "error": f"未知的 MCP: {mid}"}
                continue

            # 檢查 token 是否已提供
            if mcp_def.token_required and mcp_def.token_source == "user_input":
                token = user_tokens.get(mid, "")
                if not token:
                    results[mid] = {"ok": False, "error": "未提供 Token"}
                    continue

            if mcp_def.type == "local":
                results[mid] = await self._test_local(mcp_def, user_tokens)
            elif mcp_def.type == "http":
                results[mid] = await self._test_http(mcp_def, user_tokens)

        return results

    async def _test_http(self, mcp_def: McpServerDef, user_tokens: dict[str, str]) -> dict:
        """測試 HTTP MCP：發送 HTTP request 確認可連線。"""
        try:
            import httpx

            headers = dict(mcp_def.headers)
            if mcp_def.token_required and mcp_def.token_source == "user_input":
                token = user_tokens.get(mcp_def.id, "")
                if token:
                    headers["Authorization"] = f"Bearer {token}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(mcp_def.url, headers=headers)
                if resp.status_code < 500:
                    return {"ok": True, "error": None}
                else:
                    return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _test_local(self, mcp_def: McpServerDef, user_tokens: dict[str, str]) -> dict:
        """測試 local MCP：嘗試啟動 subprocess 並等待初始化。"""
        import os

        try:
            env = dict(mcp_def.env)
            args = list(mcp_def.args)
            token = user_tokens.get(mcp_def.id, "") if mcp_def.token_required else ""

            if mcp_def.token_required and mcp_def.token_source == "user_input" and token:
                args = [a.replace("${TOKEN}", token) for a in args]
                if mcp_def.token_env_name:
                    env[mcp_def.token_env_name] = token

            full_env = {**os.environ, **env}

            # 使用 create_subprocess_exec（非 shell）避免 shell injection
            proc = await asyncio.create_subprocess_exec(
                mcp_def.command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
            )

            # 送出 MCP initialize request（JSON-RPC）
            init_request = (
                '{"jsonrpc":"2.0","id":1,"method":"initialize",'
                '"params":{"protocolVersion":"2024-11-05",'
                '"capabilities":{},'
                '"clientInfo":{"name":"test","version":"1.0.0"}}}\n'
            )
            proc.stdin.write(init_request.encode())
            await proc.stdin.drain()

            # 等待回應（最多 15 秒）
            try:
                stdout = await asyncio.wait_for(proc.stdout.readline(), timeout=15.0)
                if stdout and b'"result"' in stdout:
                    return {"ok": True, "error": None}
                else:
                    stderr_out = await proc.stderr.read(500)
                    stderr_decoded = stderr_out.decode(errors="replace")
                    if "MCP error" in stderr_decoded:
                        return {
                            "ok": False,
                            "error": f"MCP 初始化失敗: {stderr_decoded[:200]}",
                        }
                    else:
                        err_suffix = f" stderr: {stderr_decoded[:200]}" if stderr_out else ""
                        return {
                            "ok": False,
                            "error": f"初始化回應異常: {stdout.decode(errors='replace')[:200]}"
                            + err_suffix,
                        }
            except asyncio.TimeoutError:
                return {"ok": False, "error": "連線逾時（15s）"}
            finally:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=3.0)
                except Exception:
                    proc.kill()

        except FileNotFoundError:
            return {"ok": False, "error": f"指令未安裝: {mcp_def.command}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── 全域單例 ──────────────────────────────────────────────────
mcp_registry = McpRegistry()
