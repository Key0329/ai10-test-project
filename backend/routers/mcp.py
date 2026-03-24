"""MCP 相關 API routes。"""

from pydantic import BaseModel, field_validator
from fastapi import APIRouter

from services.mcp import mcp_registry
from services.mcp_loader import scan_repo_mcp_json

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


class McpTestRequest(BaseModel):
    """MCP 連線測試請求模型。"""

    selected_mcps: list[str]
    mcp_tokens: dict[str, str] = {}


class McpScanRequest(BaseModel):
    """MCP scan 請求模型。"""

    repo_url: str
    branch: str | None = None
    github_token: str

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        import re
        if not v.startswith("https://"):
            raise ValueError("Only HTTPS repo URLs are allowed")
        if not re.match(r"^https://[\w.\-]+/[\w.\-/]+(?:\.git)?$", v):
            raise ValueError("Invalid repo URL format")
        return v


@router.get("/list")
def mcp_list():
    """回傳所有可用 MCP 及 preset 定義。"""
    return {
        "mcps": mcp_registry.get_all(),
        "presets": mcp_registry.get_presets(),
    }


@router.post("/test")
async def mcp_test(req: McpTestRequest):
    """測試指定 MCP 的連線狀態。"""
    results = await mcp_registry.test_connection(req.selected_mcps, req.mcp_tokens)
    return {"results": results}


@router.post("/scan")
def mcp_scan(req: McpScanRequest):
    """掃描 repo 的 .mcp.json，回傳 MCP servers 和需要的環境變數。"""
    return scan_repo_mcp_json(req.repo_url, req.branch, req.github_token)
