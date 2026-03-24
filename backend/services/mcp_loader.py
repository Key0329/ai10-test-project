"""
mcp_loader.py - 從 repo 讀取 .mcp.json 並轉換為 Copilot SDK 格式
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def load_repo_mcp_config(work_dir: str) -> dict:
    """讀取 repo 的 .mcp.json，回傳 mcpServers dict。

    若不存在或解析失敗回傳空 dict。
    """
    mcp_json_path = os.path.join(work_dir, ".mcp.json")
    if not os.path.isfile(mcp_json_path):
        return {}

    try:
        with open(mcp_json_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("mcpServers", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse .mcp.json: %s", e)
        return {}


def convert_to_copilot_format(
    mcp_servers: dict,
    env_overrides: dict[str, str] | None = None,
) -> dict:
    """將 .mcp.json 的 mcpServers 格式轉換為 Copilot SDK mcp_servers 格式。

    轉換規則：
    - type: "stdio" (或無 type) → "local"
    - type: "sse" / "streamable-http" → "http"
    - 自動加 tools: ["*"]
    - 展開 ${VAR} 引用（優先用 env_overrides，其次 os.environ）
    """
    env_overrides = env_overrides or {}
    result = {}

    for name, server in mcp_servers.items():
        server_type = server.get("type", "stdio")

        if server_type in ("stdio", ""):
            config: dict = {
                "type": "local",
                "command": server.get("command", ""),
                "args": _expand_list(server.get("args", []), env_overrides),
                "tools": ["*"],
            }
            env = server.get("env")
            if env:
                config["env"] = _expand_dict(env, env_overrides)
            result[name] = config

        elif server_type in ("sse", "streamable-http"):
            config = {
                "type": "http",
                "url": _expand_str(server.get("url", ""), env_overrides),
                "tools": ["*"],
            }
            headers = server.get("headers")
            if headers:
                config["headers"] = _expand_dict(headers, env_overrides)
            result[name] = config

    return result


def detect_missing_env_vars(mcp_servers: dict) -> list[str]:
    """偵測 .mcp.json 中引用了哪些未定義的環境變數。"""
    missing: set[str] = set()

    for server in mcp_servers.values():
        for arg in server.get("args", []):
            for var in _VAR_PATTERN.findall(str(arg)):
                if not os.environ.get(var):
                    missing.add(var)
        for val in server.get("env", {}).values():
            for var in _VAR_PATTERN.findall(str(val)):
                if not os.environ.get(var):
                    missing.add(var)
        url = server.get("url", "")
        if url:
            for var in _VAR_PATTERN.findall(url):
                if not os.environ.get(var):
                    missing.add(var)

    return sorted(missing)


def scan_repo_mcp_json(
    repo_url: str,
    branch: str | None,
    github_token: str,
) -> dict:
    """用 GitHub Contents API 輕量 fetch repo 的 .mcp.json，回傳 servers 和 missing_vars。

    不做 git clone，只 fetch 單一檔案。
    回傳 {"servers": [...], "missing_vars": [...]}。
    """
    import base64
    import urllib.request
    import urllib.error

    # 解析 repo_url → owner/repo
    # https://github.com/org/repo.git → org/repo
    path = repo_url.replace("https://", "").split("/", 1)[-1]
    path = path.removesuffix(".git")
    # 移除 host 前綴（e.g. github.com/）
    parts = path.split("/", 1)
    if len(parts) == 2 and "." in parts[0]:
        # github.com/org/repo → org/repo
        owner_repo = parts[1]
    else:
        owner_repo = path

    api_url = f"https://api.github.com/repos/{owner_repo}/contents/.mcp.json"
    if branch:
        api_url += f"?ref={branch}"

    req = urllib.request.Request(api_url, headers={
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "copilot-dev-system",
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        logger.debug("scan_repo_mcp_json failed: %s", e)
        return {"servers": [], "missing_vars": []}

    # GitHub API 回傳 base64 encoded content
    try:
        content_b64 = data.get("content", "")
        content_str = base64.b64decode(content_b64).decode("utf-8")
        mcp_data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse remote .mcp.json: %s", e)
        return {"servers": [], "missing_vars": []}

    mcp_servers = mcp_data.get("mcpServers", {})
    servers = sorted(mcp_servers.keys())
    missing = detect_missing_env_vars(mcp_servers)

    return {"servers": servers, "missing_vars": missing}


# ── 內部輔助函數 ──────────────────────────────────────────────

def _expand_str(value: str, overrides: dict[str, str]) -> str:
    """展開字串中的 ${VAR} 引用。"""
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in overrides:
            return overrides[var_name]
        env_val = os.environ.get(var_name)
        if env_val is not None:
            return env_val
        return match.group(0)  # 未定義則保留原樣

    return _VAR_PATTERN.sub(replacer, value)


def _expand_list(items: list, overrides: dict[str, str]) -> list[str]:
    """展開 list 中每個字串的 ${VAR} 引用。"""
    return [_expand_str(str(item), overrides) for item in items]


def _expand_dict(d: dict[str, str], overrides: dict[str, str]) -> dict[str, str]:
    """展開 dict values 中的 ${VAR} 引用。"""
    return {k: _expand_str(str(v), overrides) for k, v in d.items()}
