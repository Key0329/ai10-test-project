"""MCP 相關 API routes。"""

from pydantic import BaseModel, field_validator
from fastapi import APIRouter

from services.mcp_loader import scan_repo_mcp_json

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


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


@router.post("/scan")
def mcp_scan(req: McpScanRequest):
    """掃描 repo 的 .mcp.json，回傳 MCP servers 和需要的環境變數。"""
    return scan_repo_mcp_json(req.repo_url, req.branch, req.github_token)
